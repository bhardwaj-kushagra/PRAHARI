# The build journey

PRAHARI-SIM was built in phases defined in [SPEC §7](../SPEC.md). Each phase started with a written plan (what will be
built, which files, which tests prove it), was implemented with tests, ended with a runnable dashboard, and was
accepted by the developer before the next began. All phases, 0 to 10 (with 3a and 3b), were built and accepted on
23–24 September 2026 in one long working session with an AI coding agent (Claude Code), under the rules in `CLAUDE.md`.

## Timeline

| Phase | Goal | Outcome | Key numbers (SIM) | Page |
| --- | --- | --- | --- | --- |
| 0 | Foundation and replay shell | accepted | 23 modules with stubs; 1-day smoke run in ~1.6 s; byte-identical recordings | [phase-0-foundation.md](phase-0-foundation.md) |
| 1 | World, network and siting | accepted | covered likelihood grid 24%, corridor 49%, greedy 83% | [phase-1-world-siting.md](phase-1-world-siting.md) |
| 2 | Weather, fuel moisture, sensor signals | accepted | FFMC within 0.005 of cffdrs over 48 days | [phase-2-signals.md](phase-2-signals.md) |
| 3a | Fires and plumes (legacy) | accepted | 2.5 su at 50 m downwind, 0.25 su upwind | [phase-3a-fires.md](phase-3a-fires.md) |
| 3b | Gaussian plume (optional) | accepted | calibrated to the legacy 2.5 su; σ_y profile within 0.1% | [phase-3b-gaussian-plume.md](phase-3b-gaussian-plume.md) |
| 4 | Baselines and evaluation harness | accepted | P1 136.2/month (in the report's interval); P0 340.6 (outside; explained) | [phase-4-baselines.md](phase-4-baselines.md) |
| 5 | PRAHARI node layer | accepted | QCC exceedance 1.10%; 0.65 local false candidates per node per 30 d | [phase-5-node-layer.md](phase-5-node-layer.md) |
| 6 | Edge layer, trace, live mode | accepted | P2 3.4 false incidents/month, 75.9% detection (report 6.4, 83%; diagnosed); SCMR cuts haze alarms 15 → 3; live mode | [phase-6-edge-layer.md](phase-6-edge-layer.md) |
| 7 | Experiments and results | accepted | P2 3.4 false incidents/month (P0 340.6); every ablation raises false alarms; dial 46–67 min median; spacing 63/33/5% confirmed; legacy ablations reproduce the report simulation; detection gap traced by a 2 × 2 swap to sampling (haze-heavy calibration windows, wet-day share) | [phase-7-experiments.md](phase-7-experiments.md) |
| 8 | Communications and energy | accepted | M39 61.7 / 1,482.75 ms; ALOHA within 1.1 points of e^(−2G); 0.5 Wh/day node lasts 8.7–9.1 days; store-and-forward across a gateway outage; BME688 0.42 vs MQ-2 22.9 Wh/day | [phase-8-comms-energy.md](phase-8-comms-energy.md) |
| 9 | Regimes, satellite race, learning loop, faults | accepted | PRAHARI confirmed about 8 h before the satellite alert (`satellite_race`); stuck sensor abstains after 59 min; learning curve 49% (bound) → 68–71% confirmed at 3 false incidents/month for K = 10–100; QCC floor 4.1e-3 → 3.0e-4 from 1 to 14 quiet days | [phase-9-regimes-learning.md](phase-9-regimes-learning.md) |
| 10 | Demo hardening | accepted | presenter mode (keys 1–9, S/R, F); storyboard rehearsal 170.1 s with no external requests and no console errors; one-command launchers for macOS, Linux and Windows | [phase-10-demo.md](phase-10-demo.md) |
| 1.0 | Final audit and hardening | released | 13 findings (2 dashboard defects, 7 robustness, 3 documentation, 1 limitation) fixed or logged; every recording and result reproduces byte for byte; golden pattern unchanged (5 of 21); 60-page browser sweep and rehearsal clean | [release-1.0-audit.md](release-1.0-audit.md) |

Cross-cutting pages:

- [challenges-and-lessons.md](challenges-and-lessons.md) — the problems met across phases and how each was resolved.
- [decisions-and-tradeoffs.md](decisions-and-tradeoffs.md) — the major decisions with their alternatives, pros and
  cons.

## How a phase was run

1. **Read** `PROGRESS.md`, `KNOWN_ISSUES.md`, `DECISIONS.md`, the SPEC principles and the phase's section.
2. **Plan**: a short written plan with files and acceptance tests; the developer says "go".
3. **Build** in small pure functions with M-number comments; real stages beside their stubs.
4. **Test**: unit tests with reference values, oracle cross-checks where possible, the full suite, a browser check.
5. **Record**: update `PROGRESS.md`, `DECISIONS.md`, `KNOWN_ISSUES.md` and (from now on) these pages; regenerate
   recordings; commit and push.
6. **Review**: the developer opens the named dashboard view and accepts, or asks for changes.

## Reading a phase page

Every phase page has the same sections: goal; what was built; how it works; challenges and issues; decisions and
trade-offs; resolution of each issue; acceptance results; what to show in a demo. Decision ids such as `P4-6` refer to
entries in `DECISIONS.md` at the repository root.
