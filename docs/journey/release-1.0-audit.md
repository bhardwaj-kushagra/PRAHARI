# Release 1.0 — Final audit and hardening

## Goal

Lock a version that keeps working: find and fix what could break during a demo or in later use, make failures clear
and safe, document the code, and prove that the science did not move. The explicit limits were:

- no revamps, new features or removals;
- no change to any model, parameter or default;
- nothing that puts the accepted work at risk.

## How the audit was run

1. **Baseline first.** Before any change I recorded:
   - the SHA-256 of every recording and results file;
   - the golden-suite outcome (5 of 21 pass: the pattern documented since Phase 7);
   - the test counts and the exact package versions.
2. **Audit, then fix.** Each finding was put in one of four classes:
   - **(a) defect:** fix;
   - **(b) robustness:** harden with no output change;
   - **(c) documentation:** fix;
   - **(d) known limitation:** log.

   The checks:
   - **Static:** pyflakes, a scan for unguarded reductions and divisions, missing docstrings.
   - **Configuration fuzz (34 runs):**
     - every scenario, shortened;
     - all modules real, all stub, all off where allowed;
     - 1, 2, 7 and 100 nodes, spacings of 30 and 150 m, three layouts;
     - three seeds with 12 scripted fires.

     Each run checked for exceptions, degraded modules and non-finite values.
   - **CLI error paths:** missing or invalid files, impossible values, bad arguments, an unwritable output, Ctrl-C.
   - **Live-server requests:** path traversal, bad bodies, bad switches.
   - **Browser sweep:** every recording at 1600 × 1000, 1366 × 768 and 1280 × 720 — scrubbing, every tab, clicking a
     node, play and pause.
   - **Rehearsal:** the timed presenter rehearsal with the network blocked.
3. **Verify.** The same checks were repeated after the changes, and the outputs compared with the baseline.

## Findings and what was done

| # | Class | Finding | Outcome |
| --- | --- | --- | --- |
| A1 | defect | At 1280 × 720, recordings with the extra Phase 8 layer rows squeezed the map to zero height: no map on a small projector | The map keeps at least 360 px; the left column scrolls. The sweep now passes at all three sizes |
| A2 | defect | The race timeline claimed a race in recordings that use the satellite stub, a fixed 90-minute delay after ignition that is not M37 (for example "The satellite alert came 44 min before PRAHARI confirmed" in `gateway_outage`) | A stub alert is labelled as such and no race is claimed; the M37 recordings are unchanged |
| A3 | robustness | No error boundary: an error in any view would blank the whole page | Each region and tab is wrapped; a failing view shows its error and a retry, the rest keeps working. Checked with a deliberately broken recording |
| A4 | robustness | Several CLI paths ended in a traceback: unwritable output, a folder as output, `energy` with a bad configuration, `--seeds 1,x`, Ctrl-C | One-line errors with exit codes 2 (configuration), 1 (file) and 130 (interrupted); arguments validated |
| A5 | robustness | Impossible values gave late or misleading errors (`--days 0` reported "record.from_day 0 is not inside the run"); a grid with a non-square node count silently degraded the siting module | Checked when the configuration loads, with the key named; every shipped configuration still loads |
| A6 | robustness | Presets were found only from the repository root, with a confusing message elsewhere | Presets and the energy configuration are found from any folder; an unknown preset lists the real ones |
| A7 | robustness | Recordings and results were written in place: an interruption during the write could leave a truncated file | Atomic writes (temporary file, then rename); bytes identical |
| A8 | robustness | A recording whose last line was cut off (for example an interrupted copy) was refused entirely | The cut-off line is skipped and the footer says "incomplete recording"; any other bad line is still refused |
| A9 | documentation | `contracts_edge.py` used `np` in a type annotation without importing it | Imported; type hints resolve |
| A10 | robustness | The live server accepted a negative speed | Speed ≥ 0 and days > 0 are validated (422) |
| A11 | documentation | About 100 framework, contract, evaluation and server definitions had no docstring | Docstrings added and checked against the code (five contract docstrings were corrected against their fields); the stage-attribute convention is documented |
| A12 | limitation | `core/pipeline.py` is 314 lines after docstrings, over rule 14's guide of about 300 | Left as is: it is accepted code (rule 4). Noted in `DECISIONS.md` R1-9 |
| A13 | documentation | 16 committed recordings had a slightly stale header: the model-card `source` text of `learn` (and, in the two lightning recordings, `srp`) predated a Phase 9 configuration edit | Regenerated. Each differs from its predecessor only in that header text; every frame and trace is identical. The same bytes come from the pre-audit code |

