# Research protocol R4 — results (SIM)

**Protocol:** [protocol-r4.md](protocol-r4.md), registered in `e81fa33` before any R4 seed ran. The selection was
committed in `5855841` (7 Oct 2026, 13:45:20 UTC) before any test seed ran; every test seed file was written after
it. The seed files are archived in `results/research/r4_seeds_selection.tar.gz` and `r4_seeds_test.tar.gz`.

**Changes after registration, both logged:**

- **R4-2:** a records-only writer for the per-seed table `r4_test.json`.
- **R4-3:** three registered descriptive items were completed in code before the analysis ran:
  - the haze split for every floor;
  - the deployment-view floors in the dose table;
  - the method differences.
- **Unchanged:** family P, the selection, and every rule and setting.

**Claim:** the paper's claim and title are not reframed here (the developer's decision of 7 Oct). This page reports
the registered outcome and the protocol's own registered reading (§7 of the protocol).

**Numbers:** every number here is **SIM** and comes from `results/research/r4_analysis.json` (keys in brackets) or
`r4_selection.json`, built by `python -m prahari.research r4-analyse`. [numbers.md](numbers.md) maps each one to its
key (rows starting "R4"). The page's tables were generated from those files, not typed.

**Set-up:**

- 100 nodes at 70 m; 30 test days per seed after 28 days of calibration and tuning.
- The scenarios differ only in the haze-episode rate: ×0 (H-none), ×0.3, ×1 (H-mix, R2's) and ×3.
- Every scenario uses the same seed numbers, so all comparisons between scenarios are paired by seed. The haze is
  the only difference; protocol §9 checked this.

## 1. Selection (50 selection seeds per scenario, 5901–5950)

Each of H-none and H-mix was selected on its own runs. Settings are [r, ρ] for P2 and median + SCMR, [r, θ] for the
gate; each cell gives the setting, then its false incidents a month and detection on the selection seeds
[`selection.<scenario>.methods.<m>`, `r4_selection.json`]. No setting was invalid.

| Scenario | Method | 0.3 a month | 1 a month | 3 a month | 10 a month | Useful floor |
| --- | --- | --- | --- | --- | --- | --- |
| H-none | P2 (SCMR) | [0.5, 10]: 0.3, 83.7% | [1, 6]: 0.72, 88.3% | [3, 10]: 2.68, 92.2% | [4.3, 4]: 8.36, 94.9% | [0.05, 0]: 0, 70.7% |
| H-none | median + SCMR | [1, 0]: 0.26, 88.8% | [1.5, 0]: 0.68, 91.4% | [3, 10]: 2.68, 93.1% | [4.3, 6]: 5.94, 95.3% | [0.03, 0]: 0, 70.2% |
| H-none | evidence gate | [0.5, 0.3]: 0.3, 84.2% | [1, 0.5]: 0.92, 88.3% | [2, 0.5]: 2.7, 91.5% | [4.3, off]: 8.8, 94.9% | [0.05, 0.5]: 0, 70.7% |
| H-mix | P2 (SCMR) | not reached | [0.5, 10]: 0.88, 62.8% | [2, 10]: 2.12, 80.8% | [4.3, 6]: 8.6, 89.2% | [0.2, 10]: 0.8, 52.6% |
| H-mix | median + SCMR | not reached | [0.5, 10]: 0.96, 44.9% | [3, 10]: 2.4, 82.8% | [10, 10]: 9.94, 92.8% | [0.75, 10]: 1.06, 54.3% |
| H-mix | evidence gate | [0.03, 0.15]: 0.3, 14.6% | [0.3, 0.2]: 0.82, 47.5% | [1, 0.3]: 2.94, 73.5% | [3, 0.3]: 7.44, 86.2% | [0.5, 0.2]: 1.18, 53.1% |

## 2. Family P: the price of haze at 1 false incident a month (confirmatory)

Per seed, detection at 1 a month without haze minus with H-mix haze, each at its own selected setting. Two-sided
Wilcoxon signed-rank on the 100 paired seeds (6001–6100), seed-bootstrap 95% interval of the mean difference, Holm
across the three methods [`family_P`].

| Method | Detection without haze | Detection with H-mix haze | Difference, points (95% CI) | Wilcoxon p | Holm p | Seeds higher / lower |
| --- | --- | --- | --- | --- | --- | --- |
| P2 (SCMR) | 88.9% (0.76 FA/month) | 66.9% (0.91 FA/month) | +22.1 (+17.5 to +27.0) | 5.7e-18 | 1.2e-17 (rejected) | 99 / 0 |
| median + SCMR | 90.8% (0.69 FA/month) | 53.3% (1.15 FA/month) | +37.2 (+32.0 to +42.6) | 6.1e-18 | 1.2e-17 (rejected) | 98 / 1 |
| evidence gate | 88.9% (1.08 FA/month) | 52.9% (1.01 FA/month) | +36.0 (+31.0 to +41.4) | 3.9e-18 | 1.2e-17 (rejected) | 100 / 0 |

**Outcome:** the null hypothesis of no difference is rejected for 3 of 3 methods (Holm),
every difference positive. At 1 false incident a month, regional haze costs every
method detection: 22.1–37.2 points.

## 3. The price at the other budgets (descriptive)

**Deployment view:** each scenario at its own selected setting; unadjusted p [`descriptive.price_by_budget`].

| Method | 0.3 a month | 3 a month | 10 a month |
| --- | --- | --- | --- |
| P2 (SCMR) | not computable (H-mix does not reach it) | +9.0 (+7.4 to +10.7); p 1.5e-16 | +4.5 (+3.6 to +5.5); p 1.2e-13 |
| median + SCMR | not computable (H-mix does not reach it) | +7.0 (+5.7 to +8.5); p 5.3e-15 | +2.2 (+1.6 to +2.8); p 2.3e-09 |
| evidence gate | +66.8 (+64.0 to +69.8); p 3.9e-18 | +15.0 (+11.9 to +18.3); p 1.2e-17 | +6.7 (+5.5 to +8.0); p 3.2e-16 |

**Equal-false-alarm view (R8):** detection on each scenario's pooled test-seed curve, without haze minus with haze,
in points; 0 detection is counted where a curve does not reach the budget [`descriptive.price_at_equal_fa`].

| Method | 0.3 a month | 1 a month | 3 a month | 10 a month |
| --- | --- | --- | --- | --- |
| P2 (SCMR) | +85.9 | +15.3 | +5.4 | +4.5 |
| median + SCMR | +88.9 | +55.4 | +4.7 | +3.2 |
| evidence gate | +71.4 | +36.2 | +14.4 | +6.3 |

## 4. Floors without and with haze (descriptive)

On the test seeds, at the settings selected in §1 [`scenarios.<scenario>.floors.<m>`]. *Useful floor:* the lowest
false incidents among settings that detected at least 50% on the selection seeds. Every incident without haze is
outside haze by construction.

| Method | Scenario | Floor: FA/month (95% CI), detection | Useful floor: FA/month (95% CI), detection | Useful floor inside / outside haze (share inside) |
| --- | --- | --- | --- | --- |
| P2 (SCMR) | H-none | 0.07 (0.01–0.15), 71.4% | 0.07 (0.01–0.15), 71.4% | 0.00 / 0.07 (0.0%) |
| P2 (SCMR) | H-mix | 0.77 (0.57–0.98), 44.0% | 0.85 (0.63–1.09), 57.6% | 0.79 / 0.06 (92.9%) |
| median + SCMR | H-none | 0.00 (0.00–0.00), 70.7% | 0.00 (0.00–0.00), 70.7% | 0.00 / 0.00 (—) |
| median + SCMR | H-mix | 0.61 (0.44–0.80), 24.5% | 1.42 (1.18–1.69), 61.6% | 0.99 / 0.43 (69.7%) |
| evidence gate | H-none | 0.06 (0.00–0.14), 71.4% | 0.06 (0.00–0.14), 71.4% | 0.00 / 0.06 (0.0%) |
| evidence gate | H-mix | 0.06 (0.02–0.11), 0.8% | 1.17 (0.88–1.48), 57.5% | 1.02 / 0.15 (87.2%) |

## 5. Stricter node thresholds (question 3; descriptive)

The same floors, selected with and without the node targets r = 0.03 and 0.05; the share of capped thresholds
[`…floors.<m>.floor_r_ge_0.1`, `…share_capped_by_target`].

| Method | Scenario | Floor, all targets | Floor, r ≥ 0.1 | Useful floor, all targets | Useful floor, r ≥ 0.1 | Capped at r = 0.03 / 0.05 |
| --- | --- | --- | --- | --- | --- | --- |
| P2 (SCMR) | H-none | [0.05, 0]: 0.07, 71.4% | [0.1, 0]: 0.11, 75.2% | [0.05, 0]: 0.07, 71.4% | [0.1, 0]: 0.11, 75.2% | 0.0% / 0.0% |
| P2 (SCMR) | H-mix | [0.03, 10]: 0.77, 44.0% | [0.1, 10]: 0.79, 51.3% | [0.2, 10]: 0.85, 57.6% | [0.2, 10]: 0.85, 57.6% | 0.0% / 0.0% |
| median + SCMR | H-none | [0.03, 0]: 0.00, 70.7% | [0.1, 0]: 0.00, 77.3% | [0.03, 0]: 0.00, 70.7% | [0.1, 0]: 0.00, 77.3% | 0.0% / 0.0% |
| median + SCMR | H-mix | [0.03, 10]: 0.61, 24.5% | [0.1, 10]: 0.81, 30.5% | [0.75, 10]: 1.42, 61.6% | [0.75, 10]: 1.42, 61.6% | 0.0% / 0.0% |
| evidence gate | H-none | [0.05, 0.5]: 0.06, 71.4% | [0.1, 0.15]: 0.01, 25.1% | [0.05, 0.5]: 0.06, 71.4% | [0.1, 0.2]: 0.01, 56.6% | 0.0% / 0.0% |
| evidence gate | H-mix | [0.05, 0.05]: 0.06, 0.8% | [1, 0.05]: 0.19, 3.0% | [0.5, 0.2]: 1.17, 57.5% | [0.5, 0.2]: 1.17, 57.5% | 0.0% / 0.0% |

## 6. Dose–response (seeds 6001–6050 in every scenario; descriptive)

Deployment view: ×0.3 and ×3 use H-mix's settings and ×0 uses H-none's. Equal false alarms: R8 on each scenario's
own curve, 0 where 1 a month is not reached [`descriptive.dose_response`].

| Method | Measure | ×0 | ×0.3 | ×1 | ×3 |
| --- | --- | --- | --- | --- | --- |
| P2 (SCMR) | detection at 1 a month, deployment (FA/month) | 88.6% (0.8) | 80.0% (0.42) | 63.1% (0.9) | 35.3% (1.9) |
| P2 (SCMR) | detection at 1 a month, equal false alarms | 88.7% | 85.5% | 68.3% | 0.0% |
| P2 (SCMR) | useful floor at the selected setting (detection) | 0.1 (71.4%) | 0.3 (73.6%) | 1.02 (53.8%) | 1.56 (26.5%) |
| median + SCMR | detection at 1 a month, deployment (FA/month) | 90.3% (0.7) | 71.3% (0.4) | 51.8% (1.26) | 21.5% (2.72) |
| median + SCMR | detection at 1 a month, equal false alarms | 90.9% | 87.1% | 38.0% | 5.3% |
| median + SCMR | useful floor at the selected setting (detection) | 0 (70.3%) | 0.36 (77.6%) | 1.46 (60.1%) | 2.54 (30.0%) |
| evidence gate | detection at 1 a month, deployment (FA/month) | 88.7% (1.04) | 63.2% (0.34) | 48.5% (1.18) | 26.9% (3.08) |
| evidence gate | detection at 1 a month, equal false alarms | 88.6% | 81.6% | 45.5% | 9.2% |
| evidence gate | useful floor at the selected setting (detection) | 0.1 (71.4%) | 0.4 (67.4%) | 1.08 (53.7%) | 3.6 (32.0%) |

## 7. Other measures at 1 a month (descriptive)

**Fires overlapping haze (E5) and time to confirmation (E4)**, each scenario at its deployment setting
[`scenarios.<scenario>.methods.<m>.at_b_star`]. *Mean TTC* counts a miss as 180 min.

| Scenario | Method | Detection | FA/month | Mean TTC | Fires overlapping haze | Other fires |
| --- | --- | --- | --- | --- | --- | --- |
| H-none | P2 (SCMR) | 88.9% | 0.76 | 75 min | — | 88.9% (5247/5902) |
| H-none | median + SCMR | 90.8% | 0.69 | 68 min | — | 90.8% (5359/5902) |
| H-none | evidence gate | 88.9% | 1.08 | 75 min | — | 88.9% (5248/5902) |
| H-mix-x0.3 | P2 (SCMR) | 80.0% | 0.42 | 91 min | 67.9% (36/53) | 80.2% (2317/2888) |
| H-mix-x0.3 | median + SCMR | 71.3% | 0.40 | 104 min | 54.7% (29/53) | 71.6% (2069/2888) |
| H-mix-x0.3 | evidence gate | 63.2% | 0.34 | 119 min | 45.3% (24/53) | 63.5% (1834/2888) |
| H-mix | P2 (SCMR) | 66.9% | 0.91 | 108 min | 49.8% (158/317) | 67.8% (3788/5585) |
| H-mix | median + SCMR | 53.3% | 1.15 | 127 min | 43.9% (139/317) | 53.8% (3005/5585) |
| H-mix | evidence gate | 52.9% | 1.01 | 128 min | 39.4% (125/317) | 53.7% (2998/5585) |
| H-mix-x3 | P2 (SCMR) | 35.3% | 1.90 | 145 min | 31.0% (140/451) | 36.1% (899/2490) |
| H-mix-x3 | median + SCMR | 21.5% | 2.72 | 163 min | 23.9% (108/451) | 21.0% (524/2490) |
| H-mix-x3 | evidence gate | 26.9% | 3.08 | 154 min | 28.4% (128/451) | 26.6% (662/2490) |

**Method differences** (per-seed detection, each method at its own setting; unadjusted, descriptive)
[`scenarios.<scenario>.method_differences`]:

| Scenario | Budget | P2-medSCMR − P2-gate | P2 − P2-medSCMR | P2 − P2-gate |
| --- | --- | --- | --- | --- |
| H-none | 1 a month | +1.8 (+1.3 to +2.4); p 2.1e-07 | -1.9 (-2.5 to -1.3); p 1.9e-07 | 0.0 (0.0 to 0.0); p 0.32 |
| H-none | 3 a month | +1.1 (+0.5 to +1.6); p 0.0013 | -1.0 (-1.5 to -0.4); p 0.0034 | +0.1 (-0.4 to +0.6); p 0.28 |
| H-none | 10 a month | -0.1 (-0.6 to +0.3); p 0.42 | +0.1 (-0.3 to +0.5); p 0.46 | 0.0 (-0.1 to 0.0); p 0.32 |
| H-mix-x0.3 | 1 a month | +7.8 (+0.9 to +14.4); p 0.031 | +8.9 (+2.8 to +15.3); p 0.1 | +16.7 (+14.8 to +18.7); p 7.6e-10 |
| H-mix-x0.3 | 3 a month | +5.7 (+3.1 to +9.0); p 8.9e-06 | -2.4 (-4.4 to -0.7); p 0.0012 | +3.3 (+2.0 to +5.0); p 1.4e-06 |
| H-mix-x0.3 | 10 a month | +2.3 (+1.2 to +3.5); p 0.00016 | -0.7 (-1.6 to +0.2); p 0.14 | +1.6 (+1.0 to +2.2); p 1.2e-05 |
| H-mix | 1 a month | +0.6 (-5.4 to +6.5); p 0.58 | +13.3 (+7.7 to +19.1); p 9.4e-05 | +13.9 (+12.2 to +15.7); p 5e-18 |
| H-mix | 3 a month | +9.0 (+6.0 to +12.1); p 1.2e-08 | -2.9 (-4.7 to -1.0); p 0.0034 | +6.1 (+4.3 to +8.1); p 4.2e-10 |
| H-mix | 10 a month | +4.4 (+3.2 to +5.6); p 2.2e-11 | -2.2 (-3.0 to -1.4); p 4.8e-06 | +2.2 (+1.6 to +2.8); p 8.4e-11 |
| H-mix-x3 | 1 a month | -5.3 (-11.4 to +0.8); p 0.43 | +13.6 (+7.0 to +20.4); p 0.00053 | +8.3 (+6.2 to +10.7); p 1.5e-08 |
| H-mix-x3 | 3 a month | +19.7 (+13.3 to +26.3); p 1.3e-06 | -5.5 (-10.2 to -0.7); p 0.042 | +14.3 (+11.0 to +17.6); p 6.4e-09 |
| H-mix-x3 | 10 a month | +15.8 (+11.1 to +21.0); p 9.1e-09 | -8.9 (-12.4 to -5.8); p 6.6e-07 | +6.9 (+4.6 to +9.6); p 4.7e-08 |

## 8. Reading (SIM)

**The registered reading (protocol §7).** For every method, family P is rejected with Δ > 0: regional haze costs
detection at 1 false incident a month. In the protocol's words, that is the claim "smoke sets the price of strict
budgets" (for these methods, in this simulator). The paper's claim and title are not changed here.

1. **Without haze, every method holds 1 a month and still detects 88.9%–90.8% of fires; with H-mix haze,
   52.9%–66.9%.** The price falls as the budget loosens: 7.0–15.0 points at 3 a month
   and 2.2–6.7 at 10 (deployment view). At 0.3 a month with haze, P2 and median + SCMR
   do not reach the budget, and the gate reaches it at low detection (13.7% at equal false alarms; §3).
2. **Without haze, the floor that noise, drift and nuisance leave is small.** The useful floors are
   0.00–0.07 a month at 70.7%–71.4% detection.
   With haze they are 0.85–1.42 a month at
   57.5%–61.6% detection. For P2 and the gate, 92.9% and 87.2% of those incidents start inside
   haze; for median + SCMR, 69.7%.
3. **Stricter node thresholds do not lower the useful floor.** With haze, every method's useful-floor setting is
   the same with or without the targets 0.03 and 0.05. The lowest raw floor
   barely moves for P2 (0.77 against 0.79 a month). For median + SCMR it falls
   (0.61 against 0.81), at lower detection
   (24.5% against 30.5%). Without haze the floors are near zero either
   way (§5). Over all seeds and both scenarios,
   no strict threshold reached the bisection cap.
4. **The price grows with the haze rate.** Detection at 1 a month falls monotonically from ×0 to ×3 for every method, in both views. For example P2 (deployment):
   88.6% → 80.0% → 63.1% → 35.3%.
   At ×3, H-mix's settings no longer hold the budget (1.9–3.08 false incidents a month). At ×0.3,
   the dose point inside the range of the real NW-India rates (context, not a fitted value), P2 detects
   80.0% at 1 a month, against 88.6% without haze.
5. **Between methods.**
   - Without haze, the three differ by at most 1.9 points at 1 a month.
   - With H-mix haze, P2 leads median + SCMR by 13.3 points and the gate by 13.9.
   - R3's confirmatory result (the gate above median + SCMR at 1 a month) is not repeated here: +0.6 points (-5.4 to +6.5), p 0.58
     (descriptive; different seeds and selection).
   - At 3 and 10 a month, median + SCMR leads the gate, as in R3.
6. **Haze also slows and hides fires.** At 1 a month with H-mix haze, P2 confirms 49.8% of the
   fires whose first 3 h overlap haze and 67.8% of the others. Its mean time to confirmation
   is 108 min, against 75 min without haze.
7. **Operating points near 1 a month still move between selection and test seeds,** even with 50 selection seeds.
   With haze, selection → test false incidents a month: P2 (SCMR) 0.88 → 0.91; median + SCMR 0.96 → 1.15; evidence gate 0.82 → 1.01. 2 of 3 settings exceed the budget on the test seeds.

**Limits:**

- Simulation only: one network geometry (100 nodes at 70 m), the legacy plume, MOX sensors and the M20b haze family.
- The haze rates of the dose points are assumptions.
- The price has not been measured on real data. The real networks' events are rarer and more even than H-mix's
  ([realdata.md](realdata.md)).
- The useful floor's 50% detection threshold is the registered choice.

## Figures

All from `r4_analysis.json` (`python -m prahari.research r4-figures`); the footers give the seeds.

- [r4_price.png](figures/r4_price.png) ([PDF](figures/r4_price.pdf)): Per method, the test-seed Pareto fronts without haze (dashed) and with H-mix haze (solid).
- [r4_dose.png](figures/r4_dose.png) ([PDF](figures/r4_dose.pdf)): Detection at 1 a month and the useful floor against the haze-episode rate (seeds 6001–6050).
- [r4_floors.png](figures/r4_floors.png) ([PDF](figures/r4_floors.pdf)): Useful floors without and with haze, split inside/outside haze, with seed-bootstrap intervals.
