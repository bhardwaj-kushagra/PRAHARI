# PRAHARI-SIM — Product and Software Requirements Specification

**Project:** FIRENET–PRAHARI simulator and demonstration dashboard
**Version:** 1.0.1 · 23 September 2026 (errata to 1.0 listed in `DECISIONS.md`)
**Audience:** the developer, and AI coding agents (Claude Code or similar) working inside this repository
**Purpose of this document:** define *what* to build, *in what order*, *with which mathematics*, and *how to keep it working at every step*

> **For AI agents.** Read `CLAUDE.md` first; its rules override anything you infer. Then read §1–§4 of this file once, and afterwards only the section for the phase you are working on plus the equations it references in §5. Do not start a phase whose predecessor's acceptance tests fail.

---

## Contents

1. Product overview
2. Non-negotiable engineering principles
3. System architecture
4. The module framework (contracts, registry, stubs, config, recording)
5. Scientific models and mathematics (equations M1–M46)
6. Dashboard specification
7. Phased delivery plan (Phases 0–10)
8. Scenarios and Regime Cards
9. Testing strategy
10. Risk register and fallback matrix
11. Conference demo storyboard
12. Prompt pack for coding agents
13. Appendices: parameters, reference values, glossary

---

## 1. Product overview

### 1.1 What we are building

A local, laptop-run **simulator with a live dashboard** that demonstrates the FIRENET–PRAHARI wildfire-detection system with real mathematics:

- A virtual forest with an ignition interface (paths, villages, roads, a power line), a deployed sensor network, gateways and radio links.
- Weather, fuel moisture, fires, smoke plumes and realistic low-cost gas-sensor signals (drift, daily cycles, noise, nuisance events, regional haze, faults).
- Baseline detectors (fixed thresholds; the v1 design) and the PRAHARI decision core (TTC, QCC, node CUSUM, SCMR, Fisher combination, SRP prior, RAQ, graded escalation).
- Satellite-alert timing for comparison, LoRaWAN communication and node energy.
- An evaluation harness that reproduces the report's tables and figures from repeated Monte Carlo runs.
- A dashboard that shows all of this happening — the map, the plume, nodes lighting up, the evidence behind each alarm, and the results charts.

### 1.2 Who it is for

| Audience | What they must take away |
| --- | --- |
| Conference judges and visitors | "This works, the maths is real, and I can see why it raised that alarm." |
| The presenter | A reliable, offline, three-minute demo plus deeper views for questions |
| Future developers | A clean engine that later accepts real sensor logs and field-burn data |

### 1.3 Success criteria

| ID | Criterion | Measure |
| --- | --- | --- |
| S1 | Runs locally on a normal laptop, offline | No internet needed after installation; Windows, macOS or Linux |
| S2 | Always demo-able | Every phase leaves a runnable dashboard; recorded replays work even if the engine is broken |
| S3 | Scientifically honest | Every model has documented equations, parameters, sources and a provenance tag; nothing fabricated |
| S4 | Reproduces reported results | In legacy mode, reproduces the report's key numbers within their 95% confidence intervals (§9.3) |
| S5 | Visually impressive | Animated map with plume and node states, a "why this alarm" panel, live mechanism toggles, results charts |
| S6 | Degrades gracefully | Any module can be switched to a stub or turned off from config or the dashboard without breaking anything else |

### 1.4 Non-goals

- Not production software: no authentication, cloud deployment, databases or multi-user support.
- Not a computational fluid-dynamics or fire-spread research model. Physics is simplified, documented and labelled.
- Not firmware. The node algorithms run in Python here; porting to ESP32 is future work.
- No machine-learning model training beyond the small, explicit likelihood-ratio fit in §5.10.

### 1.5 Provenance tags used throughout

| Tag | Meaning |
| --- | --- |
| `LIT` | Value or model from literature, agency document or standard (reference number given) |
| `VEN` | Manufacturer datasheet or product claim |
| `DER` | Derived by calculation from tagged inputs |
| `ASM` | Modelling assumption chosen by us; must be listed in the dashboard's model card |
| `SIM` | Output of this simulator |
| `TGT` | Design target |

Every output shown in the dashboard is `SIM`, and the dashboard must say so.

---

## 2. Non-negotiable engineering principles

These rules exist to prevent the two failure modes that kill agent-built projects: **rewriting working code** and **getting stuck on one hard piece**. They are requirements, not suggestions. An agent that cannot satisfy one must stop and say so rather than work around it.

### P1 — Every stage is a plug-in with a stub

Every pipeline stage (sensor model, plume, TTC, QCC, SCMR, RAQ, and so on) implements a fixed interface and ships with a **stub** that returns valid, simple output. Stubs are written in Phase 0, before any real model. A real implementation *replaces* the stub through the registry; the stub is never deleted.

### P2 — Three states per module: `real`, `stub`, `off`

Configuration selects each module's state. `real` is the full model, `stub` is the simple fallback, and `off` bypasses the stage (identity or neutral output) where that is meaningful. The dashboard shows every module's state and lets the presenter switch it live.

### P3 — Contracts are frozen once a phase is accepted

Data exchanged between stages uses typed data classes defined in `engine/prahari/core/contracts.py`. After the phase that introduces a contract is accepted, its fields may only be **added** (with defaults), never renamed or removed, unless the contract version is bumped and every consumer is updated in the same change with tests.

### P4 — Additive phases, no rewrites

A new phase adds new files or replaces a stub's implementation behind the registry. It must not restructure, rename or "clean up" modules from accepted phases. Refactoring an accepted module needs an explicit entry in `DECISIONS.md` and the developer's approval.

### P5 — Failure isolation and automatic degradation

The pipeline runner wraps every module call. If a `real` module raises an exception or returns invalid output (NaN, wrong shape, out-of-range values), the runner logs it, switches that module to `stub` for the rest of the run, marks it `DEGRADED` in the module-health panel, and continues. One broken module never crashes the simulation or the dashboard.

### P6 — Timebox and escape hatch

Every phase and every module has a timebox (§7). If a module fails its acceptance tests after the timebox — about three focused attempts — the agent must:

1. set it to `stub` in the default configuration,
2. record the failure, symptoms and suspected cause in `KNOWN_ISSUES.md`,
3. move on to the next module or phase.

Being stuck on one module is never a reason to stop the project. The stub keeps everything downstream working.

### P7 — Determinism

All randomness flows from one master seed through `numpy.random.SeedSequence`, spawning a separate generator per module. The same seed and configuration must give identical results. Never use Python's `random` module or unseeded NumPy.

### P8 — Replay-first dashboard

The dashboard must work from **recorded runs** (files on disk) before it ever talks to a live engine. Every demo scenario is pre-recorded. If the live engine fails during the conference, the replay still runs. Live mode is added in Phase 6, never required.

### P9 — Evidence trace for every decision

Every node candidate and every edge decision emits an evidence record containing every intermediate value (§4.7). The "why this alarm" panel is built from these records. Auditability is a core claim of PRAHARI; the simulator must demonstrate it.

### P10 — Scientific honesty in code

- Every equation in code cites its §5 equation number in a comment: `# M26 — QCC p-value`.
- Every parameter lives in configuration with a `source` field (tag plus reference).
- No hard-coded "result" numbers anywhere except in golden tests.
- Never tune a model to make a chart look better without recording it in `DECISIONS.md`.

### P11 — Small, testable units

Each module is a small file (target under 300 lines) with its own unit tests. Maths lives in pure functions that take arrays and return arrays; no hidden global state.

### P12 — Minimal dependencies

Engine: Python 3.11+, NumPy, SciPy, PyYAML, Pydantic (optional), pytest. Server: FastAPI, Uvicorn. Dashboard: React, TypeScript, Vite, one chart library (Apache ECharts), zustand for state. Adding any other dependency requires a line in `DECISIONS.md` with the reason.

---

## 3. System architecture

### 3.1 Components

```text
┌──────────────────────────── engine/ (Python package "prahari") ──────────────────────────────┐
│                                                                                               │
│  scenario + regime config ──► World ──► Weather/FFMC ──► Ignition ──► Fire ──► Plume          │
│                                   │                                            │              │
│                                   └──► Network (nodes, gateways, links)        ▼              │
│                                                              Sensor model (per node signal)  │
│                                                                               │               │
│        ┌──────── node layer (per node) ─────────┐        ┌──────── edge layer ──────────┐     │
│        │ TTC ─► QCC ─► node score ─► CUSUM ────────► comms ─► clustering ─► SCMR ─► Fisher │  │
│        └────────────────────────────────────────┘        │         SRP prior ─► RAQ ─► escalation│
│                                                          └──────────────────────────────┘     │
│   Baselines (P0 fixed, P1 v1) run in parallel on the same signals                             │
│   Satellite model, energy model, evaluation harness, recorder (frames + evidence + metrics)  │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
            │ recordings (files)                         │ live frames (WebSocket, Phase 6+)
            ▼                                            ▼
      recordings/*.prs  ◄──────────────  server/ (FastAPI, thin wrapper)
            │                                            │
            └───────────────►  dashboard/ (React + TypeScript + Vite)  ◄───────┘
```

The engine never imports the server or dashboard. The server is a thin adapter. The dashboard knows only the frame contract (§4.6).

### 3.2 Repository layout

