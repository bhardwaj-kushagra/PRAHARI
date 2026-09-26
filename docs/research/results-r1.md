# Research protocol R1 — results (SIM)

Every number on this page is **simulation output** from PRAHARI-SIM 1.0 under the pre-registered protocol
[protocol.md](protocol.md). The numbers come from `results/research/r1_analysis.json` (keys named in brackets), and
`r1_sweeps.json` for the sweeps.

**Test seeds:** 1001–1100, with 6,043 protocol fires and 30 simulated test days per seed, after 14 days of calibration
and 14 of tuning. Operating points were chosen on selection seeds 901–920 only.

**Intervals** are 95% seed-bootstrap intervals (10,000 resamples) unless marked otherwise.

## 1. The budgets that can be reached

The false-incident budgets were pre-registered at 1, 3 and 10 per month for the 100-node network. A budget counts as
reachable when a knob value keeps the selection seeds' false incidents at or below it (protocol R4).

| Pipeline | 1 / month | 3 / month | 10 / month | Lowest rate on the test seeds |
| --- | --- | --- | --- | --- |
| P0 fixed threshold | yes (21.1% detected) | yes (21.1%) | yes | 0.13 |
| P1 v1 as written | no | no | no | 9.36 |
| P1t v1 replay-tuned | no | no | yes | 6.77 |
| AR(1) residual chart | no | no | yes | 6.56 |
| **P2 PRAHARI** | **no** | **no** | yes | **5.07** |
| P2, median subtraction instead of SCMR (P2-med) | no | **yes (66.0%)** | yes | 0.95 |

[`test.<pipeline>.at_budget`, `test.<pipeline>.curve`]

**P2 cannot go below about 5 false incidents a month at any knob value**, so every pre-registered comparison at 1 and
3 a month is "not reachable" (protocol R4). This is a finding, not a failure of the run:

- The tuned thresholds are not at their search cap (median h 329 at the strictest target, none capped).
- The M28 tuning deliberately leaves common-mode minutes out of its count, so no node threshold is aimed at regional
  haze.
- Long haze episodes still raise node candidates, and SCMR holds back only part of them.
- Subtracting the network median before the node test removes most of that common mode: P2-med reaches 0.95 a month.

## 2. PRAHARI against the baselines at 10 false incidents a month

This is the pre-registered secondary budget, and family A of the tests.

| Pipeline | Knob | False incidents / month (bootstrap interval) | Confirmed within 3 h | Median latency |
| --- | --- | --- | --- | --- |
| **P2 PRAHARI** | r = 2 | 8.38 (7.5–9.3) | **83.3%** (80.1–86.1) | 53 min |
| P0 fixed threshold | k = 12 | 10.39 (7.6–13.5) | 46.2% (42.6–49.7) | 34 min |
| P1t v1 replay-tuned | r = 0.3 | 9.13 (7.8–10.6) | 31.7% (27.2–36.3) | 94 min |
| AR(1) residual chart | r = 1 | 7.75 (6.7–8.8) | 50.6% (48.4–52.9) | 39 min |
| P1 v1 as written | — | cannot reach 10 | — | — |

**Paired per-seed difference in detection share** (R6; Holm across family A) [`comparisons.10.A`]:

| P2 minus | Mean difference (interval) | Seeds P2 better / worse | Wilcoxon p | Holm p |
| --- | --- | --- | --- | --- |
| P0 | +36.8 points (+31.9 to +41.7) | 92 / 7 | 1.2e-15 | 1.2e-15 |
| P1t | +51.6 (+46.9 to +56.3) | 100 / 0 | 3.9e-18 | 1.2e-17 |
| AR | +32.6 (+29.0 to +35.9) | 95 / 5 | 3.1e-16 | 6.1e-16 |

**Time to confirmation** (figure f3):

- P0 and the AR chart confirm their first fires sooner, because single-node alarms need no agreement. Both level off
  below 51%.
- P2 overtakes them after about 45 minutes.

## 3. What each part of PRAHARI contributes at 10 a month

Family B of the tests [`comparisons.10.B`]:

| Variant | Confirmed within 3 h | False incidents / month | P2 minus variant | Holm p |
| --- | --- | --- | --- | --- |
| P2 without SCMR | 65.9% | 7.49 | +17.7 points (+14.6 to +21.3) | 2.3e-17 |
| P2, fixed quorum 2 (no RAQ) | 74.2% | 7.77 | +9.2 (+6.6 to +12.2) | 2.0e-12 |
| P2, Gaussian z (no QCC) | 69.6% | 9.98 | +13.8 (+12.1 to +15.5) | 3.0e-16 |
| P2, slow z (no TTC) | 44.2% | 9.10 | +39.1 (+32.8 to +45.4) | 2.8e-17 |
| P2, fixed quorum 3 | 86.2% | 9.21 | −3.1 (−5.5 to −1.0) | 0.28 (not significant) |
| **P2, median subtraction, no SCMR** | **92.1%** | 7.48 | **−8.8 (−11.7 to −6.2)** | 2.6e-12 |

**Reading the ablations:**

- **SCMR, QCC, TTC and the risk-adaptive quorum each add detection** at equal false alarms. The two-timescale
  residual (TTC) matters most.
- **A fixed quorum of 3 is statistically indistinguishable from RAQ** by the pre-registered test. Its bootstrap
  interval leans slightly in its favour, and the seed counts are nearly even (40 / 45).
- **Median subtraction beats SCMR.** Replacing SCMR by network-median referencing at the node input (P2-med) detects
  8.8 points more, and it is the only variant that reaches 3 a month.

**Partial AUC** over 0.5–10 false incidents a month (R8) [`test.<pipeline>.pauc`]:

