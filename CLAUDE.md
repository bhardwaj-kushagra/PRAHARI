# CLAUDE.md — PRAHARI-SIM agent rules

This repository builds a **local simulator and dashboard** for the FIRENET–PRAHARI wildfire-detection system, for a conference demonstration. The full specification is `docs/SPEC.md`. These rules are **non-negotiable**. If a request conflicts with them, stop and say so.

## Before writing any code in a session

1. Read `PROGRESS.md` (which phase we are in), `KNOWN_ISSUES.md` (what is parked) and `DECISIONS.md`.
2. Read `docs/SPEC.md` §2 (principles) and §4 (framework) if you have not this session, then **only** the current phase's section in §7 and the §5 equations it lists.
3. State in a few bullets what you will build, which files you will touch, and which acceptance tests will prove it. Wait for "go" unless told to proceed.

## The rules

1. **Stubs are sacred.** Every stage has a `stub` implementation registered under the same name as its `real` one. Never delete, weaken or bypass a stub. New real implementations replace stubs *through the registry*, not by editing callers.
2. **Module states come from config.** Each module is `real`, `stub` or `off` in `configs/*.yaml`. Never hard-code which implementation runs.
3. **Contracts are additive.** Data classes in `engine/prahari/core/contracts.py` may gain fields with defaults. Never rename or remove a field from an accepted phase without bumping the contract version, updating every consumer and its tests in the same change, and logging it in `DECISIONS.md`.
4. **No rewrites of accepted phases.** Do not restructure, rename, reformat or "clean up" files from phases marked accepted in `PROGRESS.md`. If a change there is truly needed, propose it and wait for approval.
5. **Failures degrade; they never crash.** Every stage call goes through the runner's isolation wrapper. A real module that raises or returns invalid output (NaN, wrong shape, out of range) switches to its stub for the rest of the run and is marked `degraded`.
6. **Escape hatch — never get stuck.** If a module fails its acceptance tests after about three focused attempts, or its timebox in `docs/SPEC.md` §7 runs out:
   - set it to `stub` in `configs/default.yaml`,
   - write the symptoms, what you tried and your best diagnosis in `KNOWN_ISSUES.md`,
   - confirm the full test suite and the dashboard still run,
   - move on to the next item.

   Parking a module is always better than blocking the project.
7. **Determinism.** All randomness comes from the master seed via `numpy.random.SeedSequence`, one spawned generator per module (`core/rng.py`). New modules append their stream name at the **end** of the list. Never use Python's `random` or an unseeded NumPy call.
8. **Vectorise over nodes.** Per-node state lives in NumPy arrays. No Python loops over nodes inside the tick loop.
9. **Cite the maths.** Every formula in code carries a comment with its equation number, for example `# M26 — QCC p-value`. Every parameter lives in configuration with a `source` tag (`LIT`, `VEN`, `DER`, `ASM`, `TGT`).
10. **No fabricated results.** Charts and numbers come from simulator output files. Never hard-code result values outside `tests/golden/`. Never tune a model to improve a chart without recording why in `DECISIONS.md`.
11. **Replay first.** The dashboard must always work from recordings with no server running. Live mode is optional and must never be required.
12. **Tests with every change.** Write or update the unit tests for the equations you implement, using the reference values in `docs/SPEC.md` §9.2. Run the whole suite before finishing. Golden tests (§9.3) run in legacy mode only.
13. **Minimal dependencies.**
    - Engine: NumPy, SciPy, PyYAML, Pydantic (optional), pytest.
    - Server: FastAPI, Uvicorn.
    - Dashboard: React, TypeScript, Vite, ECharts, zustand.

    Anything else needs a line in `DECISIONS.md` first.
14. **Small files.** Keep modules under about 300 lines, with maths in pure functions (arrays in, arrays out) and no hidden global state.
15. **Label simulation.** Every dashboard view shows the SIMULATION badge. Every chart footer states seeds and simulated days.

## At the end of every session

- Update `PROGRESS.md`: what was done, test status, the next step.
- Add any deviation, new dependency or tuning choice to `DECISIONS.md`.
- Add any parked module to `KNOWN_ISSUES.md`.
- Tell the developer exactly what to open to see the change (a command and a dashboard view).

## Useful commands (keep this list up to date)

```text
pip install -e engine[dev]                    # engine
pytest engine/tests                           # all engine tests
prahari run --config configs/scenarios/smoke.yaml --out recordings/smoke.prs.jsonl.gz
prahari experiment --preset golden            # legacy-mode reproduction (Phase 4+)
uvicorn server.app:app --reload               # live server (Phase 6+)
cd dashboard && npm install && npm run dev    # dashboard (copies recordings/ in first)
cd dashboard && npm test                      # dashboard unit tests (Vitest)
cd dashboard && npm run build && npm run preview   # static build, no engine server
```