```text
prahari-sim/
├── CLAUDE.md                     # agent rules (loaded automatically by Claude Code)
├── DECISIONS.md                  # every deviation, dependency, tuning decision
├── KNOWN_ISSUES.md               # modules parked as stubs, with reasons
├── PROGRESS.md                   # phase checklist, updated at the end of each session
├── docs/SPEC.md                  # this document
├── reference/prahari_simulation.py   # the original research script (read-only oracle)
├── configs/
│   ├── default.yaml              # module states + all parameters with sources
│   ├── regimes/{india,canada,usa,australia}.yaml
│   └── scenarios/*.yaml          # demo and experiment scenarios
├── engine/
│   ├── pyproject.toml
│   ├── prahari/
│   │   ├── core/        contracts.py registry.py config.py rng.py clock.py trace.py runner.py health.py
│   │   ├── world/       geometry.py interfaces.py siting.py
│   │   ├── env/         weather.py ffmc.py
│   │   ├── fire/        ignition.py growth.py plume.py
│   │   ├── sensors/     mox.py noise.py nuisance.py haze.py faults.py health.py
│   │   ├── comms/       pathloss.py lorawan.py aloha.py
│   │   ├── energy/      budget.py solar.py storage.py
│   │   ├── detect/
│   │   │   ├── baselines/  fixed.py v1.py
│   │   │   └── prahari/    ttc.py qcc.py score.py cusum.py cluster.py scmr.py fisher.py srp.py raq.py escalate.py learn.py
│   │   ├── satellite/   overpass.py
│   │   ├── eval/        metrics.py stats.py experiments.py
│   │   ├── record/      writer.py reader.py
│   │   └── cli.py
│   └── tests/  unit/  golden/  smoke/
├── server/      app.py  (FastAPI: REST + WebSocket)
├── dashboard/   (Vite React TypeScript app)
├── recordings/  (demo recordings, committed)
└── results/     (experiment outputs, gitignored except summaries)
```

### 3.3 Time and scale

| Quantity | Default | Notes |
| --- | --- | --- |
| Tick | 1 minute | Every stage steps once per tick |
| Network | 100 nodes | Grid 10 × 10 at 70 m, or corridor layouts |
| Demo run | 1–3 simulated days | Recorded for replay |
| Experiment run | 14 d calibration + 14 d tuning + 30 d test per seed | Matches the report |
| Performance target | 1 simulated day for 100 nodes in under 3 s | Vectorise across nodes with NumPy |

All per-node state is held in NumPy arrays of shape `(N,)` or `(N, channels)`. Loops over nodes are forbidden inside the tick loop; loops over time are acceptable.

---

## 4. The module framework

Phase 0 builds this framework completely, with stubs for every stage. Everything after that plugs into it.

### 4.1 Stage interface

```python
# engine/prahari/core/registry.py (sketch)
from typing import Protocol, Any

class Stage(Protocol):
    name: str            # e.g. "qcc"
    version: str         # e.g. "1.0"
    kind: str            # "real" or "stub"

    def reset(self, ctx: "RunContext") -> None: ...
    def step(self, inputs: Any, ctx: "RunContext") -> Any: ...
    def snapshot(self) -> dict: ...   # small JSON-safe state for the dashboard / trace
```

Each stage directory has `real` and `stub` classes registered under the same name:

```python
@register("qcc", kind="real")
class QCC: ...

@register("qcc", kind="stub")
class QCCStub: ...   # Gaussian z-score p-values
```

### 4.2 Module registry and states

```python
registry.build("qcc", state=config.modules.qcc, params=config.params.qcc, rng=rngs["qcc"])
# state ∈ {"real", "stub", "off"}
```

| Module | Stub behaviour | `off` behaviour |
| --- | --- | --- |
| weather | Constant 30 °C, 40% RH, 1.5 m/s wind from the west | Not allowed (required) |
| ffmc | Constant FFMC 85 | Constant FFMC 85 |
| ignition | Fires at scripted times and places from the scenario file | No fires |
| growth | Source strength ramp Q(t) (M9) | Not allowed |
| plume | Exponential-decay legacy model (M12) | No smoke reaches sensors |
| sensor | Baseline plus white noise plus plume signal | Not allowed |
| nuisance, haze, faults | None generated | None generated |
| ttc | Slow EWMA residual only (v1 behaviour) | Raw reading minus first-day mean |
| qcc | Gaussian p-value from robust z-score | Gaussian p-value |
| cusum | Fixed h from the ARL formula (M23) | Single-sample threshold |
| scmr | Always pass | Always pass |
| fisher | Minimum p-value times cluster size (Bonferroni) | Minimum p-value |
| srp | Constant prior odds from config | Constant prior odds |
| raq | Fixed quorum of 2 | Fixed quorum of 2 |
| escalate | CONFIRMED when the quorum is met | Same |
| comms | Perfect link, zero latency | Perfect link |
| energy | Infinite energy | Infinite energy |
| satellite | Fixed 90 min after ignition | Not shown |
| learn | SBB bound (M34) | SBB bound (M34) |

### 4.3 Configuration

One YAML file composes defaults, a Regime Card and a scenario. Every parameter carries its source.

```yaml
run:
  seed: 11
  start: "2026-04-15T00:00"
  days: 2
  tick_minutes: 1
modules:
  weather: real
  plume: stub            # switch to real when Phase 3b passes
  qcc: real
  scmr: real
  raq: real
params:
  qcc:
    bins_per_day: 6
    calibration_days: 14
    source: "ASM; method LIT [37]"
  scmr:
    ratio_threshold: 3.0
    window_min: 30
    source: "ASM, tuned in report simulation"
```

The loader validates every file against a schema and fails with a clear message naming the bad key. Unknown keys are errors, not silently ignored.

### 4.4 Random numbers

```python
root = np.random.SeedSequence(config.run.seed)
names = ["weather", "ignition", "growth", "plume", "sensor", "nuisance", "haze", "faults", "comms", "satellite"]
rngs = {name: np.random.default_rng(child) for name, child in zip(names, root.spawn(len(names)))}
```

Adding a new module appends a name at the end of the list, so existing streams are unchanged and old results stay reproducible.

### 4.5 The tick loop and runner

```python
for t in clock:                                   # one tick per minute
    env   = run_stage("weather", t)               # T, RH, wind, rain
    ffmc  = run_stage("ffmc", env)
    fires = run_stage("ignition", (t, env, ffmc)) # new ignitions
    src   = run_stage("growth", (t, fires, env))  # source strengths
    conc  = run_stage("plume", (src, env))        # concentration at every node (N,)
    x     = run_stage("sensor", (t, conc, env))   # raw readings (N, channels)
    # baselines and PRAHARI run on the same x
    base  = run_baselines(x, t)
    r     = run_stage("ttc", x)
    p     = run_stage("qcc", (r, t))
    s     = run_stage("score", (p, health))
    cand  = run_stage("cusum", s)
    frames_out = run_stage("comms", cand)         # delivered candidate frames
    dec   = run_stage("edge", (frames_out, prior))  # cluster, SCMR, Fisher, SRP, RAQ, escalate
    recorder.write(t, ...)
```

`run_stage` implements principle P5: validate output, catch exceptions, degrade to stub, update module health.

### 4.6 The frame contract (engine → dashboard)

A recording is a header plus a stream of frames. Use newline-delimited JSON (`.prs.jsonl`), optionally gzipped. One frame per recorded tick; for long runs record every k-th tick (configurable) plus every tick containing an event.

```json
{
  "header": {
    "schema": "prahari.frame/1",
    "scenario": "dry_afternoon_india",
    "seed": 11,
    "tick_minutes": 1,
    "map": {"width_m": 700, "height_m": 700,
            "interfaces": [{"kind": "path", "points": [[0, 120], [700, 180]]}],
            "fuel_raster": "optional base64 PNG"},
    "nodes": [{"id": 0, "x": 35, "y": 35, "type": "B"}],
    "gateways": [{"id": "g1", "x": 350, "y": 690}],
    "modules": {"qcc": "real", "plume": "stub"},
    "model_card": [{"model": "plume", "equation": "M12", "tag": "ASM"}]
  }
}
{"t": 840,
 "weather": {"T": 34.1, "RH": 22, "wind_ms": 2.1, "wind_dir_deg": 250, "ffmc": 91.2},
 "prior": {"odds": 1.2e-4, "quorum": 2},
 "nodes": {"state": [0, 0, 1, 2], "reading": [0.12, 0.08, 1.9, 2.4],
           "residual": [0.1, 0.0, 1.8, 2.3], "p": [0.41, 0.77, 0.002, 0.0004],
           "cusum": [0.0, 0.0, 41.2, 96.0], "health": [1, 1, 1, 0.8], "soc": [0.93, 0.91, 0.9, 0.88]},
 "fires": [{"id": 3, "x": 402, "y": 311, "area_m2": 14.0, "age_min": 12}],
 "plume": {"grid": "optional coarse concentration grid, base64 float16", "levels": [0.1, 0.5, 1.0]},
 "packets": [{"from": 18, "to": "g1", "ok": true, "sf": 9}],
 "events": [{"type": "candidate", "node": 18, "trace_id": "c-18-840"}],
 "alerts": [{"level": "CONFIRMED", "cluster": [17, 18, 27], "trace_id": "d-840-1"}],
 "health": {"qcc": "ok", "plume": "stub"}}
```

Node arrays are ordered by node id to keep frames small. Node state codes: 0 normal, 1 elevated, 2 candidate, 3 confirmed member, 4 fault, 5 low power.

### 4.7 The evidence trace

Every candidate and decision writes a trace record, also stored in the recording:

```json
{"trace_id": "d-840-1", "t": 840, "type": "decision", "level": "CONFIRMED",
 "cluster": [17, 18, 27],
 "per_node": [{"node": 18, "p_channels": [0.00069], "health": [1.0], "cusum": 96.0, "h": 218.7}],
 "scmr": {"f_loc": 0.33, "f_net": 0.03, "ratio": 11.0, "pass": true},
 "fisher": {"X": 43.7, "dof": 6, "p_cluster": 8.6e-8},
 "prior": {"lambda": 3.1e-6, "p_s": 0.62, "pi": 1.9e-6, "odds": 1.9e-6},
 "bayes": {"bf_bound": 2.6e5, "posterior_odds": 0.50, "threshold": 0.01, "decision": true},
 "explanation": "3 of 9 neighbours raised candidates within 30 min; local rate 11x the network rate; Fisher p 8.6e-8 across 3 nodes; posterior odds 0.50 met the 0.01 threshold."}
```

