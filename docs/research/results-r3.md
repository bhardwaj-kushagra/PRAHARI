# Research protocol R3 — results (SIM)

**Protocol:** [protocol-r3.md](protocol-r3.md), registered in `e82ab55` before any R3 run. The selection was
committed in `9eec436` before any test seed ran. **No deviation:** nothing in the protocol, code, grids or rules
changed after registration.

**Numbers:** every number here is **SIM** and comes from `results/research/r3_analysis.json` (keys in brackets),
built by `python -m prahari.research r3-analyse`. [numbers.md](numbers.md) maps each one to its key. The page's
tables were generated from that file, not typed.

**Seeds:** H-mix selection 3901–3920, test 4001–4100; H-sync 4101–4150; H-gain 4151–4200; H-patch 4201–4250.
**Set-up:** 100 nodes at 70 m, 30 test days per seed after 28 days of calibration and tuning (R2's golden base and
M20b haze, unchanged). Differences are always **P2-medSCMR − P2-gate**, per seed.

**Validity rule** (registered from the start): no setting of any method was invalid on the selection seeds [`selection.methods.<m>.invalid_cells`],
and every selected setting is valid on every test scenario [`…valid_here`]. The rule
therefore changed nothing in R3.

## 1. Selection (H-mix selection seeds, pooled)

**B\* = 1** false incident a month [`b_star`]: the smallest of {1, 3, 10, 30} that both compared methods reach.
Settings are [r, ρ] for P2 and P2-medSCMR, [r, θ] for P2-gate.

| Method | Floor setting (selection FA / det.) | Operating setting at 1/month | Operating setting at 3/month | Operating setting at 10/month | Operating setting at 30/month |
| --- | --- | --- | --- | --- | --- |
| median + SCMR (P2-medSCMR) | [0.1, 10] (0.9 / 31.2%) | [0.3, 10] (1 / 47.8%) | [3, 10] (2.2 / 88.7%) | [6, 10] (5.9 / 91.9%) | [10, 4] (26.9 / 96.2%) |
| evidence gate (P2-gate) | [0.2, 0.05] (0 / 1.2%) | [0.3, 0.2] (0.8 / 65.4%) | [1, 0.3] (3 / 84.8%) | [3, 0.3] (7.4 / 91.9%) | [6, off] (23.1 / 94.5%) |
| P2 (SCMR, reference) | [0.2, 10] (0.6 / 71.2%) | [0.3, 10] (0.7 / 75.0%) | [2, 10] (2.75 / 88.6%) | [4.3, 6] (9.05 / 92.8%) | [10, 6] (26.55 / 95.3%) |

[`selection.methods.<m>`]

## 2. Confirmatory tests (H-mix test seeds 4001–4100)

Two-sided paired Wilcoxon signed-rank on per-seed values, paired seed-bootstrap 95% interval of the mean difference,
Holm across {H1, H2} at α = 0.05 [`scenarios.H-mix.head_to_head`].

| Endpoint | P2-medSCMR − P2-gate (95% CI) | Wilcoxon p | Holm p | Seeds higher / lower |
| --- | --- | --- | --- | --- |
| **H1** detection at B* = 1 (share of fires confirmed within 3 h) | -8.7 points (-14.8 to -2.8) | 0.012 | 0.012 (reject) | 45 / 54 |
| **H2** floor (false incidents per month at the floor settings) | +0.45 (+0.24 to +0.67) | 0.00014 | 0.00028 (reject) | 33 / 6 |

- **H1:** rejected. At B* = 1, the evidence gate confirms more fires than median + SCMR.
- **H2:** rejected. The evidence gate has the lower floor.

## 3. The false-alarm floor (E1, E3)

At each method's floor setting from §1, with the split by whether the incident started inside haze
[`scenarios.H-mix.methods.<m>.floor_at_selected_knob`]. *Det.* is the share of fires that setting confirms.

| Method | Setting | False incidents / month (95% CI) | Inside haze | Outside haze | Share inside | Det. |
| --- | --- | --- | --- | --- | --- | --- |
| median + SCMR (P2-medSCMR) | [0.1, 10] | 0.58 (0.40–0.78) | 0.47 | 0.11 | 81.0% | 22.9% |
| evidence gate (P2-gate) | [0.2, 0.05] | 0.13 (0.04–0.24) | 0.13 | 0.00 | 100.0% | 1.4% |
| P2 (SCMR, reference) | [0.2, 10] | 0.79 (0.62–0.96) | 0.66 | 0.13 | 83.5% | 52.3% |

