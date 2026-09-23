# KNOWN_ISSUES

Modules parked as stubs under the escape hatch (CLAUDE.md rule 6). Each entry: module, phase, symptoms, what was tried, best diagnosis, current state.

| Module | Phase | Symptoms | Tried | Diagnosis | State |
| --- | --- | --- | --- | --- | --- |
| — | — | Nothing parked yet | — | — | — |

## Improvement backlog (not parked)

Findings where the implementation is correct and matches the report's method, but the method itself could be
improved. They are deliberately deferred so that the main implementation (Phases 6–7) is finished first; each has a
proposal and a point at which to revisit it.

| Item | Found | Symptoms | Diagnosis | Proposal | Revisit |
| --- | --- | --- | --- | --- | --- |
| M28 common-mode exclusion misses a second network-wide rise right after a long one | Phase 5 | Golden seed 22: the node CUSUM's replay tuning ends at the 400 cap; that seed's test-period node-local rate falls to 0.03 per node per 30 d | During a long haze episode the capped slow baseline inflates s² (winsorised updates), so in the next rise only ≈ 10% of nodes reach slow z ≥ 3 (< 25%) although every node's −ln p is near its floor; 67 simultaneous candidates count as node-local. The engine's slow z equals the report's exactly, so the report's method shares it (its seed-55 outlier looks alike). Detail: `DECISIONS.md` P5-10 | Advanced option `cm_signal: evidence`: define common mode from the detection evidence (share of nodes with p ≤ 0.01, or with G above a fraction of h), keeping `slow_z` as the legacy default | After Phase 7 (golden P2 numbers first) |
| P2 detection below the report's interval in legacy mode | Phase 6; updated Phase 7 | Golden P2 confirmed within 3 h 71.3% (report 79–87%); seeds 11–30: 72.8% vs the report simulation's 82.2% (p 0.015); fresh seeds 31–50: 79.4% vs 84.4% (p 0.16); false alarms agree throughout; the ablations, spacing and legacy ablations show the same pattern | No model difference found. Same code (engine chains reproduce the report simulation on its own signals, P2 and both legacy ablations); same fire model (footprint check); same haze model (200 histories each, all KS p > 0.6); background calibration tails not significantly different on 60 fresh seeds (p 0.17–0.51, engine slightly higher). The 2 × 2 reverse swap over seeds 11–30 splits the gap between the engine seeds' haze-heavy calibration windows (background, 4.6–7.4 points) and the report seeds' low share of wet-day fires (16.7% vs the expected 20%; fire set, 2.0–4.8 points). Detail: `DECISIONS.md` P6-11, P7-9, P7-14 | Treat as sampling. If a small residual background difference matters for the demo, run a larger model-level comparison (e.g. 200 seeds of the calibration-tail statistic); method option for the advanced mode: exclude haze periods from the conformal calibration set | Optional; after the developer's review |
| ~~Node ablations are not the report simulation's variants~~ — **resolved (Phase 7 follow-up)** | Phase 7 | P2-QCC 30.8 and P2-TTC 8.2 false incidents/month as module stubs | Built the legacy forms (`experiment.ablation_form: legacy`): the report simulation's results on its own signals (P2-QCC exact; P2-TTC exact apart from its day-1 look-ahead). Detail: `DECISIONS.md` P7-12, P7-13 | — | Done |
