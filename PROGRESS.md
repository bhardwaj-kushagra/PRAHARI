# PROGRESS

| Phase | Title | Status |
| --- | --- | --- |
| 0 | Foundation and replay shell | accepted (2026-09-23) |
| 1 | World, network and siting | accepted (2026-09-23) |
| 2 | Weather, fuel moisture and sensor signals | accepted (2026-09-23) |
| 3a | Fires and plumes, legacy | accepted (2026-09-23) |
| 3b | Gaussian plume (optional) | accepted (2026-09-23) |
| 4 | Baselines and evaluation harness | accepted (2026-09-23) |
| 5 | PRAHARI node layer | awaiting review |
| 6 | PRAHARI edge layer, trace and live mode | not started |
| 7 | Experiments and results | not started |
| 8 | Communications and energy (optional) | not started |
| 9 | Regimes, satellite race, learning loop and faults (optional) | not started |
| 10 | Demo hardening | not started |

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
