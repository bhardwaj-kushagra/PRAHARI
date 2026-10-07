# Research protocol R2 — results (SIM)

**Protocol:** [protocol-r2.md](protocol-r2.md), registered in `a24bfbd` before any R2 run. One deviation, DECISIONS
R2-D1, a validity rule decided before any test result was read. The selection results were committed before the test
stage (`72c1e2a`, `16f35ff`).

**Numbers:** every number here is **SIM** and comes from `results/research/r2_analysis.json` (keys in brackets), built
by `python -m prahari.research r2-analyse`. [numbers.md](numbers.md) maps each one to its key.

**Seeds:**
- H-mix: selection 1901–1920, test 2001–2100;
- H-sync, H-gain, H-patch, H-mix-gauss: 50 test seeds each (2101–2300).

**Set-up:** 100 nodes at 70 m, 30 test days per seed after 28 days of calibration and tuning.

**† Invalid settings.** A † marks a setting whose false alarms form an incident lasting ≥ 24 h on some seed
(continuous alarming; R2-D1). Its incident count and detection are not meaningful.

## 1. Budget and operating points (H-mix selection seeds)

**Registered rule:** B* = **10** false incidents a month [`b_star`]. That is the smallest pre-set budget
that P2 and the six family-D methods all reach.

**Under R2-D1:** B* is **undefined** [`b_star_R2_D1`]. Mei and Mei-med reach budgets only through settings that
alarm continuously. Their lowest valid floors are
176.2 and
206.4 false incidents a month.

## 2. The false-alarm floor (E1, E3; H-mix test seeds)

Each method's floor is measured at the setting chosen on the selection seeds, with the seed-bootstrap interval and its
split by whether the incident started inside or outside haze [`scenarios.H-mix.methods.<m>.floor_at_selected_knob`].

| Method | Setting | False incidents / month (95% CI) | Inside haze | Outside haze | Share inside |
| --- | --- | --- | --- | --- | --- |
| P2 | [0.1,10.0] | 0.56 (0.39–0.74) | 0.55 | 0.01 | 98.2% |
| P2-med | 0.1 | 4.22 (3.04–5.44) | 3.02 | 1.2 | 71.6% |
| P2-medSCMR | [0.1,10.0] | 0.89 (0.67–1.12) | 0.63 | 0.26 | 70.8% |
| P2-factor | 0.1 | 3.79 (2.70–4.97) | 2.83 | 0.96 | 74.7% |
| P2-gate | [0.2,0.05] | 0.16 (0.06–0.29) | 0.16 | 0.0 | 100.0% |
| Mei † | 20.0 | 6.49 (5.78–7.25) | 0.26 | 6.23 | 4.0% |
| Mei-med † | 100.0 | 1.40 (1.28–1.52) | 0.07 | 1.33 | 5.0% |
| AR | 0.2 | 6.43 (5.56–7.34) | 6.43 | 0.0 | 100.0% |

**Family F** (per-seed false incidents a month at the floor settings; method − P2; Wilcoxon with Holm)
[`scenarios.H-mix.families.F`]:

| Method | Difference (95% CI) | Holm p | Seeds lower / higher than P2 |
| --- | --- | --- | --- |
| P2-med | +3.66 (+2.51 to +4.88) | 1e-09 | 11 / 59 |
| P2-medSCMR | +0.33 (+0.10 to +0.57) | 0.0077 | 16 / 36 |
| P2-factor | +3.23 (+2.14 to +4.41) | 2.2e-08 | 15 / 52 |
| P2-gate | -0.40 (-0.61 to -0.19) | 0.00044 | 34 / 6 |

## 3. Detection at B* = 10 a month (E2, E5; H-mix test seeds)

