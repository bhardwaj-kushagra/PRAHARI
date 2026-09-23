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
