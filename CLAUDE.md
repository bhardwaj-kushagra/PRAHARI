# CLAUDE.md — PRAHARI paper branch (research charter)

This branch (`paper/common-mode-floor`) turns PRAHARI-SIM into the evidence base for one research paper. Working
title: *The Common-Mode Floor: Regional Smoke, Not Sensor Noise, Limits False Alarms in Low-Cost Gas-Sensor Wildfire
Networks*.

The direction is `docs/research/direction.md`, which summarises the developer's research-direction PDF of 25 Sep
2026. Where that document and older pages conflict, the direction wins.

`main` stays the locked release 1.0 simulator, under its own `CLAUDE.md`.

On this branch, models, assumptions, protocols and code may change whenever the science needs it. **Results may
never be manipulated, selected or invented.** The rules below draw that line. If a request conflicts with them,
stop and say so.

## Before work in a session

1. Read:
   - `docs/research/direction.md`, `PROGRESS.md` (latest session), `DECISIONS.md` (Research track and Paper branch
     sections) and `KNOWN_ISSUES.md`;
   - the protocol of the round in progress (`docs/research/protocol*.md`).
2. State what you will do, which files you will touch and how it will be checked. Wait for "go" unless told to
   proceed.

## Integrity rules (non-negotiable)

1. **Pre-registration.** Every confirmatory round (R1, R2, …) has a protocol committed **before** the first run on its
   seeds: seeds, data-generating scenarios, methods, knobs, endpoints, statistics.
   - Git history must show the protocol commit before the first result file.
2. **No outcome-driven changes.** Inside a round, no model, parameter, method, grid, budget or seed changes because of
   that round's results. A change goes into the *next* round, with new seeds.
   - Anything changed after a round's runs start is a **deviation**, logged in `DECISIONS.md` with its reason.
   - Deviations are allowed only for errors (such as a configuration the world cannot represent) or for additive
     descriptive analyses, never to improve a result.
3. **Report everything.** Every registered comparison is reported, whatever its outcome, and earlier rounds stay as
   registered. Analyses not in a protocol are labelled **exploratory**.
4. **No fabricated or hand-edited results.** Numbers and figures come only from result files written by code. Never
   type a result into a document without its source.
   - `docs/research/numbers.md` maps every number in the paper to its file and key.
5. **Determinism.** All randomness comes from `numpy.random.SeedSequence` streams (`core/rng.py`). New streams are
   appended at the end of the list. No unseeded randomness. Result files must regenerate byte for byte.