## Challenges and issues

1. **Most recordings did not match the committed bytes on the first full check.** This looked like a regression. The
   diff showed one line — the header's model card — and a regeneration from the pre-audit commit gave the same bytes
   as the audited code. The committed files were stale from Phase 9, not changed by the audit. They were regenerated,
   and the difference was verified field by field (A13).
2. **A scripted rewrite of file writes mangled one line.** A regular-expression replacement turned
   `(out / "energy.json").write_text(...)` into invalid code. The script also stopped before it touched the other files.
   This was caught at once by the file check, and every write was then replaced by exact, reviewed edits.
3. **Ctrl-C could not be tested from the agent's shell,** because background jobs ignore SIGINT. It was tested through a
   Python wrapper that sends the signal to the child process.
4. **A generated docstring was wrong.** `Simulation.tick` was first described as returning a "must record" flag. Every
   inserted docstring was then compared with the code, which corrected that one and five contract docstrings.

## Decisions and trade-offs

| Decision | Pros | Cons | Ids |
| --- | --- | --- | --- |
| Treat outputs as the asset: prove byte identity before and after | no silent change to any result | a full check takes 15–30 minutes | R1-1 |
| Label the stub satellite instead of switching earlier scenarios to M37 | recordings and results unchanged; honest | the race in older recordings shows "not modelled" | R1-2 |
| Configuration errors for impossible values rather than runtime degradation | the problem is named before a run starts | a grid with 50 nodes is now refused (it used to run with a degraded siting module) | R1-6 |
| Upper version bounds below the next major release, and an exact lock file | future major releases cannot silently change results | installing with much newer packages needs a deliberate bump | R1-7 |
| Document the stage-attribute convention instead of a docstring on every stage class | no redundant text; the model card is the documentation | readers must know the convention | R1-9 |

## Verification (release gate)

| Check | Result |
| --- | --- |
| Engine tests (warnings as errors) | 222 passed, 21 golden skipped (204 before the audit plus 18 new). One warning remains: Starlette's notice that its test client will move from httpx to a successor package. It affects only the live-server tests and is harmless with the locked versions |
| Dashboard | `tsc` clean, 56 Vitest tests (53 plus 3 new), build clean |
| Recordings | all 20 regenerate byte for byte (after the A13 refresh) |
| Results | `prahari energy`, and the learning preset (`learning.json`, `learning_model_k100.json`), reproduce the committed files exactly |
| Golden suite | the same 5 of 21 pass and the same 16 miss as before the audit |
| Browser sweep | 60 page loads (20 recordings × 3 sizes), 0 console errors, 0 blank pages |
| Forced failure | a recording without `map` shows the map's notice while the tabs, clock and keys keep working; a cut-off recording opens with its "incomplete" note |
| Presenter rehearsal | 170.1 s against 170 s planned, 0 external requests, 0 console errors |
| Fuzz | 34 configurations: no exception, no non-finite value. The two non-square grids (1 and 100 nodes are square; 2 and 7 are not), injected past the loader that now refuses them, degrade the siting module to its stub as designed and still complete |
| Docs | links resolve |

## How to re-verify later

```text
scripts/check_all.sh           # tests, type check, build, doc links, every recording regenerated byte for byte
PRAHARI_GOLDEN=1 PRAHARI_JOBS=4 pytest engine/tests/golden   # the golden pattern (5 of 21, documented)
```

Install with `pip install -r engine/requirements-lock.txt -e "engine[dev,server]"` and `npm ci` to use the exact
versions this release was verified with.
