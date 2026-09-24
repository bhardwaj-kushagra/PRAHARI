# PROGRESS

| Phase | Title | Status |
| --- | --- | --- |
| 0 | Foundation and replay shell | accepted (2026-09-23) |
| 1 | World, network and siting | accepted (2026-09-23) |
| 2 | Weather, fuel moisture and sensor signals | accepted (2026-09-23) |
| 3a | Fires and plumes, legacy | accepted (2026-09-23) |
| 3b | Gaussian plume (optional) | accepted (2026-09-23) |
| 4 | Baselines and evaluation harness | accepted (2026-09-23) |
| 5 | PRAHARI node layer | accepted (2026-09-23) |
| 6 | PRAHARI edge layer, trace and live mode | accepted (2026-09-23) |
| 7 | Experiments and results | accepted (2026-09-23) |
| 8 | Communications and energy (optional) | accepted (2026-09-24) |
| 9 | Regimes, satellite race, learning loop and faults (optional) | accepted (2026-09-24) |
| 10 | Demo hardening | accepted (2026-09-24) |

Statuses: not started · in progress · awaiting review · accepted.

## Session log

### 2026-09-23 — Session 1

- Reviewed all documents and recomputed every §9.2 reference value; fixed spec errata E-1…E-5 (see `DECISIONS.md`). Spec is now 1.0.1 at `docs/SPEC.md`; the oracle scripts are in `reference/`.
- Built Phase 0:
  - Engine framework in `engine/prahari/core/`: contracts, registry, config loader (unknown keys and untagged parameters are errors), RNG streams, clock, health, trace, runner with failure isolation, tick loop.
  - A stub (and an `off` where SPEC §4.2 allows one) for all 23 modules, with M-number comments; every module is `stub` in `configs/default.yaml`.
  - Deterministic gzipped recordings, `prahari run`, smoke scenario, committed `recordings/smoke.prs.jsonl.gz`.
  - Dashboard (`dashboard/`): `FrameSource` + `RecordingSource`, Command Map, time controls with event markers, module health and model card, node readout, alerts with template explanations, SIMULATION badge and seed/days footer.

**Phase 0 acceptance (all pass):**

| # | Test | Result |
| --- | --- | --- |
| 1 | `pytest engine/tests` | 52 passed |
| 2 | Smoke scenario, 1 simulated day | ~1.6 s (limit 5 s) |
| 3 | Same seed → byte-identical recording | identical SHA-256; different seed differs |
| 4 | Dashboard opens and plays the recording | Vitest 7 passed; static build checked in Chromium: clock advances, 100 nodes, fire and confirmation shown, no console errors |
| 5 | Forced stub exception → `degraded`, run completes | `test_runner.py` (exception, NaN output, required module); also shown in the dashboard health table |

**Next step:** review and accept Phase 0, then Phase 1 — world, network and siting (M1–M4, M38 without shadowing).


### 2026-09-23 — Session 2 (Phase 1)

- Phase 0 accepted by the developer ("good enough").
- Built Phase 1 — world, network and siting:
  - Three setup modules that run once before the first tick, each with a stub, through the same isolation wrapper:
    `landscape` (M2 distance fields + M3 static intensity; stub uniform), `siting` (M1 grid and corridor, M4 greedy;
    stub grid only) and `links` (M38 without shadowing; stub perfect SF7 link).
  - A 1400 m Terai-style landscape in `configs/default.yaml`: village, two footpaths, road, power line; grid centred.
  - Header additions (additive to `prahari.frame/1`): interfaces, ignition-likelihood grid, all three layouts with
    covered likelihood, per-node links, detection radius and satellite pixel size.
  - Dashboard: layout toggle with coverage (and a hollow-circle preview of non-simulated layouts), layer switches with
    legends for interfaces, likelihood, radio links by SF, detection radius and satellite pixels; link details in the
    node panel; coverage in the header strip.
  - New scenarios and recordings: `siting_corridor`, `siting_greedy` (same landscape, fire beside a footpath).

**Covered ignition likelihood, 100 nodes, r_d = 50 m (SIM, default landscape):** grid 24%, corridor 49%, greedy 83%.
Greedy leaves 35 nodes without a direct link to `g1` (they need the Phase 8 relay); grid links span SF7–SF11.

**Phase 1 acceptance (all pass):**

| # | Test | Result |
| --- | --- | --- |
| 1 | Greedy covers at least as much likelihood as the grid at equal N | `test_acceptance_1_*` on the default landscape and a synthetic one; greedy also ≥ (1 − 1/e)·optimum on a brute-forced instance |
| 2 | Distance fields and M38 (100 dB at 200 m, 120 dB at 400 m) | `test_m2_*`, `test_acceptance_2_m38_reference_values`, SF boundaries 746/828/919/1020/1112/1213 m |
| — | Full suite, determinism, speed | 75 engine tests, 11 dashboard tests; recordings byte-identical on rerun; 1 simulated day ≈ 1.3 s |
| — | Stub fallback | a failing or unbuildable real siting degrades to the grid and the run completes (`test_runner.py`) |