| Method | Setting | Confirmed within 3 h (95% CI) | False incidents / month | Fires overlapping haze | Others |
| --- | --- | --- | --- | --- | --- |
| P2 | [4.3,6.0] | 90.5% (89.5%–91.5%) | 9.42 | 72.2% (234/324) | 91.6% (5136/5609) |
| P2-med | 0.75 | 62.5% (57.6%–67.2%) | 8.05 | 73.5% (238/324) | 61.9% (3469/5609) |
| P2-medSCMR | [6.0,6.0] | 92.2% (91.4%–93.1%) | 9.62 | 79.6% (258/324) | 93.0% (5215/5609) |
| P2-factor | 1.0 | 51.6% (46.2%–57.2%) | 9.53 | 65.7% (213/324) | 50.8% (2851/5609) |
| P2-gate | [3.0,0.5] | 89.1% (87.9%–90.2%) | 11.22 | 81.5% (264/324) | 89.5% (5022/5609) |
| Mei † | 20.0 | 100.0% (100.0%–100.0%) | 6.49 | 100.0% (324/324) | 100.0% (5609/5609) |
| Mei-med † | 100.0 | 100.0% (100.0%–100.0%) | 1.40 | 99.7% (323/324) | 100.0% (5609/5609) |
| AR | 2.0 | 59.0% (57.0%–61.0%) | 8.92 | 69.8% (226/324) | 58.4% (3277/5609) |

**Family D** (per-seed detection at B*; method − P2; Wilcoxon with Holm) [`scenarios.H-mix.families.D`]:

| Method | Difference, points (95% CI) | Holm p | Seeds better / worse than P2 |
| --- | --- | --- | --- |
| P2-med | -28.2 (-33.0 to -23.6) | 5.4e-17 | 6 / 94 |
| P2-medSCMR | +1.8 (+0.8 to +2.8) | 0.00026 | 58 / 22 |
| P2-factor | -38.9 (-44.3 to -33.5) | 3.4e-17 | 2 / 97 |
| P2-gate | -1.5 (-2.0 to -0.9) | 1.4e-05 | 17 / 58 |
| Mei † | +9.6 (+8.6 to +10.6) | 3.4e-17 | 99 / 0 |
| Mei-med † | +9.6 (+8.6 to +10.6) | 3.4e-17 | 99 / 0 |

## 4. Sensitivity analysis R2-D1 (valid settings only)

- **Floors:** family F is unchanged. Every family-F method's floor setting is valid
  [`scenarios.H-mix.sensitivity_R2_D1.families.F`].
- **Family D:** **cannot be computed**, because B* is undefined once Mei's continuously alarming settings are excluded
  [`…sensitivity_R2_D1.families.D`].
- **Mei and Mei-med:** they cannot operate at any pre-set budget (1, 3, 10 or 30 a month) without alarming
  continuously.

## 5. Every scenario: floor and detection at equal false alarms

The table gives each method's own floor (its lowest pooled false incidents a month on that scenario's seeds), then
its detection at 10 a month, interpolated along its Pareto front (R8 on the knob surface; `det_at_equal_fa.10`).

| Method | H-mix | H-sync | H-gain | H-patch | H-mix-gauss |
| --- | --- | --- | --- | --- | --- |
| P2 | 0.56 / 90.6% | 0.22 / 89.0% | 0.38 / 89.7% | 1.08 / 90.8% | 0.52 / 44.8% |
| P2-med | 4.22 / 77.3% | 0.88 / 93.2% | 5.26 / 69.5% | 2.52 / 90.5% | 4.16 / 21.3% |
| P2-medSCMR | 0.89 / 92.5% | 0.12 / 94.4% | 0.74 / 92.7% | 1.06 / 92.7% | 0.72 / 43.0% |
| P2-factor | 3.79 / 54.9% | 1.36 / 92.1% | 5.12 / 54.7% | 2.48 / 77.5% | 3.4 / 16.5% |
| P2-gate | 0.15 / 88.9% | 0.74 / 86.0% | 0.06 / 86.6% | 0.0 / 90.6% | 0.12 / 41.3% |
| Mei | 6.49 / 100.0% † | 10.82 / 0.0% † | 7.26 / 99.9% † | 3.6 / 100.0% † | 6.84 / 99.6% † |
| Mei-med | 1.4 / 100.0% † | 1.32 / 100.0% † | 1.34 / 100.0% † | 1.48 / 100.0% † | 1.42 / 99.8% † |
| AR | 6.22 / 63.0% | 6.78 / 55.0% | 6.2 / 61.9% | 3.52 / 70.9% | 6.16 / 20.9% |

Each cell reads floor / detection at 10 a month. The secondary scenarios are descriptive only (protocol §5).

