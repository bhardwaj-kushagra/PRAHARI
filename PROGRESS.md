# PROGRESS

| Phase | Title | Status |
| --- | --- | --- |
| 0 | Foundation and replay shell | awaiting review |
| 1 | World, network and siting | not started |
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