**Next step:** review and accept Phase 1, then Phase 2 — weather, fuel moisture and sensor signals (M5, M6, M7 with
`cffdrs` verification, M17 legacy, M18–M20).

### 2026-09-23 — Session 3 (Phase 2)

- Phase 1 accepted by the developer ("good").
- Built Phase 2 — weather, fuel moisture and sensor signals. Five modules are now `real` by default, each keeping its stub:
  - `weather` (M5 diurnal temperature with AR(1) noise, M6 Magnus humidity, lognormal wind, rain events),
  - `ffmc` (M7 daily FFMC at noon, **verified against the official cffdrs outputs**: 48 days within 0.005),
  - `sensor` (M18 composite reading, M19 AR(1) heteroscedastic noise, M17 linear response),
  - `nuisance` and `haze` (M20), with scenario-scriptable haze episodes.
- Spec erratum E-6: M7's moisture constant is 147.27723 (cffdrs), not 147.2 — the old value misses cffdrs by 0.12.
- Dashboard: new **Signals** tab (ECharts, loaded on demand) — weather strip (T, RH, wind, FFMC) plus haze level,
  node inspector (reading, haze bands), and eight-node small multiples on shared scales; time cursor, tooltips, SIM footer.
- New scenario and recording `signals_3day` (all signal modules real, scripted haze on day 2).
  `smoke` and the two `siting_*` scenarios keep clean stub signals so their stub detectors stay readable.

**Expected behaviour, not a bug:** with realistic signals the detection chain is still at its Phase 0 stubs (the v1
CUSUM with a nominal-ARL threshold), so in `signals_3day` it raises about 2,000 candidates a day (5,926 over three days) and the haze episode
lights the whole network. This is the report's P1 "v1 as written" failure. Real TTC/QCC/CUSUM (Phase 5) and SCMR
(Phase 6) address it.

**Phase 2 acceptance (all pass):**

| # | Test | Result |
| --- | --- | --- |
| 1a | AR(1) lag-1 correlation 0.95 ± 0.02 | `test_acceptance_1a_ar1_lag1_correlation` |
| 1b | Nuisance counts within Poisson 95% bounds | roadside and interior groups, 30 days × 100 nodes |
| 2 | M6: RH ≈ 29% at 30 °C, dew point 10 °C | 28.9% |
| 3 | M7 against cffdrs | max error 0.005 over 48 days (tolerance 0.1); M7 stays `real` |
| — | Full suite, determinism, speed | 90 engine + 16 dashboard tests; four recordings byte-identical on rerun; 1 day with all signals real ≈ 2.2 s |

**Next step:** review and accept Phase 2, then Phase 3a — fires and plumes, legacy (M8 scripted and Poisson
ignitions, M9, M12, M13, M16) and the map's fire and plume overlay.

### 2026-09-23 — Session 4 (Phase 3a)

- Phase 2 accepted by the developer ("good").
- Built Phase 3a — fires and plumes (legacy):
  - `ignition` is now `real`: scripted fires plus Poisson attempts drawn by thinning from the M3 likelihood map with a
    day/night activity profile, each sustained with M8 p_s(FFMC). `expected_fires: 0` (the default) keeps existing
    scenarios scripted-only. The legacy source (M9) and plume (M12, M13, M16) remain the stub/default models as SPEC §5
    prescribes; their upgrades are M10 (optional) and M11 (Phase 3b).
  - Recordings now carry a coarse plume grid (active plume model, 10 m, float16) every 5 ticks while fires burn, and the
    fire signal at every node (`nodes.conc`).
  - Dashboard: smoke overlay (log-scaled, one slate hue), nodes that glow with the smoke signal they receive, fire
    markers with a local wind arrow, legends.
  - New scenario and recording `fires_day` (4 expected Poisson fires plus one scripted, real weather, clean signals).

**Phase 3a acceptance (all pass, `engine/tests/unit/test_fires_phase3a.py`):**

| # | Test | Result |
| --- | --- | --- |
| 1 | 50 m straight downwind, full growth, before intermittency: 2.5 ± 0.1 su | 2.5 su through the growth and plume stages, and on the recorded grid |
| 2 | 50 m straight upwind: 0.25 ± 0.02 su | 0.25 su |
| 3 | Arrival delay = distance / wind speed | first non-zero tick = ⌊d/(60u)⌋ + 1 for three distance/speed pairs |
| — | M8 and Poisson ignition | p_s(84) = 0.5; sustained count within Poisson 95% bounds of the expected value; none in the village; clustered near interfaces; time of day follows a(t); wet fuel suppresses fires |
| — | Full suite, determinism | 101 engine + 20 dashboard tests; recordings byte-identical on rerun |

**Next step:** review and accept Phase 3a. Then Phase 3b (optional Gaussian plume, M11/M14/M15) or Phase 4 — baselines
and the evaluation harness (P0 fixed threshold, P1 v1, M44–M46, the first golden numbers).

### 2026-09-23 — Session 5 (Phase 3b)

