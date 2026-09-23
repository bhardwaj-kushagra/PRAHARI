# PRAHARI-SIM — starter kit

Simulator and dashboard for the FIRENET–PRAHARI wildfire-detection system, built phase by phase with an AI coding agent.

## What's here

| File | Purpose |
| --- | --- |
| `CLAUDE.md` | Rules the agent must follow. Claude Code loads it automatically at the start of every session in this folder. |
| `docs/SPEC.md` | Full specification: architecture, all equations (M1–M46), phases 0–10, dashboard, tests, demo storyboard, prompt pack. |
| `reference/prahari_simulation.py` | The original research simulation from the report — the oracle for golden tests. Read-only. |
| `reference/prahari_aggregate_results.py` | Script that produced the report's tables. |

## How to start

1. Clone the repository and open it in VS Code (it is already a git repository).
2. Start Claude Code in this folder. Run `/context` once to confirm `CLAUDE.md` appears under memory files.
3. Paste the "Session start" prompt from `docs/SPEC.md` §12 with N = 0. Review its plan, then say go.
4. Work one phase per session or two. After each phase, open the dashboard view the agent names, and run the "Review before accepting" prompt.
5. Phases 0–6 plus 10 give the complete conference demo. Phases 7–9 add depth when time allows.

## Run it

```text
pip install -e engine[dev]
pytest engine/tests
prahari run --config configs/scenarios/smoke.yaml --out recordings/smoke.prs.jsonl.gz
cd dashboard && npm install && npm run dev      # open the printed URL
```

Progress by phase is in `PROGRESS.md`; every deviation and dependency is in `DECISIONS.md`.

## If something gets stuck

Use the "When stuck" prompt in §12. The module is parked as a stub, logged in `KNOWN_ISSUES.md`, and everything else keeps working.

VS Code's built-in Markdown preview (Ctrl+Shift+V) renders the equations in `docs/SPEC.md`.