6. **Provenance.** Every parameter lives in configuration with a `source` tag: `LIT`, `VEN`, `DER`, `ASM`, `TGT`, or
   `DATA` (derived from a public dataset, with the script that derived it).
   - Every formula in code cites its equation (M1–M46 from `docs/SPEC.md`, R1–R8 from protocol R1, new ones from the
     round's protocol).
7. **Real data.**
   - Public datasets only, used within their licence.
   - Raw files sit under `data/real/<dataset>/`, unmodified, with a README giving the source, licence, retrieval date
     and checksum. Every derivation is a script.
   - Real data used to *set* simulation parameters are never also used to *validate* them.
   - No physical experiments are part of this paper.
8. **Labels.** Every number states whether it is **SIM** (simulator output) or **REAL** (public data), and every
   figure footer gives its seeds or dataset.
9. **Tests.** Every new method or model has unit tests with reference values. A method replayed offline has a
   fidelity test against its reference implementation. Run the whole engine suite before finishing a session.
10. **Authorship.** The authors write the paper's prose. The agent supplies analyses, numbers, figures, outlines and
    reviews. AI use is disclosed in the paper (IEEE policy).

## What is relaxed on this branch (the release-1.0 build rules)

- **Models and code.** Any model, module or accepted file may be changed or rewritten, with a `DECISIONS.md` entry
  (why, and what output changes) and updated tests.
  - Stubs are kept where they help, but they are not required for research modules.
  - Data contracts may change with their consumers and tests.
- **Configuration.** Module states and parameters still come from configuration. Research code may add its own
  configuration files (`configs/research/*.yaml`, plain YAML).
- **Dashboard and recordings.** Not maintained here, and not published from here. The byte-identity gate of
  `scripts/check_all.sh` becomes an optional regression report: run it to see which release outputs a change moves.
- **Dependencies.** Allowed with a one-line `DECISIONS.md` entry.
- **File size.** About 300 lines is a guideline, not a rule.
- **Documentation.** A research log replaces per-phase journey pages:
  - `PROGRESS.md` entries;
  - `docs/research/` pages per round;
  - `KNOWN_ISSUES.md` for open problems.

## At the end of every session

- `PROGRESS.md`: what was done, test status, the next step.
- `DECISIONS.md`: every deviation, new dependency, model change and data source.
- `docs/research/`: the round's results page and `numbers.md`, with relative links checked.
- Commit and push to `paper/common-mode-floor`. Tell the developer what to open.

## Useful commands (keep this list up to date; the release-1.0 commands still work)

```text
pip install -e "engine[dev,server]"          # engine (+ optional live server: fastapi, uvicorn, websockets)
pip install -r engine/requirements-lock.txt -e "engine[dev,server]"   # release 1.0: the exact tested versions (dashboard: npm ci)
scripts/check_all.sh [--quick]                # release check: tests, typecheck, build, doc links, recordings byte-identical
pytest engine/tests                           # all engine tests
prahari run --config configs/scenarios/smoke.yaml --out recordings/smoke.prs.jsonl.gz
prahari run --config configs/scenarios/siting_greedy.yaml --out recordings/siting_greedy.prs.jsonl.gz   # also siting_corridor
prahari run --config configs/scenarios/signals_3day.yaml --out recordings/signals_3day.prs.jsonl.gz     # Phase 2 signals
prahari run --config configs/scenarios/fires_day.yaml --out recordings/fires_day.prs.jsonl.gz           # Phase 3a fires
prahari run --config configs/scenarios/fires_day_gaussian.yaml --out recordings/fires_day_gaussian.prs.jsonl.gz   # 3b
prahari run --config configs/scenarios/node_3day.yaml --out recordings/node_3day.prs.jsonl.gz           # Phase 5 node layer
prahari run --config configs/scenarios/node_mature.yaml --out recordings/node_mature.prs.jsonl.gz       # 31 d, recorded from day 29 (~70 s)
prahari run --config configs/scenarios/node_mature__scmr-stub.yaml --out recordings/node_mature__scmr-stub.prs.jsonl.gz   # View 5 variant
prahari run --config configs/scenarios/gateway_outage.yaml --out recordings/gateway_outage.prs.jsonl.gz   # Phase 8 store-and-forward
prahari run --config configs/scenarios/cloudy_days.yaml --out recordings/cloudy_days.prs.jsonl.gz         # Phase 8 energy
prahari energy                                # Phase 8: M41–M43 comparison → results/energy.json
prahari run --config configs/scenarios/satellite_race.yaml --out recordings/satellite_race.prs.jsonl.gz   # Phase 9; also sensor_fault, lightning_storm(__no-relax), power_line_corridor, bushfire_afternoon (~1 min each)
prahari experiment --preset golden --jobs 4   # P0–P2, edge ablations, node metrics, dial → results/golden.json + summary.json
prahari experiment --preset ablation --jobs 4 # P2-QCC, P2-TTC (run after golden; joins summary.json)
prahari experiment --preset spacing --jobs 4  # P2 at 70/100/150 m, seeds 11,22,33
prahari experiment --preset seeds20 --jobs 4  # P0–P2 over seeds 11–30
prahari experiment --preset learning --jobs 4 # Phase 9: M36 learning curve + M26 maturity → results/learning.json (~5 min)
prahari experiment --preset golden --seeds 11 --pipelines P1   # quicker single-seed check
PRAHARI_GOLDEN=1 PRAHARI_JOBS=4 pytest engine/tests/golden   # golden tests (slow; skipped otherwise)
uvicorn server.app:app --reload               # live server (Phase 6); dashboard: Live engine ▸ Scenarios ▸ Start
cd dashboard && npm install && npm run dev    # dashboard (copies recordings/ in first)
cd dashboard && npm test                      # dashboard unit tests (Vitest)
cd dashboard && npm run build && npm run preview   # static build, no engine server
scripts/demo.sh [--build]                     # Phase 10: serve dashboard/dist on :8765 in presenter mode (Windows: scripts\demo.cmd)
prahari run --config configs/scenarios/wet_morning_haze.yaml --out recordings/wet_morning_haze.prs.jsonl.gz   # storyboard steps 3–4; also __scmr-stub, __raq-stub
pip install -e "engine[paper]"                 # research track: matplotlib for the paper figures (DECISIONS R2-5)
python -m prahari.research run selection --jobs 4   # protocol R1 (docs/research/protocol.md): seeds 901–920 (~1 h)
python -m prahari.research run test --jobs 4        # seeds 1001–1100 (~3–4 h; resumes: existing seed files are kept)
python -m prahari.research sweep --jobs 4           # sensitivity sweeps on seeds 1001–1010 (~2–3 h)
python -m prahari.research analyse                  # → results/research/r1_{selection,test,sweeps,analysis}.json
python -m prahari.research figures                  # → docs/research/figures/ (from the r1_*.json files only)
python -m prahari.research hazesplit                # R1 inside/outside-haze split (R2-10) → r1_haze_split.json
python -m prahari.research realdata                 # REAL: Thompson et al. N5 → real_thompson2026.json (also realdata-sc)
python -m prahari.research numbers                  # → docs/research/numbers.md (number-to-source table)
python -m prahari.research r2-run selection --jobs 4 [--scenarios H-mix]   # protocol R2 (docs/research/protocol-r2.md)
python -m prahari.research r2-run test --jobs 4     # every scenario with test seeds (~12 h; resumes)
python -m prahari.research r2-analyse               # → results/research/r2_*.json; then r2-figures
pytest engine/tests/unit/test_research_r2.py        # R2 unit and fidelity tests (~2 min)
python -m prahari.research r3-run selection --jobs 4   # protocol R3 (docs/research/protocol-r3.md); then r3-run test
python -m prahari.research r3-analyse               # → results/research/r3_*.json; then r3-figures
pytest engine/tests/unit/test_research_r3.py        # R3 fidelity and analysis tests (~1 min)
python -m prahari.research r4-run selection --jobs 4   # protocol R4 (docs/research/protocol-r4.md); then r4-run test
python -m prahari.research r4-analyse --selection-only # → results/research/r4_selection.json (--test-table: r4_test.json only; no flag: full analysis)
python -m prahari.research r4-seeds-archive test      # → results/research/r4_seeds_test.tar.gz (byte-reproducible seed records)
pytest engine/tests/unit/test_research_r4.py        # R4 checks: pairing, strict targets, analysis (~1 min)
```