- Phase 3a accepted by the developer ("good").
- Built Phase 3b — Gaussian plume: the `plume` module's real implementation (`fire/gaussian.py`) with M11 ground-reflected
  Gaussian plume, M14 Briggs σ by stability class (C by day, E at night), M15 sub-canopy wind, M16 delay x/u_c, and
  `calibrate_q()` (Q = 125.94, recorded in the model card as `notes`). The legacy M12 stays the stub and the default
  (it reproduces the report; M11 is marked advanced), and scenarios opt in with `modules.plume: real`.
- New scenario and recording `fires_day_gaussian`: the same seed, fires and weather as `fires_day`, only the plume
  model differs — switching recordings in the dashboard shows real vs stub on the same run. The smoke legend names the
  running plume model.

**Phase 3b acceptance (all pass, `engine/tests/unit/test_plume_phase3b.py`):**

| # | Test | Result |
| --- | --- | --- |
| 1 | Calibrated concentration 50 m downwind equals the legacy value | 2.5 su (class C, full growth, reference wind) |
| 2 | Crosswind profile Gaussian with the tabulated σ_y | C(y)/C(0) = exp(−y²/2σ_y²) at 0–2 σ_y, within 0.1% |
| 3 | Switching `plume: real` / `stub` works | both states run with identical fires; a failing Gaussian degrades to the legacy stub and the run completes |
| — | Risk register, M14, M15 | near-field values finite (< 50 su within 10 m); Briggs σ values; u_c = 0.4·u10 floored at 0.5; night class E stronger; delay x/u_c |
| — | Full suite, determinism | 110 engine + 20 dashboard tests; recordings byte-identical on rerun |

"Live" switching through the engine server arrives with Phase 6; in replay the two recordings are the switch.

**Next step:** review and accept Phase 3b, then Phase 4 — baselines (P0 fixed threshold M22, P1 v1 M23) and the
evaluation harness (M44–M46), with the first golden numbers from the report.

### 2026-09-23 — Session 6 (Phase 4)

