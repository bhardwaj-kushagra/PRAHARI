# PROGRESS

| Phase | Title | Status |
| --- | --- | --- |
| 0 | Foundation and replay shell | accepted (2026-09-23) |
| 1 | World, network and siting | awaiting review |
| 2 | Weather, fuel moisture and sensor signals | not started |
| 3a | Fires and plumes, legacy | not started |
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