The `explanation` string is generated by a template from the numbers, never free text.

### 4.8 Module health

`health.py` tracks per module: state (`real`, `stub`, `off`, `degraded`), exception count, last error, mean step time. The server exposes it and the dashboard shows it (§6.2, view 7).
---

## 5. Scientific models and mathematics

Each model has an equation number (M-number) that code must cite. Default parameters reproduce the report's simulation ("legacy mode") unless marked *advanced*. Where a model has a legacy and an advanced form, the legacy form is the stub or default and the advanced form is an upgrade behind the same interface.

**Units.** Distances in metres, time in minutes unless stated, temperature in °C, relative humidity in %, wind in m/s (converted to m/min where noted). Sensor output is in *sensor units* (su), a normalised log-resistance scale in which quiet-period residual noise has a standard deviation of about 0.23 su.

### 5.1 World, ignition interfaces and siting

**M1 — Node layouts.** Grid: node $(a,b)$ at $(a\,s,\; b\,s)$ for $a,b = 0,\dots,\sqrt{N}-1$, spacing $s$ (default 70 m). Corridor: nodes every $s$ metres along an interface polyline, alternating a lateral offset of $\pm d$ (default 15 m).

**M2 — Distance fields.** For each interface class $k$ (path, village, road, power line), $D_k(x)$ is the Euclidean distance from point $x$ to the nearest feature of class $k$. Precompute on a 10 m raster.

**M3 — Ignition-source intensity** (attempts per m² per minute):

$$
\lambda(x,t) \;=\; \lambda_0\, a(t) \sum_k w_k\, e^{-D_k(x)/L_k} \;+\; \lambda_{\text{light}}(x,t)
$$

- $a(t)$ — human activity profile: default 0.2 at night, 1.0 from 09:00 to 18:00, with a smooth ramp between; ×1.5 on market or festival days (`ASM`).
- $w_k$, $L_k$ — class weights and decay lengths; defaults path 1.0 / 30 m, village 1.5 / 150 m, road 1.0 / 50 m, power line 0.5 / 20 m (`ASM`). The India card weights paths and villages highest, reflecting that over 95% of fires are human-caused `LIT [17]`.
- $\lambda_{\text{light}}$ — lightning term, zero except in lightning-storm scenarios, when strikes arrive as a Poisson process over the storm footprint (`ASM`).
- $\lambda_0$ — scaled so the expected number of sustained fires per scenario matches the scenario file.

**M4 — Siting by maximum coverage.** Choose node sites $S$, with $|S| \le N$, to maximise covered ignition likelihood:

$$
\max_{S,\;|S|\le N}\; \sum_{x \in \text{raster}} \lambda(x)\; \mathbf{1}\!\left[\min_{s\in S}\lVert x-s\rVert \le r_d\right]
$$

Solve greedily: repeatedly add the candidate site with the largest marginal gain. The greedy solution is within a factor $(1-1/e) \approx 0.63$ of the optimum `LIT` (standard submodular-maximisation result). Default detection radius $r_d = 50$ m `LIT [3]`, optionally made direction-aware using prevailing wind. The dashboard shows grid, corridor and greedy layouts side by side, with covered likelihood as a percentage.

### 5.2 Weather and fuel moisture

**M5 — Diurnal weather.** Hour of day $h$:

$$
T(t) = \bar T_d + A_T \sin\!\left(\frac{2\pi (h - 9)}{24}\right) + \epsilon_T(t), \qquad \epsilon_T \sim \text{AR(1)},\ \phi = 0.98,\ \sigma = 0.3\ ^\circ\text{C}
$$

Daily means $\bar T_d$ and dew points $T_{dew,d}$ follow a slow random walk. Defaults for India pre-monsoon: $\bar T = 30$ °C, $A_T = 7$ °C, $T_{dew} = 10$ °C (`ASM`). Wind speed at 10 m is lognormal (median 1.5 m/s, σ_log 0.4) with AR(1) persistence; direction is a random walk with a prevailing mean (`ASM`). Rain events are a Poisson process with scenario-set daily probability.

**M6 — Relative humidity from dew point** (Magnus form, `LIT`):

$$
RH = 100\,\frac{\exp\!\left(\frac{17.625\,T_{dew}}{243.04 + T_{dew}}\right)}{\exp\!\left(\frac{17.625\,T}{243.04 + T}\right)}
$$

**M7 — Fine Fuel Moisture Code** (daily, Van Wagner and Pickett 1985; Van Wagner 1987; `LIT [16]`). Inputs: noon temperature $T$ (°C), humidity $H$ (%), wind $W$ (km/h), 24-hour rain $r_o$ (mm), yesterday's code $F_o$ (start-up value 85).

$$
m_o = \frac{147.2\,(101 - F_o)}{59.5 + F_o}
$$

If $r_o > 0.5$, let $r_f = r_o - 0.5$ and

$$
m_o \leftarrow m_o + 42.5\, r_f\, e^{-100/(251 - m_o)}\left(1 - e^{-6.93/r_f}\right) \;\big[\,+\,0.0015\,(m_o - 150)^2 \sqrt{r_f}\ \text{ if } m_o > 150\,\big], \qquad m_o \le 250
$$

Equilibrium moisture contents for drying ($E_d$) and wetting ($E_w$):

$$
E_d = 0.942\,H^{0.679} + 11\,e^{(H-100)/10} + 0.18\,(21.1 - T)\left(1 - e^{-0.115 H}\right)
$$

$$
E_w = 0.618\,H^{0.753} + 10\,e^{(H-100)/10} + 0.18\,(21.1 - T)\left(1 - e^{-0.115 H}\right)
$$

If $m_o > E_d$ (drying):

$$
k_d = \left[0.424\left(1 - (H/100)^{1.7}\right) + 0.0694\sqrt{W}\left(1 - (H/100)^{8}\right)\right] \times 0.581\,e^{0.0365\,T}, \qquad m = E_d + (m_o - E_d)\,10^{-k_d}
$$

If $m_o < E_w$ (wetting):

$$
k_w = \left[0.424\left(1 - \left(\tfrac{100-H}{100}\right)^{1.7}\right) + 0.0694\sqrt{W}\left(1 - \left(\tfrac{100-H}{100}\right)^{8}\right)\right] \times 0.581\,e^{0.0365\,T}, \qquad m = E_w - (E_w - m_o)\,10^{-k_w}
$$

Otherwise $m = m_o$. Finally:

$$
\text{FFMC} = \frac{59.5\,(250 - m)}{147.2 + m}
$$

> **Verification required.** These equations are transcribed from memory of the standard formulation. The unit tests for M7 must compare against reference values computed with the official `cffdrs` implementation (R package, or a vetted Python port) for at least ten weather days, to within 0.1 FFMC. If they do not match, fix M7 before relying on it; until then run `ffmc: stub`. The standard start-up values are documented as suitable for Canadian, northern US and Alaskan spring conditions, not elsewhere `LIT [15]`; the India card must note this.

Hourly FFMC (Van Wagner 1977; `cffdrs` hourly function) is an optional upgrade behind the same interface.

### 5.3 Ignition

**M8 — Sustained-ignition probability** (logistic in the moisture code, form from Beverly and Wotton `LIT [10]`):

$$
p_s(M) = \frac{1}{1 + e^{-(a + b\,M)}}
$$

Defaults $a = -21$, $b = 0.25$ with $M$ = FFMC, giving $p_s \approx 0.2$ at FFMC 78, 0.5 at 84 and 0.9 at 92 (`ASM`, shape only — the published coefficients are per fuel category and must be refitted for Indian fuels).

**Ignition process.** Attempts form an inhomogeneous Poisson process with intensity $\lambda(x,t)$ (M3). Simulate by thinning: draw candidate attempts at the maximum rate, accept each with probability $\lambda(x,t)/\lambda_{max}$, then keep each accepted attempt as a sustained fire with probability $p_s(M_t)$. Experiments also support **scripted ignitions** (time and place from the scenario), which are needed to measure detection rates under controlled conditions, as in the report.

### 5.4 Fire growth and source strength

**M9 — Legacy source strength** (default, reproduces the report):

$$
Q(\tau) = Q_{max}\left(1 - e^{-\tau/\tau_g}\right), \qquad \tau = \text{minutes since ignition},\ \tau_g = 10,\ Q_{max} \sim Q_{ref}\cdot\text{Lognormal}(0,\,0.5)
$$

**M10 — Advanced growth** (optional). Elliptical fire with head rate of spread

$$
R = R_0 \, e^{\,b_u u_c}\, g(\text{FFMC}), \qquad g(F) = \max\!\left(0,\ \frac{F - 70}{25}\right)
$$

with defaults $R_0 = 0.2$ m/min and $b_u = 0.5$ s/m (`ASM`). Length-to-breadth ratio $1 + 0.5\,u_c$. Area $A = \pi a b$. Emission rate is proportional to the rate of area growth, $Q \propto \frac{dA}{dt}\, w_{fuel}\, EF$, scaled so that $Q$ at 15 min matches M9's $Q_{ref}$. This mode is illustrative only.

### 5.5 Smoke transport

**M11 — Gaussian plume, advanced.** Ground-reflected, steady-state concentration at a receptor $x$ metres downwind, $y$ crosswind and height $z$, from a source at height $H$:

$$
C(x,y,z) = \frac{Q}{2\pi\, u_c\, \sigma_y(x)\, \sigma_z(x)}\; e^{-\frac{y^2}{2\sigma_y^2}}\left[e^{-\frac{(z-H)^2}{2\sigma_z^2}} + e^{-\frac{(z+H)^2}{2\sigma_z^2}}\right], \qquad x > 0
$$

Defaults: receptor height $z = 2.5$ m (trunk mount, `LIT [3]`), source height $H = 0.5$ m, plume rise ignored for small fires (`ASM`). Upwind receptors ($x \le 0$) receive $C = 0$ from this term; the upwind factor in M13 is added as a small diffusive floor so that upwind nodes see about 10% `LIT [3]`.

