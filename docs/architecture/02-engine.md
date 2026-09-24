# Architecture 2 — the engine

The engine is the Python package `engine/prahari/` (NumPy, SciPy, PyYAML; pytest for tests). This page walks through
it from the outside in.

## Package layout

```text
engine/prahari/
├── cli.py                  `prahari run` and `prahari experiment`
├── stages.py               imports every stage module so they register themselves
├── core/                   the framework (no science in here)
│   ├── registry.py         Stage base class, @register(name, kind), lookup and build
│   ├── runner.py           Slot: the isolation wrapper around every stage call
│   ├── config.py           load, merge and validate YAML (unknown keys and untagged parameters are errors)
│   ├── rng.py              one NumPy Generator per module, spawned from the master seed
│   ├── clock.py            ticks, minutes, time of day
│   ├── context.py          RunContext: positions, distances, neighbours, current tick, shared per-tick values
│   ├── contracts*.py       stage output data classes and their validators
│   ├── pipeline.py         Simulation: setup, the tick, frames, events, traces, the run loop
│   ├── health.py, trace.py module health records; evidence-trace records
├── world/                  landscape (M2–M3), siting (M1, M4), geometry
├── env/                    weather (M5–M6), ffmc (M7)
├── fire/                   ignition (M3 with lightning, M8), growth (M9), plume (M12 legacy), gaussian (M11, M14–M15)
├── sensors/                mox sensor (M17–M19), nuisance and haze (M20), faults (stub) and faults_real (M21, Phase 9)
├── detect/baselines/       fixed (P0, M22), v1 (P1, M23), v1t (P1t)
├── detect/prahari/         ttc, qcc, score, cusum (stubs) and ttc_real, qcc_real, cusum_real, tuning (Phase 5);
│                           cluster, scmr, fisher, srp, learn, raq, escalate (stubs) and edge_real, decide_real,
│                           escalate_real (Phase 6); score_real (M27 + M29) and learn_real (M36) (Phase 9)
├── comms/                  pathloss (M38 + shadowing, relays), lora (M39, M40 maths), lorawan (stub), lorawan_real (Phase 8)
├── energy/                 power (M41–M43 maths), budget (stub), budget_real (Phase 8)
├── satellite/              overpass (stub: fixed delay), race (M37 overpasses, Phase 9)
├── record/                 writer and reader of recordings, frame helpers, world header sections
└── eval/                   stats (M44–M46), experiments (harness), node_metrics (Phase 5),
                            offline (edge replay, dial), report (summary table) (Phase 7), energy_table (Phase 8),
                            learning (M36 learning curve, M26 maturity) (Phase 9)
server/                     optional live server: app.py (FastAPI), live.py (threaded run + LiveWriter)
```

## Stages and the registry

A **stage** is a class with `reset(ctx)` (clear per-run state) and `step(inputs, ctx)` (one tick), plus metadata for
the model card: `equation` (M-numbers), `tag` (provenance), `description`, and `snapshot()` (small state shown as
notes). Each module name has up to three registered classes:

```python
@register("qcc", kind="stub")   # always present; simple, cannot fail
@register("qcc", kind="real")   # the full model
@register("qcc", kind="off")    # module switched out (where allowed)
```

Real implementations live in their own files where the stub file is from an accepted phase (for example
`qcc_real.py` beside `qcc.py`), so accepted code is not edited.

## Isolation: the Slot

Every stage call goes through a `Slot` (`core/runner.py`). It builds the fallback chain
**real → stub → off → hold last valid output → the contract's neutral output**. If the running implementation raises
an exception, or returns output that fails its contract check (NaN, wrong shape, out of range), the slot moves one step
down the chain for the rest of the run, marks the module `degraded`, records the error once and adds a `degraded` event
to the frame. The run never stops. Step times are measured here and written to `*.health.json`, not to the recording,
so recordings stay byte-identical.

## Configuration

`config.py` merges `configs/default.yaml` with a scenario or preset file. Rules enforced on load:

- every key in an override must exist in the defaults, with the same type;
- every block under `params` must carry `source:` starting with LIT, VEN, DER, ASM or TGT;
- every module has a state, `real`, `stub` or `off`.

Top-level sections: `run` (seed, start, days, tick), `scenario`, `record` (frame interval, grids, `from_day`),
`world` (map, nodes, interfaces, gateways), `modules` (states), `params` (per-module parameters), `experiment`.

## Randomness

`core/rng.py` spawns one `numpy.random.Generator` per stream from `SeedSequence(seed)`. The stream list is
append-only (weather, ignition, growth, plume, sensor, nuisance, haze, faults, comms, satellite, protocol, srp, links,
energy), so adding a
module never changes the numbers other modules draw. Python's `random` and unseeded NumPy calls are not used.

