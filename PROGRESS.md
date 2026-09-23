# PROGRESS

| Phase | Title | Status |
| --- | --- | --- |
| 0 | Foundation and replay shell | accepted (2026-09-23) |
| 1 | World, network and siting | accepted (2026-09-23) |
| 2 | Weather, fuel moisture and sensor signals | accepted (2026-09-23) |
| 3a | Fires and plumes, legacy | awaiting review |
| 3b | Gaussian plume (optional) | not started |
| 4 | Baselines and evaluation harness | not started |
| 5 | PRAHARI node layer | not started |
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