**M12 — Legacy exponential-directional model** (stub and default for golden tests):

$$
C_i(t) = Q\!\left(t - \frac{d_i}{u}\right)\, e^{-d_i/L}\; h(\varphi_i)\; \varepsilon_i(t), \qquad L = 40\ \text{m}
$$

$d_i$ is the distance from the fire to node $i$; $\varepsilon_i(t) = \exp(\mathcal N(0, 0.5^2) - 0.125)$ is mean-one intermittency; $Q_{ref}$ is set so that $C = 2.5$ su at 50 m straight downwind at full growth, matching detection at about 50 m downwind within minutes `LIT [3]`.

**M13 — Directional factor**, with $\varphi_i$ the angle between the downwind direction and the fire-to-node bearing:

$$
h(\varphi) = 0.1 + 0.9\left(\frac{1 + \cos\varphi}{2}\right)^2
$$

**M14 — Dispersion coefficients** (Briggs, open-country; $x$ in metres; `LIT`, standard air-quality modelling references). Use the stability class from the scenario (default C by day, E at night):

| Class | $\sigma_y(x)$ | $\sigma_z(x)$ |
| --- | --- | --- |
| A | $0.22x\,(1+0.0001x)^{-1/2}$ | $0.20x$ |
| B | $0.16x\,(1+0.0001x)^{-1/2}$ | $0.12x$ |
| C | $0.11x\,(1+0.0001x)^{-1/2}$ | $0.08x\,(1+0.0002x)^{-1/2}$ |
| D | $0.08x\,(1+0.0001x)^{-1/2}$ | $0.06x\,(1+0.0015x)^{-1/2}$ |
| E | $0.06x\,(1+0.0001x)^{-1/2}$ | $0.03x\,(1+0.0003x)^{-1}$ |
| F | $0.04x\,(1+0.0001x)^{-1/2}$ | $0.016x\,(1+0.0003x)^{-1}$ |

These formulas were fitted for distances of roughly 100 m to 10 km. Below 100 m, clamp $\sigma_y, \sigma_z \ge 1$ m and treat results as approximate (`ASM`). **Calibration rule:** set $Q$ by solving M11 so that the ground concentration 50 m downwind, at full growth, in class C, equals the legacy model's 2.5 su. Implement this as a function `calibrate_q()` and record the value in the model card (`DER`).

**M15 — Sub-canopy wind:** $u_c = \alpha_c\, u_{10}$ with $\alpha_c = 0.4$ (`ASM`); floor at 0.5 m/s.

**M16 — Transport delay:** $\tau_i = x_i / u_c$ (downwind distance over canopy wind speed).

**Multiple fires.** Concentrations from simultaneous fires add linearly at each node.

**Plume grid for the dashboard.** Evaluate the active plume model on a coarse grid (for example 70 × 70 cells of 10 m), every 5 ticks, quantised to float16, for the heat overlay.

### 5.6 Sensor model

**M17 — Metal-oxide response.** Legacy: the plume concentration in su adds linearly to the reading. Advanced: a saturating log response, typical of metal-oxide sensors `ASM`:

$$
y = \beta \ln\!\left(1 + \frac{C}{C_0}\right)
$$

with $\beta$ and $C_0$ chosen so that $y \approx C$ for small $C$.

**M18 — Composite reading** for node $i$, channel 1 (BME688 gas):

$$
x_i(t) = \underbrace{d_i(t)}_{\text{drift}} + \underbrace{c_i\,A_{day}(t)\,\sin(2\pi\,\text{tod} - \pi/2 + \phi_i)}_{\text{residual daily cycle}} + \underbrace{e_i(t)}_{\text{AR(1)}} + \underbrace{0.05\,t_3}_{\text{heavy tail}} + n_i(t) + g_i\,H(t) + y_i(t)
$$

- Drift $d_i(t)$: random walk with step $\mathcal N(0, 0.002^2)$ per minute plus linear ageing with slope $\mathcal N(0, 0.5^2)$ over the run length.
- Daily cycle: $c_i \sim U(0.2, 0.4)$ after temperature–humidity compensation; $A_{day}$ varies by ±30% day to day. The uncompensated raw channel used by the fixed-threshold baseline adds a further $0.7\,A_{day}\sin(\cdot)$.
- $t_3$: Student-t with 3 degrees of freedom.
- $n_i(t)$: nuisance events; $H(t)$: regional haze with node gain $g_i \sim \mathcal N(1, 0.2^2)$ clipped to [0.5, 1.5]; $y_i(t)$: fire signal from M12 or M11 and M17.

**M19 — Autocorrelated noise:**

$$
e_i(t) = 0.95\, e_i(t-1) + \sigma_e\left(1 + 0.6\max\!\left(0, \sin(2\pi\,\text{tod} - \pi/2)\right)\right)\eta_t, \qquad \sigma_e = 0.05,\ \eta_t \sim \mathcal N(0,1)
$$

**M20 — Nuisance events and haze.**

- Nuisance: half the nodes are "roadside" with rate 1 per day; the rest 1 per 5 days. Each event adds $a\,e^{-(t-t_0)/\tau}$ for 60 minutes, with $a \sim \text{Lognormal}(\ln 1.5,\ 0.6)$ and $\tau \sim U(2, 10)$ min.
- Haze: episodes at rate 1 per 10 days, duration $D \sim U(180, 720)$ min, amplitude $U(0.8, 2.5)$, with 60-minute linear ramps up and down (trapezoid).
- Crop-burning seasons in the India card raise the haze rate (scenario parameter).

**M21 — Faults** (advanced; rates per node per 30 days, `ASM`):

| Fault | Effect | Default rate |
| --- | --- | --- |
| Stuck-at | Reading frozen at its last value | 0.05 |
| Offset jump | Step of ±U(0.5, 1.5) su | 0.1 |
| Spike burst | 5–20 samples of ±5 su | 0.1 |
| Dropout | Missing data (NaN) for 10–600 min | 0.2 |

### 5.7 Baseline detectors

**M22 — P0 fixed threshold.** Using the first day of raw data for node $i$: alarm when $x_i^{raw}(t) > \mu_i + 3\sigma_i$. Rising edges with a 30-minute refractory period count as alarms; any node alarm is a network alarm.

**M23 — P1 v1 as written.** Slow EWMA baseline and variance (M24 without the freeze cap), $z = (x - b)/s$, CUSUM $G_t = \max(0, G_{t-1} + z_t - k)$ with $k = 0.5$, and $h$ from Siegmund's approximation for an in-control average run length of 30 days (43,200 samples) assuming independent Gaussian data:

$$
ARL_0 \approx \frac{e^{-2\Delta b} + 2\Delta b - 1}{2\Delta^2}, \qquad \Delta = -k,\quad b = h + 1.166 \;\;\Rightarrow\;\; h \approx 8.8
$$

Confirmation: two or more candidates within radius $R$ and 30 minutes. P1t is P1 with $h$ tuned by M28.

### 5.8 PRAHARI node layer

**M24 — TTC slow baseline** (drift and health), with $\alpha = 1/720$ per minute (12-hour time constant):

$$
b_t = b_{t-1} + \alpha\,(\tilde x_t - b_{t-1}), \qquad s_t^2 = s_{t-1}^2 + \alpha\left[(\tilde x_t - b_{t-1})^2 - s_{t-1}^2\right]
$$