- Phase 3b accepted by the developer ("good").
- Built Phase 4 — baselines and the evaluation harness:
  - `baseline_p0` (M22 fixed threshold, `detect/baselines/fixed.py`) and `baseline_p1` (M23 "v1 as written",
    `detect/baselines/v1.py`), each with a stub and an off, running after the sensor in every scenario; their alarms are
    recorded as `p0_alarm` / `p1_alarm` frame events.
  - `eval/stats.py` (M44 Wilson, M45 exact Poisson, M46 incident merging and detection) and `eval/experiments.py`
    (quiet pass + fire pass per seed, protocol fires from the new `protocol` stream).
  - `prahari experiment --preset golden` → `results/<preset>_seed<N>.json` and `results/summary.json` (committed).
  - Dashboard: **Results** tab (false incidents per month on a log axis with M45 intervals, per-seed ticks and the
    report's intervals as hollow diamonds; detection within 3 h with M44 intervals; table; seeds/days footer) and a
    **Baselines** map layer (P0 ▲, P1 ○ in grey for 30 simulated minutes).

**Phase 4 acceptance:**

| # | Test | Result |
| --- | --- | --- |
| 1a | P1 false incidents / month within the report's 123–143 (legacy mode, seeds 11, 22, 33, 44, 55) | **pass** — 136.2 (M45 CI 126.2–146.8) |
| 1b | P0 false incidents / month within the report's 277–307 | **miss** — 340.6 (324.6–357.2); statistical, not a code difference — see below and `DECISIONS.md` P4-6/P4-7 |
| 2 | M44: 272/328 → 82.9% (78.5–86.6); M45: 32 in 150 days → 6.4/month (4.4–9.0) | pass (`test_eval_phase4.py`) |
| — | M22, M23, M46 against the oracle's own functions on identical inputs | exact agreement (threshold, EWMA/CUSUM/refractory, confirmation, incident merging, detection) |
| — | Harness smoke, determinism, full suite | 120 engine passed + 2 golden skipped (run separately), 24 dashboard; recordings byte-identical on rerun |

Why P0 misses: false alarms are clustered (haze episodes, heavy-tailed bursts), so the seed-to-seed spread is far
wider than the report's pooled Poisson interval. The oracle itself over seeds 11–30 gives P0 321.9 ± 11.1 (mean ± SE)
per month; the report's 291 is a low 5-seed draw. Running our engine over the same 20 seeds gives P0 310.9 ± 15.9 and
P1 141.8 ± 2.1 — no detectable difference from the oracle (Welch p 0.58 and 0.40). Nothing was tuned.

**Next step:** review Phase 4. If the P0 explanation is accepted, Phase 5 — the PRAHARI node layer (M24 EWMA with
the freeze cap, M25–M28 and the P1t tuning), replacing the detection-chain stubs through the registry.

### 2026-09-23 — Session 7 (Phase 5)

- Phase 4 accepted by the developer ("good").
- Built Phase 5 — the PRAHARI node layer, as real stages beside the untouched stubs:
  - `ttc` real: M24 slow baseline with the 180-minute freeze cap (winsorised resumption) and M25 fast residual
    against the lagged 60–180-minute window mean, O(1) per tick.
  - `qcc` real: M26 conformal p-values per node and 4-hour bin; 14 calibration days, then frozen and searched with
    one vectorised binary search (optional 28-day sliding window).
  - `cusum` real: M28 CUSUM of −ln p with k = 1.5; h replay-tuned by bisection on the tuning days with common-mode
    periods excluded; `h_default` (DER) until tuned.
  - `baseline_p1t`: P1t, v1 with the capped slow z and h tuned by M28.
  - Harness: P1t pipeline and node metrics (`experiment.node_metrics`); `results/summary.json` gains a `node` block.
  - Dashboard: Node Inspector (reading and slow baseline, fast residual, p-value with its floor, CUSUM with h and
    candidates, health weight) and calibration badge in the Node tab; node-layer table in Results.
  - New scenario and recording `node_3day` (signals_3day plus a day-3 fire); `signals_3day` now runs the real node
    layer; framework scenarios keep the stub node layer.

**Phase 5 acceptance (golden seeds 11, 22, 33, 44, 55; details in `DECISIONS.md` P5-9…P5-11):**

| # | Test | Result |
| --- | --- | --- |
| 1 | QCC exceedance on held-out quiet data within 0.8–2.0% at nominal 1% | **pass** — 1.10% (per seed 0.61–1.58%); report simulation 1.54% |
| 2 | Replay-tuned h gives 1 ± 0.5 node-local false candidates per node per 30 d | **pass** — 0.65 (median 0.70); report simulation 1.70 on the same seeds |
| 3 | TTC stub reproduces v1's lock-up and daily-cycle leakage | **pass** — stub frozen for days after a +2 su step while the real TTC re-baselines; stub keeps 0.953 of a daily cycle (DER ωτ/√(1+(ωτ)²)), the fast residual 0.52 |
| — | M24, M25, M26, M28 and P1t against the report simulation on identical inputs | exact agreement |
| — | M26 reference value (n = 1000 → p_min = 1/1001), exchangeable-data exceedance, sliding window | pass |
| — | Failing real QCC degrades to its stub; the run completes | pass |
| — | Step time of the node layer (SPEC §10: < 5 ms) | ttc 0.06 + qcc 0.14 + score 0.05 + cusum 0.06 ms per tick |
| — | Full suite, determinism | 133 engine passed + golden run separately; 28 dashboard; recordings byte-identical on rerun |

P0 and P1 golden numbers are unchanged from Phase 4. P1t gives 14.4 false incidents per month (11.3–18.1) against the
report's 18.6 (15.0–22.8); over 20 seeds the engine (17.1) and the report
simulation (18.3) do not differ detectably (Welch p 0.58), so the 5-seed miss is sampling, as for P0 in Phase 4. One finding is logged, not tuned: after a long haze episode the M28
common-mode exclusion (slow z ≥ 3 on 25% of nodes) can miss a second network-wide rise, which pushes seed 22's tuned h
to its cap (P5-10, with a proposal).

**To see it:** `cd dashboard && npm run dev`, choose `node_3day.prs.jsonl.gz`, click node 31 (south-west of the
fire, which starts on day 3 at 13:00): the Node tab shows the stacked evidence. The Results tab shows the node-layer
table.

**Next step:** review Phase 5. Then Phase 6 — the PRAHARI edge layer (M30 clustering, M31 SCMR, M32 Fisher, M33
legacy prior, M34 legacy quorum then the Bayes form, M35 escalation), the evidence trace and live mode.

### 2026-09-23 — Session 8 (Phase 5 follow-ups and documentation)

- The developer confirmed the Phase 5 plan and left the follow-ups to the agent's judgement:
  - **Seed-22 common-mode weakness:** deferred, not changed — logged in `KNOWN_ISSUES.md` (improvement backlog) with
    a proposal to revisit after Phase 7; the default keeps reproducing the report's method.
  - **E-7:** applied; SPEC 1.0.3 says one-sided z ≥ 3 for M28's common-mode rule.
  - **Single-node fire in `node_3day`:** fixed in the demo, not the model — `record.from_day` (warm start) and the new
    scenario `node_mature` (31 days, days 29–31 recorded). With mature calibration and tuned h (226.6) the day-31
    fire gives candidates at nodes 41 (+67 min) and 31 (+108 min) and is confirmed at +134 min (SIM). Cold
    recordings are byte-identical to before (DECISIONS P5-14).
- **Documentation set** in `docs/` (DECISIONS Doc-1): `README.md` index; `guide/` (overview, background, glossary,
  setup, troubleshooting, demo walkthrough); `architecture/` (system, engine, models, data contracts, dashboard,
  testing); `journey/` (timeline, one page per phase 0–5, challenges and lessons, decisions and trade-offs);
  `results/validation.md`. CLAUDE.md rule 16 and SPEC §7 make documentation part of every phase.
- Tests: 134 engine passed (5 golden skipped; golden run separately), 29 dashboard.

**To see it:** open `docs/README.md` on GitHub (Mermaid diagrams render there). Dashboard: `npm run dev`, choose
`node_mature.prs.jsonl.gz`, go to day 31 13:00–15:30, click node 41; the footer reads "31 simulated days, recorded
from day 29".

**Next step:** Phase 6 — the PRAHARI edge layer (M30–M35), the evidence trace and live mode; plan first, then "go".

### 2026-09-23 — Session 9 (Phase 6)

- Phase 5 and the documentation set accepted by the developer ("good").
- Built Phase 6 — the PRAHARI edge layer, evidence trace and live mode:
  - Real edge stages beside the stubs: clustering M30 (legacy per-candidate form by default, as the report's
    simulation; components form optional), SCMR M31, Fisher M32, legacy day-type prior M33 (new `srp` stream,
    per-day overrides), RAQ M34 (legacy quorum 2 dry / 3 wet by default; Bayes form selectable), escalation M35.
  - Traces name the rule that decided, the incident and the triggering node; alerts carry the incident.
  - Harness pipeline P2; server `server/app.py` (FastAPI + WebSocket) streaming the recording's line format; module
    switches between frames.
  - Dashboard: "Why this alarm" (View 3) with the escalation ladder, SCMR gauge, Fisher, prior and Bayes bar;
    mechanism switches with live counters (View 5); Live engine panel and `LiveSource`.
  - `node_mature` day 31 set to a dry, busy day; new replay variant `node_mature__scmr-stub`.

**Phase 6 acceptance (details in `DECISIONS.md` P6-1…P6-12 and `docs/journey/phase-6-edge-layer.md`):**

| # | Test | Result |
| --- | --- | --- |
| 1 | P2 reproduces the report's numbers within intervals (legacy mode) | **miss** — 3.4 (2.0–5.4) false incidents/month vs 6.4 (4.4–9.0); 75.9% confirmed within 3 h vs 83% (79–87). Over 20 seeds false alarms match the report simulation (6.25 vs 7.20, p 0.48); detection is 8 points lower (74.0% vs 82.2%, p 0.03). Our code reproduces the report simulation exactly on its own data; the gap is in the simulated world (more haze in the engine seeds' calibration days; continuous weather wind vs a constant random wind per injected fire). Fix proposed, pending approval (KNOWN_ISSUES) |
| 2 | Legacy and Bayes RAQ agree on the worked example | **pass** — 2 nodes on dry days, 3 on wet days, in both forms |
| 3 | Every alert has a complete trace | **pass** — SCMR, Fisher, prior, Bayes, incident, anchor, explanation; methods named |
| 4 | The dashboard works in replay and live mode | **pass** — replay: why panel, SCMR switch keeps the clock (haze-day alarms 3 → 15); live: frames stream, a switch is applied mid-run; no console errors |
| — | Legacy edge vs the report's `confirm` on identical candidate streams | identical alarms |
| — | Reference values | Fisher 7.4e-6 and 8.6e-8; SBB bound 100 and 1e4 |
| — | Full suite, determinism | 146 engine passed (6 golden skipped unless enabled), 33 dashboard; recordings byte-identical on rerun |