## The tick

`Simulation` (`core/pipeline.py`) runs `prepare()` (setup stages, then `reset` on every tick stage) and then, for every
simulated minute:

1. `step_signals(t)`: weather → ffmc → ignition → growth → plume, nuisance, haze → sensor → faults.
2. `step_baselines(x)`: P0, P1 and P1t on the same readings.
3. `step_node(x)`: ttc → qcc → score → cusum. The TTC slow z is also put in `ctx.z_slow` for the common-mode rule.
4. `step_edge(t, env, fuel, cand)`: comms → srp → cluster → scmr → fisher → learn → raq → escalate (M30–M35);
   then energy — which receives the minute, the weather and this minute's packets — and satellite. The energy mode
   goes into `ctx.energy_mode` so that next minute's comms skips nodes that are off (Phase 8).
5. Events (ignitions, candidates, alarms, haze start, degradations) and evidence traces are collected, node display
   states are computed, and a frame dictionary is built.

`run()` writes every `record.every_k_ticks`-th frame plus every frame that has an event or alert, and the last one.
Packets from minutes between written frames are carried into the next written frame, each tagged with its own minute
`t`, so the packet animation loses nothing (Phase 8).
With `record.from_day` set (warm start), everything is simulated from day 0 but frames and traces are written only
from that day on; the header is written after the first recorded tick so its model card shows, for example, the tuned
threshold.

Per-node state is held in NumPy arrays; there are no Python loops over nodes inside the tick (CLAUDE.md rule 8). The
node layer costs about 0.3 ms per tick (SIM timing on the development machine).

## Communications and energy (Phase 8)

- **Links (setup).** `LinksReal` computes path loss to every gateway (M38). With `links.shadowing_sd_db` > 0 it adds a
  fixed X_σ per node–gateway and node–node pair from the `links` stream, keeps every gateway's closing SF (for
  re-routing) and picks a TS011 relay for each node without a direct link. `ctx.links` carries the result to comms.
- **Comms (`lorawan_real.py`).** Each minute: candidate frames and hourly heartbeats get a random start in the minute
  and a channel; `lora.collide` resolves overlaps on the same channel and SF with the capture rule; lost candidate
  frames retry after U(1, 10) s; relayed frames make a second hop from the relay; frames that finish after the
  minute, and later retries, are resolved and delivered in the next minute. During a gateway outage a node re-routes
  to another gateway if one closes, otherwise queues its candidate frames and sends them when the gateway returns.
  Only delivered candidates reach the edge, at the minute they arrive.
- **Energy (`budget_real.py`).** Each minute: half-sine solar harvest (cloudy days scaled), draw by power mode, radio
  energy for the node's packets, supercapacitor balance, then the mode for the next minute (ULP below 20%, off below
  5%, back on at 10%).
- **Defaults.** Both modules stay `stub` except in the Phase 8 scenarios, so every earlier result and recording is
  unchanged (checked frame by frame).

## Regimes, satellite, faults and learning (Phase 9)

- **Regime Cards.** `configs/regimes/<name>.yaml` sits between `default.yaml` and the scenario (`regime: canada`). It
  sets weather, interface weights, haze and the radio plan, and a `regime_card` block (name, label, radio plan, alert
  format, lightning) that the recording header copies as `regime`.
- **Arrival time.** The real comms stage fills `Delivered.t_detect`, the minute each delivered candidate was raised;
  the cluster stage windows candidates by that minute, so a frame delayed by the radio still meets its neighbours.
- **Lightning.** `IgnitionReal` turns scripted storms into Poisson strikes over a disc; each can ignite a fire in the
  forest. `ctx.storm` stays set until 180 minutes after a storm ends; the prior then carries `lightning`, and SCMR
  uses its relaxed ratio.
- **Satellite (`race.py`).** When a fire ignites, the whole overpass plan is drawn at once (which pass sees it, which
  misses, when the alert arrives) and published as a `satellite_plan` event for the race timeline.
- **Faults and health (`faults_real.py`, `score_real.py`).** Faults change the readings after the sensor stage; a
  dropout sets `Readings.missing` and holds the last value. The real score stage computes each node's health weight
  and zeroes the evidence of a node that abstains.
- **Learning (`learn_real.py`, `eval/learning.py`).** The learn stage now receives the clusters, SCMR and health
  weights as well as Fisher; with a fitted model file (K ≥ 10 burns) it returns the fitted likelihood ratio, otherwise
  the bound. The harness lists every cluster window of the protocol runs, fits the model for each K and compares the
  rules at a fixed false-alarm budget.
