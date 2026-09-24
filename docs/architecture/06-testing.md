# Architecture 6 — testing

Tests are how each phase proves it is done. Every phase has acceptance tests from SPEC §7, and every equation has unit
tests using the reference values in SPEC §9.2.

## Layers

| Layer | Where | What it proves | When it runs |
| --- | --- | --- | --- |
| Contracts | `engine/tests/unit/test_contracts.py` | every stage's real and stub outputs satisfy their data contracts | always |
| Isolation | `engine/tests/unit/test_runner.py` | a failing module degrades to its stub and the run completes | always |
| Equations | `engine/tests/unit/test_*_phaseN.py` | each model against SPEC reference values and closed-form results | always |
| Oracle cross-checks | `test_eval_phase4.py`, `test_node_phase5.py`, `test_edge_phase6.py`, `test_ablation_legacy.py` | P0, P1, P1t, M24–M28, the legacy ablation forms, the legacy edge (`confirm`) and the M46 counting agree **exactly** with `reference/prahari_simulation.py` on identical inputs | always |
| Offline replay | `test_experiments_phase7.py` | the offline edge equals the live edge, offline tuned h and replayed candidates equal the live CUSUM, per-fire wind, pipeline grouping, dial at the design target equals P2, table order | always |
| Radio and energy | `test_comms_energy_phase8.py` | M39 reference times (acceptance 1), pure-ALOHA success within 3 points of e^(−2G) (acceptance 2), capture, shadowing and relays, delivery, heartbeats, store-and-forward, M41 budgets, M42 half-sine, M43 store, a 0.5 Wh-per-day node lasting 9 ± 0.5 days (acceptance 3), modes, cloudy days, determinism of a Phase 8 scenario | always |
| Phase 9 | `test_phase9_edge_time.py`, `test_phase9_satellite.py`, `test_phase9_faults.py`, `test_phase9_regimes.py`, `test_phase9_learning.py` | clustering by detection minute; M37 overpass times, threshold, miss and delay, and the race deltas; M21 faults and M29 health weights (acceptance 3: a stuck sensor's weight below 0.1 within 90 minutes); lightning strikes, the storm hold and the SCMR relaxation, the M33 integral prior, regime composition; the M36 IRLS fit, the likelihood ratio, the switch at K ≥ k_min, training sets and the fixed-budget operating point, the M26 floor (SPEC §9.2) | always |
| Release hardening | `test_release_hardening.py`; dashboard `errorBoundary.test.ts`, the parser and race tests | atomic writes keep the previous file on failure and leave recording bytes unchanged; impossible configuration values are clear errors; every shipped configuration loads; CLI errors are one line with the documented exit codes; contract type hints resolve; the live server rejects negative speed and days; the error boundary resets on a new recording or tab; a cut-off last line or a truncated `.gz` opens as an incomplete recording; only the latest load may set the source (`loadToken.test.ts`); a stub satellite claims no race | always |
| Live server | `test_server_phase6.py` | scenarios, a live run streams recording lines in order, module switches, health | when fastapi and httpx are installed |
| Configuration | `test_config.py` | merge rules, unknown keys, missing source tags | always |
| Traces | `test_trace.py` | evidence records and explanation sentences | always |
| Smoke and determinism | `engine/tests/smoke/` | the smoke scenario runs fast, the same seed gives identical bytes, the experiment harness works | always |
| Golden | `engine/tests/golden/` | legacy-mode results against the report's intervals (false incidents for all eight pipelines, detection for P0–P2), ablation and spacing rates (report value inside our interval), node-layer acceptance | only with `PRAHARI_GOLDEN=1` (about 25 minutes on one core; `PRAHARI_JOBS=4` parallelises seeds) |
| Dashboard | `dashboard/src/**/*.test.ts` (Vitest) | recording parser, helpers for layers, series, results and formatting; race timeline, regime filter and learning-curve checks (Phase 9) | always |
| Browser check | a Playwright script run during development | the static build loads each view, charts render, no console errors | at the end of each phase |
| Storyboard | `dashboard/src/presenter.test.ts`; a timed Playwright rehearsal during development | the storyboard is valid, names existing recordings and fits in 180 s; the rehearsal presses 1–9 against the launcher's server with all non-local requests blocked, holds each step for its planned time, and checks load times, the S/R variants and console errors (Phase 10 acceptance) | `npm test`; the rehearsal before a demo |

## Running them

`scripts/check_all.sh` runs the whole release check in one command: the engine tests with warnings as errors, the
dashboard type check, unit tests and build, the documentation link check, and every scenario regenerated and
compared byte for byte with `recordings/` (`--quick` skips the last). The release 1.0 audit also ran two
development-time sweeps, kept out of the repository because they use Playwright:

- a configuration fuzz: every scenario, all-real, all-stub, all-off, odd node counts, layouts and seeds with many fires;
- a browser sweep: every recording at three screen sizes, every tab.

Both are described in [../journey/release-1.0-audit.md](../journey/release-1.0-audit.md).

```bash
pytest engine/tests -q                      # engine: about 1 minute
PRAHARI_GOLDEN=1 PRAHARI_JOBS=4 pytest engine/tests/golden # golden: slow
cd dashboard && npm test                    # dashboard
```

## Why oracle cross-checks

The report's simulation draws all its random numbers from one stream; the engine uses one stream per module (so that
adding a module never changes the others). The two can therefore never produce the same random draws. The
cross-checks separate the two questions:

1. **Is the code the same?** Feed identical arrays to our function and to the oracle's function and require identical
   output. This has held for every baseline and node-layer function.
2. **Is the behaviour the same?** Run both over the same 20 seeds and compare the distributions (Welch and
   Mann–Whitney tests). See [../results/validation.md](../results/validation.md).

## Test fixtures

- `engine/tests/unit/data/cffdrs_fwi_01.csv` — the cffdrs package's published FFMC test outputs (M7 verification).
- `engine/tests/golden/report_reference.json` — the report's numbers; the only hard-coded result values in the project
  (CLAUDE.md rule 10).
- `engine/tests/golden/equivalence_*.json` — per-seed evidence of the engine-versus-oracle comparisons.
- Synthetic data in tests is drawn from explicitly seeded generators and marked "test fixture only".

## Counts at the end of Phase 6

146 engine tests pass (6 golden tests skipped unless enabled) and 33 dashboard tests pass (SIM development machine).