- P2-med 0.60 (0.51–0.71);
- P0 0.30;
- P2-Q3 0.28;
- P2 0.18 (0.14–0.22), low because P2 detects nothing below 5 a month;
- AR 0.07;
- P1t 0.04;
- P1 0.01.

## 4. A wrong prior (RAQ)

The srp day types were flipped at random, and P2 was scored at its selected knob (r = 2) [`priors`]:

| Days mislabelled | 0% | 10% | 20% | 30% |
| --- | --- | --- | --- | --- |
| Confirmed within 3 h | 83.3% | 81.9% | 80.8% | 79.7% |
| False incidents / month | 8.38 | 8.45 | 8.71 | 8.82 |

The prior helps modestly, and a wrong prior degrades the result gradually: 3.6 points at 30% mislabelling.

## 5. Sensitivity sweeps

**Set-up:** ten seeds (1001–1010) per point, one assumption changed at a time from the golden configuration
[`r1_sweeps.json`, figure f5].

**Measure:** detection at 10 false incidents a month, interpolated from each point's own curve (R8 rule; 0 = the
budget cannot be reached). At the default point, P2 is at 84.5%, P2-med at 93.3% and the AR chart at 52.0% on these
ten seeds.

| Assumption (default) | Values | P2 | P2-med | AR(1) chart |
| --- | --- | --- | --- | --- |
| Noise memory φ (0.95) | 0.8 / 0.9 / 0.98 | 84.2 / 86.2 / 61.8 | 82.9 / 87.4 / 77.8 | 58.2 / 57.8 / 49.5 |
| Noise level σ (0.05) | 0.025 / 0.10 | 80.5 / 62.8 | 84.0 / 81.4 | 59.8 / 48.2 |
| Haze frequency (×1) | ×0 / ×3 / ×6 | 95.4 / **0** / **0** | 95.2 / 72.1 / 66.3 | 80.4 / 18.8 / 33.5 |
| Node-gain spread (0.2) | 0.1 / 0.4 | 84.4 / 81.5 | 94.8 / **65.8** | 53.2 / 53.4 |
| Nuisance rate (×1) | ×0.5 / ×2 / ×4 | 82.8 / 86.3 / 81.5 | 93.5 / 93.3 / 90.8 | 52.7 / 53.8 / 41.8 |
| Drift (×1) | ×2 / ×4 | 81.0 / 79.2 | 91.8 / 88.3 | 51.2 / 49.8 |
| Plume model (legacy M12) | Gaussian M11 | 35.9 | 39.8 | 17.6 |
| Spacing (70 m) | 50 / 100 / 150 m | 93.3 / 56.4 / 14.1 | 98.8 / 70.2 / 23.0 | 79.1 / 22.3 / 5.7 |

**What the sweeps show** (descriptive; ten seeds per point, so read the direction more than the decimals):

- **Haze frequency decides between the two common-mode defences.**
  - With three or six times the default haze (a crop-burning season), P2 can no longer reach 10 false incidents a
    month, while P2-med keeps 72% and 66%.
  - Without haze, all three PRAHARI-family variants are equal (about 95%).
- **Node-gain spread is median subtraction's weakness, as expected.** At a gain standard deviation of 0.4, P2-med
  falls to 65.8% and drops below P2 (81.5%). A shared median cannot cancel haze that each node sees at a different
  strength.
  - Together with the haze result, this is the paper's design lesson: the two methods fail in opposite conditions. A
    gain-normalised median, or median referencing plus SCMR, is the natural next step, evaluated under a new protocol.
- **Absolute detection depends strongly on the plume model and the spacing.**
  - Every pipeline loses about half its detection with the Gaussian plume.
  - Detection falls steeply beyond 70 m.

  The paper must present absolute detection as conditional on the modelled plume. The ranking of the pipelines holds
  in every row except the gain-spread and φ = 0.8 points.
- **Robust:** nuisance rate and drift change little. The AR chart stays 30–40 points below the PRAHARI variants
  throughout.
- **The textbook ARL threshold (P1 at h = 8.8)** gives 124–171 false incidents a month at every point
  [`fa_at_first_knob`]. The ARL formula's failure is not specific to φ = 0.95.

**Excluded point:** 200 m spacing. Ten nodes at 200 m do not fit the 1,400 m landscape, so siting fell back to a 70 m
grid; that is not a 200 m network. The reason is recorded in `r1_sweeps.json` (`excluded`) and DECISIONS R2-9.

## 6. What this supports, and what it does not

**Supported (SIM):**

- In this simulator, at equal false alarms, the budgeted chain beats a fixed threshold, v1 and a classical AR(1)
  residual chart by 33–52 points of detection.
- Every component except the quorum rule carries weight.
- Network-median referencing is a better common-mode defence than SCMR, and it opens the low-false-alarm budgets.

**Not supported:**

- Any field performance.
- PRAHARI as specified (P2) meeting 1 or 3 false incidents a month.
- Any claim that SCMR is the best common-mode method.

**Limits:**

- One simulator, with ASM-tagged background models; the sweeps test the main ones.
- Absolute detection depends on the plume model (about halved with the Gaussian plume) and on spacing.
- A legacy-mode plume.
- A 100-node, 70 m grid.
- Median subtraction assumes that a fire affects well under half the nodes.

## Figures

- [f2 operating curves](figures/f2_operating_curves.png): false incidents against confirmed fires, every baseline, P2
  and P2-med.
- [f3 time to confirmation](figures/f3_time_to_confirm.png): at 10 a month.
- [f4 ablations](figures/f4_ablations.png): at 10 a month.
- [f5 sensitivity](figures/f5_sensitivity.png): the sweeps (P2, P2-med and the AR chart).

PDF versions sit beside each PNG.