- **Defaults.** All of these stay `stub`, off or `legacy` by default and in the golden presets, so every earlier
  result and recording keeps identical frames.

## Robustness (release 1.0)

- **Configuration values.** Besides unknown keys, wrong types and missing `source` tags, the loader rejects values
  the simulator cannot run with, naming the key (`check_values`):
  - `run.days` ≤ 0, `run.tick_minutes` < 1;
  - `world.n_nodes` < 1, `world.spacing_m` ≤ 0;
  - an unknown layout, or a grid layout with a non-square node count;
  - a warm start outside the run, and `record.every_k_ticks` < 1.

  It also names unreadable files and invalid YAML with their line.
- **Atomic outputs.** Recordings, health files and every results JSON are written through `record.writer.write_atomic`: a
  temporary file in the same folder, then a rename. An interruption or a full disk leaves the previous file intact.
  The bytes written are unchanged.
- **The CLI never ends in a traceback.**
  - Configuration problems exit with 2, file problems with 1, and Ctrl-C with 130, each with one line on stderr.
  - `--seeds` and `--jobs` are checked by the argument parser.
  - Presets and the energy configuration are found from any folder.
- **Stage documentation convention.** Every registered stage class documents itself through class attributes read by
  the model card: `equation` (M-numbers), `tag` (provenance) and `description`. Its module docstring explains the
  model. Framework code, contracts, the evaluation code and the server carry docstrings.

## Live mode (Phase 6)

`server/live.py` runs a `Simulation` in a background thread through a `LiveWriter`, which has the same methods as the
file writer (`header`, `frame`, `trace`, `close`) but appends each line to a list that WebSocket clients read. Before
each recorded frame it applies queued module switches (`Simulation.switch_module` rebuilds that module's Slot) and
paces frames to the requested speed. `server/app.py` exposes `GET /scenarios`, `POST /run`, `GET /health`,
`POST /modules` and the WebSocket `/frames`. The engine never imports the server.

## The experiment harness

`eval/experiments.py` runs the M46 protocol headlessly, calling exactly the same `step_signals`, baseline and node
code but building no frames:

- per seed, a **quiet pass** (no fires) for false alarms, and a **fire pass** with protocol fires (every 6 hours in
  the test period, kept with probability 0.8 on dry days and 0.2 on wet days, drawn from the `protocol` stream);
- the same day types are written into the prior's `day_type_overrides`, so fires, prior and quorum share a calendar;
- pipelines are grouped by what they change: the baselines (P0, P1, P1t) and every P2 variant that differs only at
  the edge share one pair of passes; a node-layer ablation (P2-QCC, P2-TTC) swaps its module and gets passes of its
  own;
- during a pass with the node layer, `eval/offline.py`'s `ScoreRecorder` keeps each tick's node evidence
  S = −ln p, the share of nodes with slow z ≥ 3 and the node candidates;
- the edge is then **replayed offline** from those candidates through the same registered stages (`edge_stages`,
  `edge_alarms`), once per edge variant: P2, P2-SCMR (SCMR as stub) and P2-RAQ (RAQ as stub). A unit test checks
  that the offline P2 equals the live edge alarm for alarm;
- the **operating dial** re-tunes h (M28) from the recorded S for other false-candidate targets with the same
  bisection as the live tuner, replays the CUSUM (`cusum_replay`) and the edge, and pools each point like a
  pipeline;
- incidents and detections are counted with `eval/stats.py` (M44–M46);
- with `node_metrics`, `eval/node_metrics.py` also records QCC exceedance, node candidates and the tuned h;
- with `spacings`, the whole protocol repeats per node spacing;
- `--jobs N` maps seeds over N forked processes; each seed's streams come from its own master seed, so the result
  does not depend on N;
- output: `results/<preset>_seed<N>.json`, `results/<preset>.json`, and `results/summary.json`, which
  `eval/report.py` rebuilds after every preset: the golden preset is the primary table, the ablation pipelines
  join it, the spacing sweep and the 20-seed sweep are attached, and a `table` block lists every pipeline in the
  report's order beside the report's value (copied from `engine/tests/golden/report_reference.json`, the only place
  such numbers live).

## Adding a real module (the pattern used in every phase)

1. Write the maths as pure functions (arrays in, arrays out), each formula commented with its M-number.
2. Add a `real` class registered under the existing module name, in a new file if the stub's file is accepted.
3. Add its parameters to `configs/default.yaml` with a `source` tag; set the module state.
4. Import the file in `stages.py`.
5. Write unit tests with SPEC §9.2 values and, where the oracle has the same function, an identical-input
   cross-check.
6. Regenerate recordings, update the docs (CLAUDE.md rule 16).
