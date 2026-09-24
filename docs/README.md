# PRAHARI-SIM documentation

This folder explains the PRAHARI-SIM project: what it is, the ideas behind it, how to run it, how it is put
together, and how it was built phase by phase — including the problems met on the way and how each was handled.
Everything the simulator produces is **simulation output (SIM)**, not field data.

## Where to start

| If you want to… | Read |
| --- | --- |
| Understand the project in ten minutes | [guide/01-overview.md](guide/01-overview.md) |
| Learn the science and statistics behind it | [guide/02-background.md](guide/02-background.md), then [guide/03-glossary.md](guide/03-glossary.md) |
| Install and run it | [guide/04-setup.md](guide/04-setup.md) |
| Fix something that does not work | [guide/05-troubleshooting.md](guide/05-troubleshooting.md) |
| Present it to someone | [guide/06-demo-walkthrough.md](guide/06-demo-walkthrough.md) |
| See how the pieces fit together | [architecture/01-system.md](architecture/01-system.md) |
| Follow the build story, phase by phase | [journey/README.md](journey/README.md) |
| Check the numbers and how they were validated | [results/validation.md](results/validation.md) |

## Map of the folder

```text
docs/
├── README.md                  this page
├── SPEC.md                    the specification: requirements, equations M1–M46, phases, tests (source of truth)
├── guide/                     for a reader or presenter
│   ├── 01-overview.md         the problem, the system, the simulator, what "SIM" means
│   ├── 02-background.md       wildfire smoke, gas sensors, fuel moisture, radio links, detection statistics
│   ├── 03-glossary.md         every term and acronym used in the code and dashboard
│   ├── 04-setup.md            prerequisites, installation, every command
│   ├── 05-troubleshooting.md  symptoms → causes → fixes
│   └── 06-demo-walkthrough.md presenter-mode storyboard, click path, talking points, likely questions
├── architecture/              for a developer
│   ├── 01-system.md           components and data flow
│   ├── 02-engine.md           registry, stages, isolation, configuration, randomness, tick loop, harness
│   ├── 03-models.md           every model M1–M46: what it does, where it lives, its state
│   ├── 04-data-contracts.md   recordings, frames, traces, health and results files
│   ├── 05-dashboard.md        data sources, store, views, layers, charts, colours
│   └── 06-testing.md          test layers and how to run them
├── journey/                   how it was built
│   ├── README.md              timeline of phases
│   ├── phase-0-foundation.md … phase-10-demo.md
│   ├── release-1.0-audit.md   the final audit: findings, fixes, proof that outputs did not change
│   ├── challenges-and-lessons.md
│   └── decisions-and-tradeoffs.md
└── results/
    └── validation.md          golden numbers, equivalence checks, acceptance results
```

## How these documents relate to the logs

The repository root keeps three short logs of record, written as the work happens:

- `PROGRESS.md` — what each session did, test status, next step.
- `DECISIONS.md` — every deviation, interpretation, tuning choice and dependency, with an id (for example P5-10).
- `KNOWN_ISSUES.md` — parked modules and the improvement backlog.

The pages here explain those entries in full sentences and link back to their ids. When the two disagree, the logs
and the code win; please fix the page. From Phase 6 onwards every phase updates these pages as part of its work
(`CLAUDE.md` rule 16, SPEC §7).

For the conference itself, [`DEMO_CHECKLIST.md`](../DEMO_CHECKLIST.md) in the repository root is the one page to
follow (Phase 10).