**Deployment view** (the H-mix-selected setting applied unchanged; detection, false incidents a month)
[`scenarios.<sc>.methods.<m>.at_b_star`]:

| Method | H-sync | H-gain | H-patch | H-mix-gauss |
| --- | --- | --- | --- | --- |
| P2 | 88.8%, 8.00 | 89.1%, 9.24 | 90.4%, 8.58 | 43.5%, 7.50 |
| P2-med | 80.1%, 3.10 | 67.2%, 9.66 | 66.5%, 5.02 | 15.5%, 8.60 |
| P2-medSCMR | 94.3%, 8.22 | 92.6%, 9.56 | 93.3%, 11.96 | 42.9%, 9.52 |
| P2-factor | 75.6%, 4.30 | 56.2%, 10.38 | 58.7%, 6.02 | 13.1%, 8.64 |
| P2-gate | 85.6%, 9.74 | 86.8%, 11.00 | 87.2%, 8.34 | 40.8%, 9.54 |
| Mei | 100.0%, 10.82 † | 99.9%, 7.26 † | 100.0%, 3.60 † | 99.6%, 6.84 † |
| Mei-med | 100.0%, 1.36 † | 100.0%, 1.42 † | 99.9%, 1.52 † | 99.7%, 1.42 † |
| AR | 58.1%, 10.78 | 60.0%, 9.20 | 58.5%, 6.50 | 18.1%, 8.74 |

## 6. Reading (SIM)

**1. The floor is regional haze, under every haze model tested.** At its floor setting, P2's false incidents start
inside haze 98.2% of the time on H-mix
(90.9% on H-sync,
100.0% on H-patch). R1's §7 finding carries over to realistic,
uneven and patchy haze.

**2. Median subtraction does not survive realistic haze.**
- In R1 (synchronous haze) it was the best method.
- On H-mix its floor is 4.22 a month (P2:
  0.56), and it detects 62.5% at B*
  against P2's 90.5% (family D, Holm p 5.4e-17).
- On H-sync it does well: 93.2% at 10 a month. Synchronous,
  even haze flatters it, as the research direction expected.
- The one-factor gain reference behaves the same way: it detects 51.6% at B*.

**3. Median plus SCMR is the best valid method at B*.** It detects 92.2%,
+1.8 points over P2 (Holm p
0.00026). Its floor is slightly higher
(0.89 against 0.56).

**4. The evidence gate has the lowest floor.** It reaches 0.16 a
month (family F -0.40, Holm p 0.00044).
At B* it detects -1.5 points against P2.

**5. Mei's sum of local CUSUMs cannot hold a budget.**
- Its registered family-D "advantage" (+9.6 points) is an artifact of
  continuous alarming (R2-D1).
- Valid settings start at about 176 false incidents
  a month.
- Summing evidence across the network also sums the common mode.

**6. Detection is plume-conditional.** With the Gaussian plume, detection falls by half or more for every method (P2
43.5% at its H-mix setting, against 90.5% on H-mix). False alarms do not depend on the plume, because the quiet
pass has no fire.

**7. Added on 7 Oct 2026 (audit; descriptive).** R1's floor of about 5 a month belongs to SCMR's fixed ratio
ρ = 3. On these seeds, P2's lowest rate at ρ = 3 is 4.52 a month on H-sync and 5.47 on H-mix, against 0.22 and 0.56
at ρ = 10, at about the same detection at that setting (55.2–56.2% on H-sync). ρ = 10 is close to the ratio's ceiling
for an interior cluster (100/9 ≈ 11.1 with 9-node neighbourhoods, DER), so it means "confirm only while the rest of
the network is quiet". See [audit-2026-10-07.md](audit-2026-10-07.md) §4.1.

**Limits:**
- simulated MOX network at 70 m;
- one haze model family (M20b), with ranges from real data that is km-scale and PM-based (realdata.md);
- the secondary scenarios are descriptive;
- the R2-D1 rule was added after the selection stage (before any test result).

## Figures

- [Floor with the inside/outside-haze split, H-mix](figures/r2_floor_H-mix.png)
- [Pareto fronts: detection against false incidents](figures/r2_pareto_H-mix.png)
- [Mean time to confirmation](figures/r2_amoc_H-mix.png)
- [Floors in every scenario](figures/r2_scenarios.png)