**To see it:** `cd dashboard && npm run dev`, open `node_mature.prs.jsonl.gz`, go to day 31 at 15:15, tab *Alerts*
("Why this alarm"); then day 30 at 14:00 and press *SCMR*. Live: `uvicorn server.app:app --port 8000`, then
*Live engine* ▸ *Scenarios* ▸ *Start*.

**Next step:** review Phase 6 and decide on the proposed legacy per-fire wind option (KNOWN_ISSUES). Then Phase 7 —
experiments and results (ablations, operating dial, node spacing, maturity curve).

### 2026-09-23 — Session 10 (Phase 7)

- Phase 6 accepted by the developer, with approval for the legacy per-fire wind option.
- Built Phase 7 — experiments and results:
  - Per-fire wind (`plume.wind: per_fire`) for experiment presets; demos keep the weather wind (DECISIONS P7-1).
  - Offline edge and dial replay from recorded node evidence (`eval/offline.py`), tested equal to the live path;
    pipelines grouped by node-layer overrides; `--jobs N`; spacing sweeps (P7-2 … P7-4, P7-7).
  - Presets `golden` (P0, P1, P1t, P2, P2-SCMR, P2-RAQ, node metrics, dial), `ablation` (P2-QCC, P2-TTC), `spacing`
    (70/100/150 m), `seeds20` (seeds 11–30); `results/summary.json` combines them in the report's table format
    (`eval/report.py`, P7-5).
  - Results view: ablation chart, operating-dial chart, spacing chart; label layout fixed; every footer names seeds
    and simulated days (P7-8).
  - Golden tests extended to ablations, detection and spacing (P7-6); evidence file
    `engine/tests/golden/equivalence_p7_seeds11_30.json`.

**Phase 7 acceptance (details in `DECISIONS.md` P7-9 and `docs/journey/phase-7-experiments.md`):**

