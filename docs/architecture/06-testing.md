# Architecture 6 — testing

Tests are how each phase proves it is done. Every phase has acceptance tests from SPEC §7, and every equation has unit
tests using the reference values in SPEC §9.2.

## Layers

| Layer | Where | What it proves | When it runs |
| --- | --- | --- | --- |
| Contracts | `engine/tests/unit/test_contracts.py` | every stage's real and stub outputs satisfy their data contracts | always |
| Isolation | `engine/tests/unit/test_runner.py` | a failing module degrades to its stub and the run completes | always |
| Equations | `engine/tests/unit/test_*_phaseN.py` | each model against SPEC reference values and closed-form results | always |
| Oracle cross-checks | `test_eval_phase4.py`, `test_node_phase5.py`, `test_edge_phase6.py` | P0, P1, P1t, M24–M28, the legacy edge (`confirm`) and the M46 counting agree **exactly** with `reference/prahari_simulation.py` on identical inputs | always |
| Live server | `test_server_phase6.py` | scenarios, a live run streams recording lines in order, module switches, health | when fastapi and httpx are installed |
| Configuration | `test_config.py` | merge rules, unknown keys, missing source tags | always |
| Traces | `test_trace.py` | evidence records and explanation sentences | always |
| Smoke and determinism | `engine/tests/smoke/` | the smoke scenario runs fast, the same seed gives identical bytes, the experiment harness works | always |
| Golden | `engine/tests/golden/` | legacy-mode results against the report's intervals, node-layer acceptance | only with `PRAHARI_GOLDEN=1` (about 8 minutes) |
| Dashboard | `dashboard/src/**/*.test.ts` (Vitest) | recording parser, helpers for layers, series, results and formatting | always |
| Browser check | a Playwright script run during development | the static build loads each view, charts render, no console errors | at the end of each phase |

## Running them

```bash
pytest engine/tests -q                      # engine: about 1 minute
PRAHARI_GOLDEN=1 pytest engine/tests/golden # golden: slow
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