## 4. Detection at B* = 1 a month (E2, E4 at B*, E5)

[`scenarios.H-mix.methods.<m>.at_b_star`]. *Mean TTC*: mean time to confirmation, a miss counting as 180 min.

| Method | Setting | Confirmed within 3 h (95% CI) | False incidents / month | Mean TTC | Median latency | Fires overlapping haze | Others |
| --- | --- | --- | --- | --- | --- | --- | --- |
| median + SCMR (P2-medSCMR) | [0.3, 10] | 40.2% (35.0%–45.5%) | 1.24 | 143 min | 85 min | 37.3% (107/287) | 40.4% (2276/5634) |
| evidence gate (P2-gate) | [0.3, 0.2] | 48.1% (42.6%–53.5%) | 1.04 | 133 min | 75 min | 37.6% (108/287) | 48.7% (2743/5634) |
| P2 (SCMR, reference) | [0.3, 10] | 57.2% (51.3%–62.9%) | 0.75 | 121 min | 69 min | 45.3% (130/287) | 57.9% (3260/5634) |

## 5. Descriptive: every budget (H-mix test seeds)

**Deployment view:** each method at its operating setting for the budget, chosen on the selection seeds
[`scenarios.H-mix.head_to_head.descriptive_by_budget`]. The p-values are unadjusted and not confirmatory.

| Budget | P2-medSCMR: det. / FA | P2-gate: det. / FA | Difference (95% CI) | Wilcoxon p | Seeds higher / lower |
| --- | --- | --- | --- | --- | --- |
| 1/month | 40.2% / 1.24 | 48.1% / 1.04 | -8.7 (-14.8 to -2.8) | 0.012 | 45 / 54 |
| 3/month | 85.2% / 2.16 | 74.8% / 3.00 | +10.3 (+6.9 to +13.8) | 9.1e-09 | 76 / 18 |
| 10/month | 90.6% / 4.80 | 87.5% / 7.39 | +3.1 (+1.7 to +4.6) | 6.3e-05 | 56 / 24 |
| 30/month | 95.2% / 24.43 | 92.8% / 20.91 | +2.4 (+1.6 to +3.2) | 1.6e-07 | 65 / 17 |

**Equal-false-alarm view (R8):** each method's pooled Pareto curve on the test seeds, interpolated at the budget
[`scenarios.H-mix.methods.<m>.det_at_equal_fa`]. 0.0% means the curve does not reach that budget (its lowest rate
is above it).

| Method | 1/month | 3/month | 10/month | 30/month |
| --- | --- | --- | --- | --- |
| median + SCMR (P2-medSCMR) | 40.6% | 87.8% | 92.4% | 95.6% |
| evidence gate (P2-gate) | 47.0% | 76.6% | 87.8% | 94.3% |
| P2 (SCMR, reference) | 69.8% | 85.3% | 90.1% | 94.7% |

## 6. Secondary scenarios (descriptive)

Deployment view: the H-mix settings of §1, on each scenario's test seeds. The tests are the same as §2 but are
descriptive here; their Holm step is within each scenario only [`scenarios.<s>.head_to_head`].

| Scenario | H1 analogue: detection at B* (95% CI) | Holm p | H2 analogue: floor (95% CI) | Holm p |
| --- | --- | --- | --- | --- |
| H-mix | -8.7 (-14.8 to -2.8) | 0.012 | +0.45 (+0.24 to +0.67) | 0.00028 |
| H-sync | +12.4 (+5.2 to +19.8) | 0.0055 | -0.42 (-0.96 to +0.02) | 0.17 |
| H-gain | -11.7 (-19.4 to -4.1) | 0.07 | +0.38 (+0.00 to +0.76) | 0.07 |
| H-patch | +10.6 (+4.2 to +16.4) | 7.1e-05 | +1.26 (+0.92 to +1.64) | 7e-07 |

Det. at equal FA = B* is 0.0% where the method's curve on that scenario stays above B* (P2 and median + SCMR in H-patch).