| # | Test | Result (SIM) |
| --- | --- | --- |
| 1 | Golden-number tests pass (§9.3) | **not met** — 6 of 21 golden tests pass (P1 false incidents; P1 and P1t detection; P2-QCC detection; both node-layer targets); 15 miss: false incidents for P0, P1t, P2 and the four ablations, P0 and P2 detection, three ablation-detection checks and all three spacing checks. Documented, not tuned (DECISIONS P7-9, P7-10; KNOWN_ISSUES) |
| 2 | Charts render from files | **pass** — every chart reads `results/summary.json` |
| 3 | Each chart shows seeds and days | **pass** — every footer; browser check with no console errors |
| — | Suite | 151 engine tests pass (21 golden skipped unless enabled), 35 dashboard tests |

Key numbers (golden seeds): P2 3.4 false incidents/month against P0 340.6; every ablation raises false alarms (P2-QCC
30.8, P2-TTC 8.2, P2-SCMR 5.0, P2-RAQ 5.4); dial 46–67 minutes median time to confirm; spacing 63 / 33 / 5%
confirmed at 70 / 100 / 150 m. Over seeds 11–30 and 31–50 false alarms agree with the report simulation for every
pipeline; the PRAHARI pipelines detect less (about 9 points on seeds 11–30, 5 points and not significant on fresh
seeds 31–50, 7 points over all 40, p 0.007), linked to haze in the calibration windows; open in KNOWN_ISSUES.

**To see it:** `cd dashboard && npm run dev`, tab *Results* (main, ablation, dial and spacing charts).
Files: `results/summary.json`, `docs/journey/phase-7-experiments.md`, `docs/results/validation.md`.

**Next step:** review Phase 7; decide on the proposed legacy node-ablation forms and on the calibration-haze item
(KNOWN_ISSUES). Then Phase 8 (communications and energy, optional) or Phase 9/10 as the developer prefers.

### 2026-09-23 — Session 11 (Phase 7 follow-up: legacy ablations and the reverse swap)

- The developer approved building the report simulation's node ablations and running the reverse swap.
- **Legacy ablations** (DECISIONS P7-12, P7-13): `ttc.detect_on: slow`, `qcc.form: robust_z`, `cusum.statistic: z`
  (+ `k_z`), optional contract fields `PValues.z` and `Scores.z`, selected by `experiment.ablation_form: legacy` (the
  `ablation` preset). Defaults unchanged: every recorded frame identical; recordings regenerated only for the model
  card's source text. On the report simulation's own seed-11 signals: P2-QCC exact; P2-TTC exact once its day-1
  look-ahead is accounted for. Golden seeds: P2-QCC 8.8, P2-TTC 8.4 false incidents/month (report 17.4, 11.8);
  seeds 11–30 match the report simulation's false alarms (p 0.48, 0.44).
- **Reverse swap and model checks** (DECISIONS P7-14): 2 × 2 over seeds 11–30 — engine backgrounds cost 4.6–7.4
  points of detection, engine fire sets 2.0–4.8; no model difference behind either (haze process, fire geometry and
  timing, calibration tails on 60 fresh seeds all agree; the report seeds drew fewer wet-day fires). The P2
  detection gap is recorded as sampling (KNOWN_ISSUES updated; the ablation item resolved).
- Tests: 157 engine tests pass (21 golden skipped unless enabled), 36 dashboard tests; golden suite 5 of 21 pass (P1
  false incidents, P1 and P1t detection, both node targets) — P2-QCC detection now misses (legacy 67.3% vs the report's
  78%; the stub form had passed); every other result as in session 10. Browser check: 5 Results charts, no console errors.

**To see it:** `cd dashboard && npm run dev`, tab *Results* — the ablation chart now shows the legacy forms (footer
says so). Evidence: `engine/tests/golden/equivalence_p7_seeds11_30.json`; write-up:
`docs/journey/phase-7-experiments.md` (follow-up section) and `docs/results/validation.md` §1–2.

**Next step:** review Phase 7. Then Phase 8 (communications and energy, optional), 9 (regimes and learning) or 10
(demo packaging), as the developer prefers.

### 2026-09-23 — Session 12 (Phase 8)

- Phase 7 and its follow-up accepted by the developer ("good").
- Built Phase 8 — communications and energy (DECISIONS P8-1 … P8-12):
  - M38 shadowing and TS011 relays in the links setup module (`shadowing_sd_db`, default 0).
  - Real comms (`comms/lora.py`, `comms/lorawan_real.py`): M39 time on air, M40 ALOHA collisions with capture,
    retries, relay hops, hourly heartbeats, gateway outages with re-routing and store-and-forward.
  - Real energy (`energy/power.py`, `energy/budget_real.py`): M41 budget by power mode and airtime, M42 half-sine
    harvest with cloudy days, M43 supercapacitor with ULP and stop modes.
  - `prahari energy` → `results/energy.json` (MQ-2 against BME688); scenarios `gateway_outage` and `cloudy_days`.
  - Dashboard: packet animation and queue badges, state-of-charge ring gauges, gateway out-of-service mark, power
    mode and SoC chart in the node views, energy chart in Results.
  - Comms and energy stay stubs by default: every earlier recording keeps identical frames.

