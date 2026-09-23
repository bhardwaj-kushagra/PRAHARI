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
| P2 detection below the report's interval in legacy mode | Phase 6; updated Phase 7 | Golden P2 confirmed within 3 h 71.3% (report 79–87%); over seeds 11–30 the engine's P2 detects 72.8% against the report simulation's 82.2% (p 0.015) while false alarms agree (6.25 vs 7.20 per month); P2-SCMR and P2-RAQ show the same pattern; the baselines' detection agrees; spacing and ablation confirmation rates follow P2 | Our node and edge code reproduces the report simulation exactly on its own data, and with per-fire wind (P7-1) the fire footprint is the same (seed 11: 5.19 vs 5.10 nodes lifted by ≥ 1 su). The difference sits in the quiet calibration data: haze gives the engine's fast residual a much heavier upper tail (seed 11: 2.2% of minutes above 1 su vs 0.29%; 0.18% with haze off), which widens the conformal reference sets. The haze model is the same; the engine's seeds 11–30 drew more episodes (66 vs 45 in days 0–27). On fresh seeds 31–50 the gap halves (79.4% vs 84.4%, p 0.16) with identical false alarms; over all 40 seeds about 7 points remain (p 0.007). Detail: `DECISIONS.md` P6-11, P7-9 | Next diagnostic: a reverse swap (the report simulation's quiet background through the engine's chain). Method option (with the M28 item above): exclude haze periods from the conformal calibration set, as an advanced, non-legacy setting | With the M28 common-mode item, after the developer's review |
| Node ablations are not the report simulation's variants | Phase 7 | P2-QCC 30.8 false incidents/month (report 17.4, 13.9–21.5); P2-TTC 8.2 (report 11.8, 9.0–15.2) | Ours replace the module by its stub (P2-QCC: Gaussian p of the slow z, k 1.5; P2-TTC: v1 slow residual without the cap). The report simulation's "minus conformal" runs the CUSUM on the MAD-scaled fast residual with k 0.5; "minus two-timescale" uses a conformal p of the capped slow z. Detail: `DECISIONS.md` P7-10 | Legacy ablation forms selected by parameters (`ttc.detect_on: slow`, `qcc.form: gaussian_fast`, `cusum.statistic: z`), each a small addition to accepted Phase 5 modules — needs approval (rule 4) | On approval |