| Scenario | Method | Floor at H-mix setting (inside haze) | Own lowest floor | Det. at B* (FA/month) | Det. at equal FA = B* |
| --- | --- | --- | --- | --- | --- |
| H-mix | median + SCMR (P2-medSCMR) | 0.58 (0.47) | 0.58 at [0.1, 10] | 40.2% (1.24) | 40.6% |
| H-mix | evidence gate (P2-gate) | 0.13 (0.13) | 0.12 at [0.3, 0.05] | 48.1% (1.04) | 47.0% |
| H-mix | P2 (SCMR, reference) | 0.79 (0.66) | 0.73 at [0.1, 10] | 57.2% (0.75) | 69.8% |
| H-sync | median + SCMR (P2-medSCMR) | 0.22 (0.10) | 0.22 at [0.1, 10] | 65.8% (0.38) | 85.4% |
| H-sync | evidence gate (P2-gate) | 0.64 (0.64) | 0.64 at [0.2, 0.05] | 53.4% (1.76) | 19.7% |
| H-sync | P2 (SCMR, reference) | 0.40 (0.34) | 0.40 at [0.2, 10] | 63.0% (0.56) | 73.1% |
| H-gain | median + SCMR (P2-medSCMR) | 0.70 (0.48) | 0.70 at [0.1, 10] | 36.6% (1.00) | 36.6% |
| H-gain | evidence gate (P2-gate) | 0.32 (0.32) | 0.26 at [0.1, 0.05] | 48.8% (1.20) | 47.2% |
| H-gain | P2 (SCMR, reference) | 0.62 (0.52) | 0.42 at [0.1, 10] | 58.2% (0.76) | 69.7% |
| H-patch | median + SCMR (P2-medSCMR) | 1.26 (1.12) | 1.26 at [0.1, 10] | 48.8% (1.90) | 0.0% |
| H-patch | evidence gate (P2-gate) | 0.00 (0.00) | 0.00 at [1.5, 0.05] | 38.2% (0.48) | 59.2% |
| H-patch | P2 (SCMR, reference) | 1.34 (1.30) | 1.28 at [0.1, 10] | 47.4% (1.50) | 0.0% |

## 7. Reading (SIM)

1. **At the strictest budget the gate wins; from 3 a month median + SCMR wins.** H1 favours the evidence gate by 8.7 points at B* = 1 (Holm p 0.012). At 3, 10 and 30 a month the sign reverses: median + SCMR confirms +10.3, +3.1 and +2.4 points more (descriptive). The ranking depends on the budget, so neither method
   dominates.
2. **The gate's lower floor is bought with detection.** H2 confirms the gate's lower floor (0.13 against 0.58 a month, Holm p 0.00028). But at that setting the gate confirms 1.4% of fires, and median + SCMR 22.9%. Every gate floor incident starts inside haze (100.0%); median + SCMR's share is 81.0%.
3. **Neither beats plain SCMR at B\* = 1.** The reference P2 confirms 57.2% at 0.75 false incidents a month, against 48.1% (gate) and 40.2% (median + SCMR). At equal false alarms the order holds: 69.8%, 47.0%, 40.6%. P2 was not part of any test; this is descriptive.
4. **Median + SCMR overshoots the budget on new seeds.** Its B* setting gave 1 a month on the selection seeds and 1.24 on the test seeds; the gate's gave 0.8 and 1.04. With only 20 selection seeds, operating points near 1 a month are noisy.
5. **The detection ranking at B\* changes with the haze.** Median + SCMR leads under synchronous haze (+12.4 points) and narrow patches (+10.6); the gate leads under uneven gain (-11.7, Holm p 0.07) and on H-mix. The gate's floor is lower in H-mix, H-gain and H-patch (0.00 there; that is why its bar is absent in the scenario figure) but not under synchronous haze.
6. **R2's result at 10 a month replicates on fresh seeds.** At 10 a month median + SCMR confirms 90.6% and the gate 87.5% (R2, at its B* = 10: 92.2% and 89.1%; `r2_analysis.json`).

**Limits:** simulation only; one network geometry (100 nodes at 70 m); 30 test days per seed; the selection uses 20
seeds, so settings near the strictest budget transfer imperfectly (point 4).

## Figures

All from `r3_analysis.json`, via `python -m prahari.research r3-figures`; footers give the seeds.

- [r3_floor_H-mix.png](figures/r3_floor_H-mix.png) ([PDF](figures/r3_floor_H-mix.pdf)): Floors at the selected settings, split inside/outside haze (H-mix test seeds).
- [r3_pareto_H-mix.png](figures/r3_pareto_H-mix.png) ([PDF](figures/r3_pareto_H-mix.pdf)): Pareto fronts: detection against false incidents per month (H-mix test seeds).
- [r3_amoc_H-mix.png](figures/r3_amoc_H-mix.png) ([PDF](figures/r3_amoc_H-mix.pdf)): AMOC: mean time to confirmation against false incidents per month (H-mix).
- [r3_scenarios.png](figures/r3_scenarios.png) ([PDF](figures/r3_scenarios.pdf)): Each method's own lowest floor in every scenario.