**Phase 8 acceptance (details in `DECISIONS.md` P8-10 and `docs/journey/phase-8-comms-energy.md`):**

| # | Test | Result (SIM) |
| --- | --- | --- |
| 1 | M39: 61.7 ms at SF7, 1,482.8 ms at SF12 (24 B) | **pass** — 61.7 ms and 1,482.75 ms |
| 2 | ALOHA success within 3 points of e^(−2G) | **pass** — 82.4 / 61.5 / 37.8% vs 81.9 / 60.7 / 36.8% at G = 0.1 / 0.25 / 0.5 |
| 3 | A 0.5 Wh-per-day node with no sun lasts 9 ± 0.5 days | **pass** — stops at 5% after 8.66 days, empty after 9.11 |
| — | Suite | 176 engine tests pass (21 golden skipped unless enabled), 40 dashboard tests; new recordings byte-identical on rerun; browser check without console errors |

**To see it:** `cd dashboard && npm run dev`; open `gateway_outage.prs.jsonl.gz`, day 31 from 14:00 to 14:50 (gateway
crossed out, queue badge on node 41, burst at 14:30, confirmation at 14:48); open `cloudy_days.prs.jsonl.gz`, day 5
at 02:00 (amber ULP rings), click a node for its state-of-charge chart; tab *Results* for the energy chart.

**Next step:** review Phase 8; decide on the arrival-time item (KNOWN_ISSUES). Then Phase 9 (regimes, satellite race,
learning loop, faults) or Phase 10 (demo packaging).

### 2026-09-24 — Session 13 (Phase 9)

- Phase 8 accepted by the developer ("good"); the arrival-time fix approved.
- Built Phase 9 — regimes, satellite race, learning loop and faults (DECISIONS P9-1 … P9-16):
  - Arrival-time fix: `Delivered.t_detect`; the cluster window uses each candidate's detection minute.
  - M37 satellite race (`satellite/race.py`) and the race timeline under the map (View 4).
  - M21 faults (`sensors/faults_real.py`) and M29 health weights (`detect/prahari/score_real.py`); a node below 0.1
    abstains and is drawn as a fault.
  - M3 lightning storms, the SCMR relaxation while a storm is flagged (held 180 min), and the M33 integral prior
    (option).
  - Regime Cards (`configs/regimes/`: india, canada, usa, australia), the header's `regime` block and the regime
    selector (View 8).
  - M36 learning loop (`learn_real.py`, `eval/learning.py`, `prahari experiment --preset learning`): learning curve
    and calibration-maturity curve, charted in Results.
  - Scenarios: `satellite_race`, `sensor_fault`, `lightning_storm` (+ `__no-relax`), `power_line_corridor`,
    `bushfire_afternoon`. All earlier recordings regenerated for the header; frames identical except
    `gateway_outage` (fix: confirmation 14:48 → 15:14) and two `cloudy_days` traces (no decision changes).

**Phase 9 acceptance (details in `docs/journey/phase-9-regimes-learning.md` and `docs/results/validation.md` §7):**

| # | Test | Result (SIM) |
| --- | --- | --- |
| 1 | Race timeline reports correct deltas on scripted fires | **pass** — `satellite_race`: candidate +55 min, confirmation +74 min, satellite alert +9 h 20 min (Terra 22:30); unit and Vitest checks |
| 2 | Learning curve monotone within noise, K = 5 → 100 | **pass** — 49% (bound) → 68, 68, 68, 71% confirmed within 3 h at ≤ 3 false incidents/month on held-out seeds 51–53 (183 fires) |
| 3 | Stuck sensor's health weight < 0.1 within 90 min | **pass** — 58 min (unit test), 59 min (node 55 in `sensor_fault`) |
| — | Suite | 204 engine tests pass (21 golden skipped unless enabled), 48 dashboard tests, `tsc` and build clean; browser check of the race timeline, fault glyph, regime selector and both Results charts with no console errors; docs link check clean |

Parked: nothing. New limits logged in `KNOWN_ISSUES.md`: a +1.5 su offset is not caught; a stuck sensor can raise one
candidate before it abstains. The first learning run exposed a training-set bug (quiet data varying with K), fixed
before acceptance (P9-13).

**To see it:** `cd dashboard && npm run dev`:
- Open `satellite_race.prs.jsonl.gz`, day 31, and scrub from 14:00: the race timeline under the map.
- Open `sensor_fault.prs.jsonl.gz`, day 31 from 09:00: node 55 abstains at 09:59; click it for the health weight.
- Pick a regime in the new *Regime* selector (Canada: `lightning_storm`).
- Open the *Results* tab for the learning and maturity charts.

**Next step:** review Phase 9. Then Phase 10 (demo hardening).

### 2026-09-24 — Session 14 (Phase 10)

