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

*Filled in when the sweep runs finish (`r1_sweeps.json`, figure f5).*

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
- A legacy-mode plume.
- A 100-node, 70 m grid.
- Median subtraction assumes that a fire affects well under half the nodes.

## Figures

- [f2 operating curves](figures/f2_operating_curves.png): false incidents against confirmed fires, every baseline, P2
  and P2-med.
- [f3 time to confirmation](figures/f3_time_to_confirm.png): at 10 a month.
- [f4 ablations](figures/f4_ablations.png): at 10 a month.
- f5 sensitivity: the sweeps (pending, added when the sweep runs finish).

PDF versions sit beside each PNG.