Freeze both while $|z_t| \ge 3$. If frozen for more than 180 minutes, resume updates using the winsorised residual $\tilde x_t = b_{t-1} + \text{clip}(x_t - b_{t-1}, -3s, 3s)$. (Without the cap, v1's baseline can lock up permanently; the simulation showed this.)

**M25 — TTC fast residual** (detection):

$$
r_t = x_t - \frac{1}{120}\sum_{u=t-180}^{t-61} x_u
$$

Implement with cumulative sums in $O(1)$ per tick. A slow baseline alone retains about 95% of a 24-hour cycle ($\omega\tau/\sqrt{1+(\omega\tau)^2}$ with $\omega\tau = \pi$, `DER`); the lagged window removes it.

**M26 — QCC conformal p-value.** For each node and each of six 4-hour time-of-day bins, keep the sorted calibration scores $\{\alpha_j\}_{j=1}^{n}$ (here $\alpha = r$ from calibration days, default 14 days):

$$
p_t = \frac{1 + \left|\{\, j \le n : \alpha_j \ge \alpha_t\,\}\right|}{n+1}, \qquad p_{min} = \frac{1}{n+1}
$$

Compute the count with a binary search (`numpy.searchsorted`). **Maturity:** the calibration set grows as quiet data accumulate (sliding window, default maximum 28 days), so $p_{min}$ falls. The dashboard shows each node's calibration size $n$ and floor.

**M27 — Node score.** Health-weighted combination across channels, re-calibrated with M26 against its own quiet-period distribution:

$$
S_t = \sum_{i} c_i\left(-\ln p_{i,t}\right)
$$

With one channel, $S_t = -\ln p_t$.

**M28 — Node CUSUM with replay-tuned threshold:**

$$
G_t = \max\left(0,\ G_{t-1} - \ln p^{node}_t - k\right), \qquad k = 1.5, \qquad \text{candidate when } G_t > h,\ \text{then } G \leftarrow 0,\ \text{30-minute refractory}
$$

Tune $h$ by bisection on the tuning days (default 14) so that node-local false candidates equal the target rate $r$ (default 1 per node per 30 days). **Exclude common-mode periods from the count:** minutes when at least 25% of nodes have $|z| \ge 3$, padded by ±60 minutes. Those are the edge's job (SCMR).

**M29 — Health weight** $c_i \in [0,1]$ (advanced; stub = 1):

$$
c_i = \mathbf 1[\text{fresh}]\cdot \mathbf 1[\text{not stuck}]\cdot \exp\!\left(-\frac{\max(0, |q_i| - 3)}{2}\right)
$$

- Fresh: data received within the last 5 minutes.
- Not stuck: rolling 60-minute variance above 1% of the node's median variance.
- $q_i$: the robust z-score of node $i$'s slow baseline against the median of its neighbours' baselines, over the last quiet day (neighbour consensus).

### 5.9 PRAHARI edge layer

**M30 — Clustering.** Keep candidates from the last $W = 30$ minutes. Build a graph linking candidate nodes within $R = 1.6\,s$ of each other. Each connected component is a cluster $C$. Multiple simultaneous fires therefore produce separate clusters.

**M31 — SCMR (Spatial Common-Mode Rejection):**

$$
\rho_C = \frac{f_{loc}}{\max(f_{net},\ 1/N)} \ge 3
$$

$f_{loc}$ is the fraction of nodes in $C$'s neighbourhood (every node within $R$ of any member) with a candidate in the window; $f_{net}$ is the same fraction network-wide. If the prior carries a lightning-storm flag, lower the threshold to 1.5 (`ASM`, untested hypothesis). Failing clusters are held at WATCH.

**M32 — Fisher combination.** Each candidate has $p_i \approx r\,\Delta T$ (for example $1/(30 \cdot 1440) \times 30 \approx 6.9\times10^{-4}$). For a cluster that passes SCMR:

$$
X_C = -2\sum_{i\in C}\ln p_i\ \sim\ \chi^2_{2|C|}, \qquad p_C = 1 - F_{\chi^2_{2|C|}}(X_C)
$$

**M33 — SRP prior** for cluster $C$ over window $\Delta t$, integrating M3 over the cluster's neighbourhood area $A_C$:

$$
\pi_C = 1 - \exp\!\left(-\,p_s(M_t)\,\Delta t \int_{A_C}\lambda(x,t)\,dx\right) \approx p_s(M_t)\,\Delta t\,\Lambda_C(t)
$$

The legacy mode instead uses the day type: prior odds $10^{-4}$ on dry, busy days and $10^{-6}$ on wet, quiet days (`TGT`).

**M34 — RAQ (Risk-Adaptive Quorum) decision rule:**

$$
\text{ALARM} \iff \text{BF}(p_C)\cdot\frac{\pi_C}{1-\pi_C} \ge \frac{C_{FA}}{C_{miss}}, \qquad \text{BF}(p) \le \frac{1}{-e\,p\ln p}\quad (p < 1/e)
$$

The bound is Sellke, Bayarri and Berger's calibration `LIT [41]`; default cost ratio $C_{FA}/C_{miss} = 0.01$ (`TGT`). The *legacy* RAQ uses its consequence directly: quorum 2 on dry, busy days and 3 on wet, quiet days. The dashboard must show the reverse view: "on today's prior, this many agreeing nodes are needed".

**M35 — Graded escalation** (state machine per cluster):

| From | To | Condition |
| --- | --- | --- |
| — | WATCH | Prior above the scenario's watch threshold, or a cluster failing SCMR |
| WATCH or — | CANDIDATE | Any node candidate |
| CANDIDATE | CONFIRMED | M34 true |
| CONFIRMED | ESCALATED | Two or more confirmed clusters within 1 km, or a cluster growing by at least 2 nodes within 30 min |
| any | cleared | No candidates in the cluster's neighbourhood for 120 min |

Every transition writes an evidence trace (§4.7).

### 5.10 Learning loop: from bound to fitted likelihood ratio

This is the mechanism by which the simulator gets better as evidence accumulates. It mirrors what the field programme will do with controlled burns.

**M36 — Fitted likelihood ratio.**

1. Run $K$ simulated controlled burns (scripted ignitions) plus quiet periods. Label each cluster window as fire (1) or no fire (0).
2. Features: $f = [\,X_C,\ |C|,\ \ln\rho_C,\ \bar c\,]$.
3. Fit a logistic regression $P(1 \mid f)$ with L2 regularisation (implement with NumPy iteratively reweighted least squares or SciPy's optimiser — no new dependency).
4. Convert to a likelihood ratio using the training prior $\pi_{train}$:

$$
\widehat{LR}(f) = \frac{P(1\mid f)}{1-P(1\mid f)}\bigg/\frac{\pi_{train}}{1-\pi_{train}}
$$

5. Use $\widehat{LR}$ in place of the bound in M34 once $K \ge 10$; below that, keep the bound.

**Learning curve.** Repeat for $K = 5, 10, 20, 50, 100$ on held-out seeds. Plot confirmation rate at a fixed false-alarm budget, and median time to confirm, against $K$. Also plot **calibration maturity**: QCC floor $p_{min}$ and node-candidate latency against days of quiet data. Both curves must come from real runs, never be drawn by hand.

### 5.11 Satellite baseline

**M37 — Satellite alert time** for a fire ignited at $t_0$:

1. Overpasses at fixed local times: Terra 10:30 and 22:30, Aqua 13:30 and 01:30, VIIRS 13:30 and 01:30 IST `LIT [17]`.
2. The first overpass at which the fire's area exceeds the detection threshold $A_{det}$ detects it with probability $1 - p_{miss}$. Defaults: $A_{det} = 500$ m², $p_{miss} = 0.2$ for cloud or canopy (`ASM` — label these clearly as illustrative).
3. Alert time = overpass time + processing delay $\sim U(40, 60)$ min for MODIS or $U(60, 90)$ min for VIIRS `LIT [17]`.

Fire area comes from M10 when enabled; otherwise from $A(\tau) = A_{15}\,(\tau/15)^2$ with $A_{15} = 20$ m² (`ASM`).

### 5.12 Communications

**M38 — Path loss**, log-distance with shadowing, calibrated to measured forest loss of about 100 dB at 200 m and 120 dB at 400 m at 922 MHz `LIT [3]`:

$$
PL(d) = 100 + 10\,n\,\log_{10}\!\frac{d}{200} + X_\sigma, \qquad n = \frac{20}{10\log_{10}2} \approx 6.64\ (\texttt{DER}),\quad X_\sigma \sim \mathcal N(0, 6^2)\ \text{dB}\ (\texttt{ASM})
$$

Received power $P_{rx} = P_{tx} + G_{tx} + G_{rx} - PL(d)$, defaults $P_{tx} = 14$ dBm, $G = 2$ dBi each. A link at spreading factor $SF$ closes if $P_{rx}$ exceeds the receiver sensitivity plus a 3 dB margin. Default sensitivities at 125 kHz bandwidth: SF7 −123, SF8 −126, SF9 −129, SF10 −132, SF11 −134.5, SF12 −137 dBm (`VEN`, typical SX127x values; verify against the datasheet in use). Each node uses the lowest SF that closes to its best gateway; a TS011 relay node forwards for nodes with no direct link.

**M39 — LoRa time on air** (Semtech formula, `VEN`):

$$
T_{sym} = \frac{2^{SF}}{BW}, \qquad n_{payload} = 8 + \max\!\left(\left\lceil\frac{8PL - 4SF + 28 + 16\,CRC - 20\,IH}{4\,(SF - 2\,DE)}\right\rceil (CR + 4),\ 0\right)
$$

$$
T_{packet} = (n_{preamble} + 4.25)\,T_{sym} + n_{payload}\,T_{sym}
$$

Defaults: payload $PL = 24$ bytes, $CR = 1$ (4/5), $CRC = 1$, explicit header $IH = 0$, $DE = 1$ for SF11–SF12, preamble 8 symbols, $BW = 125$ kHz.

**M40 — Collisions.** Uncoordinated uplinks on one channel behave like pure ALOHA. For offered load $G$ (packets per packet-time on that channel):

$$
P_{success} = e^{-2G}
$$

In the discrete simulator, two frames on the same channel and SF overlapping in time collide unless one is at least 6 dB stronger (capture effect, `ASM`). Confirmed uplinks retry up to 3 times with random back-off $U(1, 10)$ s. Heartbeat frames go out hourly. Gateway-outage scenarios queue frames at the node (store-and-forward) and deliver them when the gateway returns.

### 5.13 Energy

**M41 — Daily energy budget** per node:

$$
E_{day} = V\sum_{m}\ I_m\, t_m
$$

Defaults per day at 3.3 V: BME688 per its mode (ULP 0.09 mA, LP 0.9 mA, standard scan 3.9 mA, `VEN [33]`); ESP32 deep sleep 10 µA and active 80 mA for 1 s per minute; LoRa transmit 44 mA at 14 dBm for each frame's time on air (M39) and receive 11 mA for the Class A windows. The MCU and radio figures are `VEN`, typical values — verify against the datasheets in use. MQ-2 comparison mode: heater 950 mW continuous `VEN [34]`.

**M42 — Solar harvest:**

$$
E_{solar,day} = A_{panel}\,\eta\, G_{day}\, k_{canopy}
$$

Defaults: 1 W panel equivalent ($A\eta = 0.001$ kW), $G_{day} = 5$ kWh/m²/day pre-monsoon India, $k_{canopy} = 0.3$ (`ASM`). Distribute over the day with a half-sine from 06:00 to 18:00; cloudy days scale by $U(0.1, 0.4)$.

**M43 — Supercapacitor state:**

$$
E_{stored} = \tfrac12 C\left(V^2 - V_{min}^2\right)
$$

Two 3,000 F, 2.7 V cells, $V_{min} = 1.35$ V each, giving about 4.6 Wh usable (`DER`). When the state of charge falls below 20%, the node drops to ULP scanning; below 5% it stops and its map state becomes "low power".

### 5.14 Evaluation and statistics

**M44 — Wilson interval** for a detection rate $\hat p = k/n$ at $z = 1.96$:

$$
\frac{\hat p + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}
$$

**M45 — Exact Poisson interval** for $k$ false incidents: lower $= \tfrac12\chi^2_{0.025}(2k)$, upper $= \tfrac12\chi^2_{0.975}(2k+2)$, then scale to per month.

**M46 — Counting rules** (must match the report):

- *Incident merging:* alarms within 60 minutes and within $2R$ of an existing incident's nodes join that incident.
- *Detection:* a fire counts as detected if a confirmed alarm involving a node within 150 m of the ignition occurs within 3 hours; latency is the time from ignition to that alarm.
- *False incident:* an incident with no fire within 150 m and 3 hours.
- *Test protocol:* per seed, 14 days calibration, 14 days tuning, 30 days test; fires injected at 6-hour slots in the test period with probability 0.8 on dry days and 0.2 on wet days; the quiet pass (no fires) measures false alarms, the fire pass measures detection.
---

## 6. Dashboard specification

### 6.1 Technology and data sources

- React 18, TypeScript, Vite; Apache ECharts for charts; zustand for state. The map is plain SVG (nodes, links, interfaces, fires) plus one HTML canvas layer for the plume heat overlay. No map tiles or GIS libraries, so it works offline.
- One `FrameSource` interface with two implementations:
  - `RecordingSource` reads `recordings/*.prs.jsonl(.gz)` from disk or a file picker. Built in Phase 0.
  - `LiveSource` connects to the server's WebSocket. Added in Phase 6.

  Every view consumes `FrameSource` only, never a specific implementation.
- Run with `npm run dev` locally. A static build (`npm run build`) must open recordings without any server, for the offline demo.

### 6.2 Views

**View 1 — Command Map** (the hero screen, always visible):

- Forest canvas, with a fuel or tree-density texture from the header, and ignition interfaces drawn as styled polylines: path, village, road, power line.
- Nodes as glyphs coloured and shaped by state (§6.3); gateways; radio links, with animated dots for packets once Phase 8 is done.
- Wind arrow with speed; plume heat overlay; fire markers with a growing perimeter.
- **Satellite pixel overlay** toggle: a 375 m square grid drawn over the network, with the caption "one satellite pixel ≈ 29 node cells at 70 m" (`DER`).
- Header strip: scenario name, simulated clock, day type (dry/busy or wet/quiet), current prior and the **required quorum** ("today: 2 nodes must agree"), and a permanent **SIMULATION** badge.
- Time controls: play/pause, speed (×1, ×10, ×60, ×600), step one tick, scrub bar with event markers (ignitions, candidates, alerts).

**View 2 — Node Inspector** (drawer opened by clicking a node):

- Stacked, time-aligned charts: raw reading; TTC slow baseline and fast residual; QCC p-value on a log axis with the floor line $p_{min}$; CUSUM $G_t$ with the threshold $h$; health weight $c_i$.
- Badges: node type, calibration size $n$, $p_{min}$, state of charge.

**View 3 — "Why this alarm"** (opens on any candidate or alert, built from the evidence trace):

- SCMR gauge: local rate versus network rate, and the ratio against 3.
- Fisher: the cluster's nodes, their p-values and the combined $p_C$.
- Prior breakdown: $\lambda$ (people) × $p_s$ (fuel dryness) = $\pi$.
- Bayes bar: posterior odds against the cost threshold, with a pass/fail marker.
- The template-generated explanation sentence.
- Escalation ladder: WATCH → CANDIDATE → CONFIRMED → ESCALATED, current level lit.

**View 4 — Race timeline** (the "aha" strip under the map):

- Horizontal timeline from ignition. Markers for the first node candidate, PRAHARI confirmation, the next satellite overpass and the satellite alert (overpass plus processing).
- Deltas are labelled, such as "PRAHARI confirmed 71 min before the satellite alert". Every label carries the `SIM` tag.

**View 5 — Mechanism switches** (the live ablation panel):

- Toggles for TTC, QCC, SCMR, RAQ and SRP (real ↔ stub), using the module-state mechanism.
- Live counters for the current run: false alarms so far, fires detected, median latency.
- In replay mode the toggles switch between pre-recorded variants of the same scenario and seed. In live mode they reconfigure the running engine.
- Demo moment: turn off SCMR during a haze episode and watch false alarms appear.

**View 6 — Results** (charts from `results/`, each with a footer listing seeds, days and the `SIM` tag):

- False incidents per month by pipeline, with 95% intervals (M45).
- Ablation: false alarms with intervals, plus confirmation labels.
- Operating dial: false alarms against median latency, one point per target rate.
- Node spacing: single-node alerts and confirmations at 70, 100 and 150 m.
- Learning curve (M36) and calibration maturity (M26).
- Energy per day, log scale (M41).

**View 7 — Module health and model card:**

- A table of every module: state (`real`, `stub`, `off`, `degraded`), version, mean step time, last error.
- The model card: each model's equation number, key parameters and provenance tag. This is what a judge sees when asking "what is simulated and what is assumed?"

**View 8 — Regime and scenario selector:** India, Canada, USA and Australia cards, a scenario list, and the seed.

### 6.3 Visual language

Screen theme: dark control-room, consistent with the poster's typography and accents.

| Token | Hex | Use |
| --- | --- | --- |
| bg | #0E1113 | Page background |
| panel | #161B1F | Cards and drawers |
| line | #2A3238 | Borders and gridlines |
| text | #E8E3DA | Primary text |
| text-2 | #A8A29A | Secondary text (must pass 4.5:1 contrast on the panel) |
| ember | #F26A2E | PRAHARI, candidates, alarms |
| pine | #2FA38A | Healthy nodes, verified results |
| amber | #E0B341 | Elevated and WATCH |
| grey | #7E8790 | Baselines, faults, disabled |

**Fonts:** Barlow Condensed for headings and large numbers, IBM Plex Sans for UI text, IBM Plex Mono for values and tags. Bundle the fonts locally for offline use.

**Node glyphs** (never distinguished by colour alone):

| State | Glyph |
| --- | --- |
| Normal | Small pine dot |
| Elevated | Amber ring |
| Candidate | Ember dot with a slow pulse |
| Confirmed member | Ember dot with a halo |
| Fault | Grey ×, with health below 0.5 |
| Low power | Hollow circle |

**Motion:** pulses at 1 Hz; packets travel along links in 400 ms; plume heat fades in and out over 300 ms; no motion faster than that. Respect a "reduce motion" toggle.

**Layout:** map on the left (60%), inspector or why-panel on the right (40%), race timeline across the bottom. Everything must be readable on a 1920 × 1080 projector from 3 m: minimum 14 px UI text, 20 px chart labels in presentation mode.

### 6.4 Presenter mode

- Full-screen toggle (F).
- Keys 1–9 jump to the storyboard steps in §11, each loading a recording at a bookmarked tick.
- Space plays and pauses. S toggles SCMR and R toggles RAQ (replay variants).
- A small on-screen caption area shows one line per step, editable in a JSON file.

### 6.5 Performance

- 60 frames per second map rendering for up to 400 nodes.
- Recordings of a two-day scenario under 50 MB compressed.
- Playback decimates frames when speed exceeds ×60 but never skips event ticks.

---

## 7. Phased delivery plan

Each phase ends with a runnable dashboard and passing tests. Phases 0–6 are the **minimum viable demo**. Phases 7–10 add depth and can be done in any order after 6, or skipped.

```text
0 ─► 1 ─► 2 ─► 3a ─► 4 ─► 5 ─► 6 ─┬─► 7  (experiments, results page)
                 └─► 3b (optional)  ├─► 8  (comms + energy)
                                    ├─► 9  (regimes, satellite race, learning, faults)
                                    └─► 10 (demo hardening — always do last)
```

A **session** below means one focused working session of an agent (roughly 1–3 hours). Timeboxes are ceilings. On hitting one, apply the escape hatch.

### Phase 0 — Foundation and replay shell

- **Goal:** the whole framework exists with stubs everywhere, and the dashboard plays a recording.
- **Build:**
  - `core/`: contracts, registry, config loader with schema validation, RNG streams, clock, runner with failure isolation (P5), health, trace, and recording writer/reader.
  - Stubs for every module in §4.2.
  - CLI: `prahari run --config configs/scenarios/smoke.yaml --out recordings/smoke.prs.jsonl.gz`.
  - Dashboard: Vite app with `RecordingSource`, the Command Map (static nodes on a blank forest), time controls, the module-health view and the SIMULATION badge.
  - Files: `PROGRESS.md`, `DECISIONS.md`, `KNOWN_ISSUES.md`.
- **Acceptance:**
  1. `pytest` passes.
  2. The smoke scenario runs one simulated day in under 5 s.
  3. The same seed gives a byte-identical recording.
  4. The dashboard opens the recording and plays it.
  5. Forcing one stub to raise an exception marks it `degraded` without stopping the run.
- **Demo value:** a map of a deployed network, playing.
- **Timebox:** 2 sessions.

### Phase 1 — World, network and siting

- **Goal:** a believable forest with interfaces and three deployment layouts.
- **Maths:** M1, M2, M3 (static $\lambda$ map), M4 (greedy siting), M38 without shadowing (link lines and spreading factors).
- **Dashboard:** interface layers; toggle between grid, corridor and greedy layouts with the percentage of ignition likelihood covered; gateway links coloured by spreading factor; satellite pixel overlay.
- **Acceptance:**
  1. Greedy siting covers at least as much likelihood as the grid at equal node count.
  2. Unit tests pass for the distance fields and M38 (100 dB at 200 m, 120 dB at 400 m).
- **Stub fallback:** grid layout only.
- **Timebox:** 2 sessions.

### Phase 2 — Weather, fuel moisture and sensor signals

- **Goal:** realistic sensor streams.
- **Maths:** M5, M6, M7 (with verification), M17 legacy, M18, M19, M20.
- **Dashboard:** weather strip (T, RH, wind, FFMC); node inspector with the raw reading; a small-multiples panel of eight nodes.
- **Acceptance:**
  1. Signal statistics match defaults: the AR(1) lag-1 correlation is 0.95 ± 0.02; nuisance event counts are within Poisson 95% bounds.
  2. M6 test: RH ≈ 29% at T = 30 °C and dew point 10 °C.
  3. The M7 test against `cffdrs` reference values either passes, or M7 is parked as a stub and logged.
- **Escape hatch:** if M7 cannot be verified, `ffmc: stub` (constant 85, or a scenario-scripted daily value) — nothing downstream breaks.
- **Timebox:** 2 sessions.

### Phase 3a — Fires and plumes, legacy

- **Goal:** fires appear, smoke reaches nodes, and the map comes alive.
- **Maths:** M8 (scripted and Poisson ignitions), M9, M12, M13, M16.
- **Dashboard:**
  - fire markers
  - plume heat overlay from the coarse grid
  - node glyphs that brighten with signal
  - the wind arrow driving the plume direction
- **Acceptance:**
  1. A node 50 m straight downwind of a full-grown fire receives 2.5 ± 0.1 su (before intermittency).
  2. A node at the same distance directly upwind receives 0.25 ± 0.02 su.
  3. Arrival delay equals distance over wind speed.
- **Timebox:** 2 sessions.

### Phase 3b — Gaussian plume (optional upgrade)

- **Goal:** replace the legacy plume with physics that scientists recognise, behind the same interface.
- **Maths:** M11, M14, M15, `calibrate_q()`.
- **Acceptance:**
  1. The calibrated concentration 50 m downwind equals the legacy value.
  2. The crosswind profile is Gaussian with the tabulated $\sigma_y$.
  3. Switching `plume: real` or `plume: stub` works live.
- **Escape hatch:** keep `plume: stub` (legacy); golden tests always run in legacy mode anyway.
- **Timebox:** 1–2 sessions.

### Phase 4 — Baselines and evaluation harness

- **Goal:** the "old way" runs, and the simulator can measure performance.
- **Maths:** M22, M23, M44, M45, M46, and the test protocol.
- **Build:** `prahari experiment --pipelines P0,P1 --seeds 11,22,33,44,55`, writing `results/*.json`. Dashboard results view v1 with the false-alarm chart.
- **Acceptance:**
  1. P0 and P1 reproduce the report's false-alarm rates within their 95% intervals in legacy mode (§9.3).
  2. The M44 and M45 unit tests pass.
- **Demo value:** "here is how often the old approaches cry wolf".
- **Timebox:** 2 sessions.

### Phase 5 — PRAHARI node layer

- **Goal:** calibrated node evidence.
- **Maths:** M24 (with freeze cap), M25, M26, M27, M28, and the P1t tuning.
- **Dashboard:** full node inspector (residual, p-value with floor, CUSUM with $h$); candidate pulses on the map.
- **Acceptance:**
  1. QCC exceedance on held-out quiet data is within 0.8–2.0% at nominal 1%.
  2. Replay-tuned $h$ gives 1 ± 0.5 node-local false candidates per node per 30 days on held-out quiet days.
  3. Replacing TTC with its stub reproduces v1's lock-up and daily-cycle leakage in a unit test.
- **Timebox:** 2 sessions.

### Phase 6 — PRAHARI edge layer, trace and live mode

- **Goal:** the complete decision core with explanations; live engine connection.
- **Maths:** M30, M31, M32, M33 (legacy day-type prior first), M34 (legacy quorum first, then the Bayes form), M35.
- **Build:**
  - Evidence traces; the why-panel; escalation ladder; mechanism switches.
  - Server: FastAPI with `GET /scenarios`, `POST /run` (starts a live run), WebSocket `/frames`, `GET /health`, `POST /modules` (switch states).
  - `LiveSource` in the dashboard.
- **Acceptance:**
  1. P2 reproduces the report's numbers within intervals in legacy mode (§9.3).
  2. The legacy and Bayes forms of RAQ agree on the worked example: 2 nodes on dry days, 3 on wet days.
  3. Every alert has a complete trace.
  4. The dashboard works in both replay and live mode.
- **Demo value:** the **complete minimum viable demo**.
- **Escape hatch:** if live mode misbehaves, ship replay-only; it is sufficient for the conference.
- **Timebox:** 3 sessions.

### Phase 7 — Experiments and results

- **Goal:** reproduce and extend the report's evaluation from the simulator.
- **Build:** experiment presets for ablation, operating dial, spacing sweep and seed sweeps; `results/summary.json` in the report's table format; the full results view.
- **Acceptance:**
  1. The golden-number tests pass (§9.3).
  2. Charts render from files, never from hard-coded arrays.
  3. Each chart shows seeds and days.
- **Timebox:** 2 sessions.

### Phase 8 — Communications and energy (optional)

- **Goal:** show IAS-relevant engineering depth.
- **Maths:** M38 with shadowing and SF selection, M39, M40, TS011 relay, store-and-forward; M41, M42, M43.
- **Dashboard:** packet animation; per-node state-of-charge gauges; energy chart comparing MQ-2 and BME688.
- **Scenarios:** gateway outage; three cloudy days.
- **Acceptance:**
  1. M39 matches reference values: 61.7 ms at SF7 and 1,482.8 ms at SF12 for 24 bytes.
  2. The ALOHA success rate in a synthetic load test is within 3 percentage points of $e^{-2G}$.
  3. A 0.5 Wh-per-day node with no sun lasts 9 ± 0.5 days.
- **Escape hatch:** `comms: stub` and `energy: stub` (perfect link, infinite energy); nothing else changes.
- **Timebox:** 2 sessions.

### Phase 9 — Regimes, satellite race, learning loop and faults (optional, high "aha")

- **Goal:** the four fire regimes, the satellite comparison, a system that visibly improves with evidence, and graceful handling of faulty sensors.
- **Maths:** M3 in full, including the lightning term; M33 integral prior; M37; M36 with learning curves; M21 faults; M29 health weights; the lightning-aware SCMR relaxation.
- **Dashboard:** regime selector; race timeline; learning-curve and maturity charts; fault glyphs with the health weight dropping to zero ("this sensor abstains").
- **Acceptance:**
  1. The satellite race timeline reports correct deltas on scripted fires.
  2. The learning curve is monotone within noise from K = 5 to K = 100.
  3. A stuck sensor's health weight falls below 0.1 within 90 minutes.
- **Escape hatch:** each sub-feature is separate; park any that fails.
- **Timebox:** 3 sessions.

### Phase 10 — Demo hardening (always last)

- **Goal:** a demo that cannot fail on stage.
- **Build:**
  - Record every storyboard scenario (§11), plus the replay variants for the mechanism switches.
  - Presenter mode (§6.4).
  - A static dashboard build that opens recordings without a server.
  - A one-command launcher script for each operating system.
  - `DEMO_CHECKLIST.md`.
- **Acceptance:**
  1. Laptop in airplane mode: the static build opens and plays all storyboard steps.
  2. A full rehearsal of §11 takes 3 minutes or less.
  3. No console errors.
- **Timebox:** 1–2 sessions.

---

## 8. Scenarios and Regime Cards

### 8.1 Regime Card (India example)

```yaml
regime: india
label: "India — Terai and dry deciduous"
weather: {t_mean: 30, t_amp: 7, dew_point: 10, wind_median_ms: 1.5, prevailing_dir_deg: 250, rain_prob_day: 0.02}
ignition:
  weights: {path: 1.0, village: 1.5, road: 1.0, power_line: 0.5}
  decay_m: {path: 30, village: 150, road: 50, power_line: 20}
  activity: "day_high_night_low"
  lightning: false
fuel_model: {code: "ffmc", a: -21, b: 0.25, note: "shape only; refit to FSI fire records"}
radio: {plan: "IN865"}
haze: {base_rate_per_10d: 1.0, crop_burning_multiplier: 3.0}
alert_format: "fsi_kml"
sources: {ignition_share: "LIT [17]", fuel_model: "ASM, form LIT [10]"}
```

The Canada card enables lightning and uses native FFMC; the USA card weights roads and power lines and uses `US915`; the Australia card uses `AU915`.

### 8.2 Scenario catalogue

| Scenario | Regime | What it shows | Phase needed |
| --- | --- | --- | --- |
| `smoke` | any | Framework only | 0 |
| `quiet_week` | India | No fires; baselines cry wolf, PRAHARI stays calm | 4, 6 |
| `dry_afternoon_ignition` | India | Fire near a footpath; two nodes confirm | 6 |
| `wet_morning_haze` | India | Haze episode; SCMR holds at WATCH; three nodes needed | 6 |
| `crop_burning_plus_fire` | India | Regional smoke plus a real local fire; the fire still stands out | 6 |
| `sensor_fault` | India | Stuck sensor abstains; no false alarm | 9 |
| `power_line_corridor` | USA | Corridor siting along a distribution line; utility operations alert | 1, 6 |
| `lightning_storm` | Canada | Several simultaneous fires; separate clusters | 9 |
| `gateway_outage` | India | Store-and-forward; the edge still decides locally | 8 |
| `satellite_race` | India | Ignition at 14:00; PRAHARI against the next pass | 9 |
| `spacing_70_100_150` | India | Confirmation falling with spacing | 7 |

Scenario files list scripted ignitions (time, x, y), haze windows, faults, module states and recording decimation.

---

## 9. Testing strategy

### 9.1 Test layers

| Layer | Where | What | When |
| --- | --- | --- | --- |
| Unit | `tests/unit/` | Every M-equation against hand-computed values (§9.2) | Every change |
| Contract | `tests/unit/test_contracts.py` | Every stage's real and stub outputs validate against contracts | Every change |
| Isolation | `tests/unit/test_runner.py` | A deliberately failing module degrades to stub; the run completes | Every change |
| Determinism | `tests/smoke/` | The same seed gives an identical recording hash | Every change |
| Golden | `tests/golden/` | Legacy-mode reproduction of report numbers (§9.3) | Phases 4, 6, 7 and before any demo |
| Dashboard | `dashboard/` (Vitest) | Recording parser; the `FrameSource` interface | Every dashboard change |
| Demo | `DEMO_CHECKLIST.md` | Manual rehearsal in airplane mode | Phase 10 and before travel |

### 9.2 Reference values for unit tests

| Equation | Input | Expected |
| --- | --- | --- |
| M6 | T = 30 °C, dew point 10 °C | RH ≈ 28.9% |
| M8 | FFMC 84, a = −21, b = 0.25 | 0.5 |
| M13 | φ = 0, π/2, π | 1.0, 0.325, 0.1 |
| M23 | k = 0.5, ARL 43,200 | h ≈ 8.8 |
| M26 | n = 1,000 | p_min = 1/1001 |
| M32 | two p-values of 6.9 × 10⁻⁴ | p_C ≈ 7.4 × 10⁻⁶ |
| M32 | three p-values of 6.9 × 10⁻⁴ | p_C ≈ 8.6 × 10⁻⁸ |
| M34 | BF bound needed 100 | p ≈ 4.8 × 10⁻⁴ |
| M34 | BF bound needed 10⁴ | p ≈ 2.9 × 10⁻⁶ |
| M38 | d = 200 m, 400 m, no shadowing | 100 dB, 120 dB |
| M39 | 24 B, SF7, 125 kHz, CR 4/5 | 61.7 ms |
| M39 | 24 B, SF12, 125 kHz, CR 4/5, DE on | 1,482.8 ms |
| M43 | 2 × 3000 F, 2.7 V → 1.35 V | ≈ 4.56 Wh |
| M44 | 272 of 328 | 82.9% (78.5–86.6%) |
| M45 | 32 incidents in 150 days | 6.4 per month (4.4–9.0) |

### 9.3 Golden numbers (legacy mode)

Configuration: legacy models (M9, M12, M17 linear, M33 day-type prior, legacy RAQ), 100 nodes at 70 m, seeds 11, 22, 33, 44 and 55, and the test protocol in M46. Pass if each point estimate falls within the report's 95% interval. On failure, record the difference in `DECISIONS.md` with the suspected cause, such as random-stream ordering. `reference/prahari_simulation.py` is the oracle to compare against.

| Pipeline | False incidents per month (report 95% CI) | Confirmed within 3 h |
| --- | --- | --- |
| P0 fixed threshold | 291 (277–307) | 95% (93–97) |
| P1 v1 as written | 132 (123–143) | 99% (98–100) |
| P1t v1 replay-tuned | 18.6 (15.0–22.8) | 59% (53–64) |
| P2 PRAHARI | 6.4 (4.4–9.0) | 83% (79–87) |
| P2 minus QCC | 17.4 (13.9–21.5) | 78% |
| P2 minus TTC | 11.8 (9.0–15.2) | 66% |
| P2 minus SCMR | 12.0 (9.2–15.4) | 84% |
| P2 minus RAQ | 10.0 (7.4–13.2) | 88% |

Spacing (3 seeds): confirmed within 3 h 85% at 70 m, 56% at 100 m, 13% at 150 m.

Advanced models (Gaussian plume, fault injection, full prior) produce **new** numbers, reported separately and never mixed with the golden set.

---

## 10. Risk register and fallback matrix

| Module or area | Risk | Symptom | Fallback (no other change needed) |
| --- | --- | --- | --- |
| FFMC (M7) | Transcription error | Unit test mismatch against `cffdrs` | `ffmc: stub`; scripted daily FFMC |
| Gaussian plume (M11) | Near-field blow-up | NaN or extreme values within 10 m | `plume: stub` (legacy M12) |
| QCC | Memory or speed | Step time over 5 ms | Reduce bins or window; else `qcc: stub` (Gaussian) |
| CUSUM tuning | Bisection does not converge | h at the search cap | Use the report's tuned h from configuration; log it |
| SCMR | Suppresses real simultaneous fires | Missed fires in the lightning scenario | Disable relaxation; document as a known limitation |
| Bayes RAQ | Unstable at tiny p-values | Overflow in $p\ln p$ | Clip p to 10⁻³⁰⁰; else legacy quorum |
| Learning loop | Too few labelled windows | Unstable coefficients | Require K ≥ 10; keep the bound |
| Comms | Slow event simulation | Tick over 50 ms | `comms: stub` |
| Energy | Unrealistic drain | Nodes die on day 1 | Check units; else `energy: stub` |
| Live server | WebSocket drops | Dashboard freezes | Replay mode (P8) |
| Dashboard plume canvas | Low frame rate | Under 30 fps | Coarser grid; update every 10 ticks |
| Recording size | Files too large | Over 50 MB | More decimation; drop the plume grid on non-event ticks |

---

## 11. Conference demo storyboard (about 3 minutes)

| Step | Key | Recording and tick | What the audience sees | Line to say |
| --- | --- | --- | --- | --- |
| 1 | 1 | `dry_afternoon_ignition`, start | A Terai-style forest; nodes along footpaths and a village edge; the satellite pixel overlay on | "One satellite pixel covers about 29 of our node cells." |
| 2 | 2 | `quiet_week`, ×600, with P0 shown | Fixed-threshold alarms popping up everywhere | "This is how cheap sensors behave with fixed thresholds — hundreds of false alarms a month." |
| 3 | 3 | `wet_morning_haze`, at the haze tick | Many nodes turn amber; SCMR gauge below 3; held at WATCH | "Haze lifts every node. PRAHARI rejects what's common to the whole network." |
| 4 | 4 | Same, with SCMR switched off (variant) | False alarms flood in | "Switch that mechanism off, and here's what you get." |
| 5 | 5 | `dry_afternoon_ignition`, ignition tick | Fire starts by the path; plume drifts downwind; two nodes pulse, then confirm | "On a dry, busy afternoon, Bayes' rule needs just two nodes." |
| 6 | 6 | Same, why-panel open | SCMR ratio, Fisher p, prior breakdown, posterior against threshold, explanation | "Every alarm explains itself." |
| 7 | 7 | Same, race timeline | PRAHARI confirmation marker well before the satellite alert marker | "The satellite hasn't even passed yet." |
| 8 | 8 | Results view | False-alarm chart and ablation | "In simulation, 45× fewer false alarms — and removing any mechanism makes it worse." |
| 9 | 9 | Module health and model card | Every model, equation and assumption listed | "Everything here is simulated, and here are the assumptions." |

---

## 12. Prompt pack for coding agents

Copy these into Claude Code (or another agent), replacing `N` with the phase.

**Session start**

```text
Read CLAUDE.md, PROGRESS.md and KNOWN_ISSUES.md. Then read docs/SPEC.md sections 2, 4 and the Phase N section in 7, plus every equation that phase references in section 5. Summarise in five bullets what you will build, which files you will create or change, and which acceptance tests you will make pass. Do not write code until I say go.
```

**Build a phase**

```text
Implement Phase N of docs/SPEC.md. Follow CLAUDE.md strictly: stubs stay, contracts are additive only, no changes to accepted phases' modules. Cite M-numbers in comments. Write the unit tests from section 9.2 that apply to this phase first, then the implementation. Run the full test suite. Stop when the Phase N acceptance tests pass, update PROGRESS.md, and show me the dashboard change I should look at.
```

**When stuck**

```text
You have tried three times and the Phase N acceptance test for <module> still fails. Apply the escape hatch from CLAUDE.md: set <module> to stub in configs/default.yaml, record the symptoms and your best diagnosis in KNOWN_ISSUES.md, make sure the full suite and the dashboard still run, then continue with the next item in Phase N.
```

**Review before accepting a phase**

```text
Review the changes for Phase N against docs/SPEC.md. Check: (1) every stage has a working stub; (2) no accepted contract field was renamed or removed; (3) every equation cites its M-number and every parameter has a source; (4) the same seed gives an identical recording; (5) one forced module failure degrades gracefully. List any violations and fix them.
```

**Record the demo**

```text
Using the scenarios in docs/SPEC.md section 8.2 and the storyboard in section 11, generate every recording needed for presenter mode, including the SCMR-off variant for step 4. Verify each opens in the static dashboard build with no server running. Write DEMO_CHECKLIST.md.
```

---

## 13. Appendices

### 13.1 Reference numbers

Bracketed numbers such as `[17]` refer to the reference list in the FIRENET–PRAHARI technical report. The ones used most here:

| Ref | Source |
| --- | --- |
| [3] | Chan et al., ANU, 2023: ground-sensing experiments (directional loss, 50 m detection, forest path loss) |
| [10] | Beverly & Wotton, 2007: logistic sustained-flaming models |
| [15] | cffdrs documentation: FWI start-up values and their limits |
| [16] | Van Wagner (1987); Van Wagner & Pickett (1985): FFMC |
| [17] | Forest Survey of India: overpass times, processing delay, human-caused share |
| [33] | Bosch BME688 datasheet |
| [34] | Winsen / Hanwei MQ-2 specifications |
| [37] | Inductive conformal anomaly detection (Laxhammar & Falkman, via CODiT) |
| [41] | Sellke, Bayarri & Berger, 2001: p-value calibration |
| [42] | LoRa Alliance TS011 relay specification |

### 13.2 Glossary

| Term | Meaning |
| --- | --- |
| Stage or module | One step of the pipeline, with `real` and `stub` implementations |
| Stub | Simple, always-working fallback implementation |
| Contract | Typed data structure passed between stages |
| Recording | File of frames and evidence traces that the dashboard replays |
| Evidence trace | Record of every number behind a candidate or decision |
| Legacy mode | Models and parameters that reproduce the report's simulation |
| TTC, QCC, SRP, RAQ, SCMR | The five PRAHARI mechanisms |
| Regime Card | Per-region parameter set: ignition layers, fuel model, radio plan, haze, alert format |
| su | Sensor units: normalised gas-sensor scale |

### 13.3 Definition of done for the whole project

1. Phases 0–6 and 10 accepted.
2. Golden tests pass in legacy mode.
3. The storyboard runs in airplane mode in 3 minutes or less.
4. The model card lists every assumption.
5. `KNOWN_ISSUES.md` honestly lists anything parked.