- Phase 9 accepted by the developer (approval of the Phase 10 plan).
- Built Phase 10 — demo hardening (DECISIONS P10-1 … P10-6):
  - Storyboard recordings: new `wet_morning_haze` (day 30 wet, quiet; `node_mature`'s haze) with `__scmr-stub` and
    `__raq-stub` variants; the other §11 steps reuse `satellite_race` and `node_mature` (mapped in
    `dashboard/public/storyboard.json` and the journey page).
  - Presenter mode (§6.4): keys 1–9, Space, S, R, F, Esc; the caption strip under the header; captions and bookmarks in
    `storyboard.json`, editable without a rebuild; `?presenter=1` opens step 1.
  - Launchers: `scripts/demo.sh`, `scripts/demo.ps1`, `scripts/demo.cmd` — serve `dashboard/dist` with Python's
    standard-library server on port 8765 and open presenter mode; `npx vite preview` as a fallback.
  - `DEMO_CHECKLIST.md`.

**Phase 10 acceptance:**

| # | Test | Result |
| --- | --- | --- |
| 1 | Airplane mode: the static build plays all storyboard steps | **pass** — rehearsal through the launcher's server with all non-local requests blocked: 0 external requests; all nine steps load (≤ 0.4 s each); S and R open the right variants |
| 2 | A full rehearsal takes 3 minutes or less | **pass** — 170.1 s (170 s planned) |
| 3 | No console errors | **pass** |
| — | Suite | 204 engine tests pass (21 golden skipped unless enabled), 53 dashboard tests; build clean; `wet_morning_haze` byte-identical on rerun; docs link check clean |

**To see it:** run `scripts/demo.sh` (Windows: double-click `scripts\demo.cmd`). The browser opens on step 1; press F for
full screen, then 1–9. Read `DEMO_CHECKLIST.md` before the talk.

**Next step:** review Phase 10. All phases of SPEC §7 are then complete; what remains is the developer's rehearsal on
the demo laptop and any items from `KNOWN_ISSUES.md` the developer wants before the conference.

### 2026-09-24 — Session 15 (Phase 10 acceptance)

- Phase 10 accepted by the developer ("good, approved phase 10"). All phases 0–10 of SPEC §7 are now accepted.
- No code, recording or model changes this session. Test status as at `32f920d`: 204 engine tests pass (21 golden
  skipped unless enabled), 53 dashboard tests pass.

**To see it:** `scripts/demo.sh` (Windows: double-click `scripts\demo.cmd`), then F and 1–9; follow `DEMO_CHECKLIST.md`.

**Next step:** the developer's rehearsal on the demo laptop. Optional items remain in `KNOWN_ISSUES.md` (the M28
common-mode backlog, the P2 legacy detection gap, the M29 small-offset limit, the pre-abstain candidate) for the
developer to schedule or leave.

### 2026-09-24 — Session 16 (release 1.0: final audit and hardening)

- Developer request: audit, fix, document and harden the code so this version can be locked; no revamps, features or
  removals. Details: `docs/journey/release-1.0-audit.md`, `DECISIONS.md` R1-1 … R1-11.
- Baseline recorded first (hashes of every recording and result, golden outcome 5 of 21, package versions).
- **Fixed (dashboard):**
  - the map collapsing at 1280 × 720;
  - the race timeline claiming a race against the satellite stub.
- **Hardened:**
  - error boundaries around every view;
  - atomic writes of recordings and results;
  - configuration value checks;
  - one-line CLI errors with exit codes 2, 1 and 130;
  - presets found from any folder;
  - incomplete recordings open with a note;
  - live-server request validation.
- **Documented:** about 100 docstrings; README for the finished project; architecture, guide and troubleshooting
  pages.
- **Locked:**
  - `engine/requirements-lock.txt`;
  - upper version bounds;
  - `engines: node >= 20`;
  - version 1.0.0;
  - `scripts/check_all.sh`.
- **Refreshed:** 16 recordings whose header model-card `source` text was stale from Phase 9. Frames and traces are
  identical; the pre-audit code gives the same bytes.

**Release gate:**
- **Engine:** 222 tests pass, with warnings as errors (21 golden skipped unless enabled).
- **Dashboard:** 56 tests pass; `tsc` and build clean.
- **Outputs:** all 20 recordings regenerate byte for byte; `energy.json`, `learning.json` and the K = 100 model reproduce
  exactly; the golden suite gives the same 5 pass and 16 miss.
- **Browser:** 60-page sweep with 0 console errors; the forced-failure check behaves as designed; presenter rehearsal
  170.1 s, 0 external requests, 0 errors.
- **Fuzz:** 34 configurations with no exception and no non-finite value.

**To see it:** `scripts/check_all.sh` (all checks), `scripts/demo.sh` (the demo), and the Phase 9 or 10 recordings at
1280 × 720 (the map stays visible).

**Next step:** none required. Tag `v1.0.0` marks the locked release; any later change should keep `scripts/check_all.sh`
passing and log output changes in `DECISIONS.md`.

