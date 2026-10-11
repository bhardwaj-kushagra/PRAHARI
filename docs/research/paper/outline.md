# Paper outline (bullets for the authors; no numbers)

This outline holds no results. Every number comes from [evidence-map.md](evidence-map.md) (generated) and
[numbers.md](../numbers.md). It follows the IEEE skeleton of [paper-plan.md](../paper-plan.md) (Phase D), adapted to
[direction.md](../direction.md). The authors write the prose (charter rule 10).

The claim and the title are still open, so the outline has slots for either reading of contribution 2.
**Reading A** is the direction's wording. **Reading B** is the revised form the evidence map supports.

## 0. Title and abstract (written last)

- **Title:**
  - the direction's working titles, or a revision; the developer decides;
  - if Reading B is chosen, the title names the detection price of strict budgets, not an unmovable floor.
- **Abstract** (about 150–200 words, one item each):
  - the problem;
  - the method (pre-registered, equal false alarms);
  - the decomposition finding;
  - the strategy comparison;
  - the real-data check;
  - the limits;
  - the open testbed.

## 1. Introduction

- **Problem:**
  - early wildfire detection with low-cost ground gas sensors;
  - the gap left by satellites and cameras, with the motivation updated from current, cited sources (direction
    fix 6).
- **The operational limit is false alarms at the network level,** not node accuracy.
  - The field evidence: Thompson et al. 2026 (*Fire* 9:141), alerts from distant smoke.
- **Gap:**
  - studies report detection without a fixed network false-alarm rate;
  - the novelty must be verified against the literature before it is claimed (evidence map, "Claims to avoid").
- **Contributions** (the four in [direction.md](../direction.md), worded per the developer's decision on
  contribution 2):
  1. a pre-registered, equal-false-alarm evaluation on an open, deterministic testbed;
  2. the decomposition (Reading A or Reading B);
  3. common-mode strategies and where each breaks;
  4. real-data checks of the premises.

## 2. Related work (about 20–25 references, each read before citing)

- **Ground-sensor wildfire networks:** WSN fire detection; N5 field evaluations; low-cost MOX sensors in smoke.
- **SPC under autocorrelation:** residual charts, CUSUM, average-run-length design.
- **Conformal anomaly detection** and the conformal CUSUM; calibration under dependence (a stated limit).
- **Distributed detection with correlated noise;** k-of-n counting rules; Mei's sum of local CUSUMs; scan
  statistics (named, not run: a limit).
- **Common-mode rejection in sensor arrays:** median referencing, factor models.
- **Positioning:**
  - no component is new;
  - the contribution is the evidence and the decomposition.

## 3. System and signal model

- **Network:**
  - a grid of nodes with a fixed spacing and neighbourhood radius (T1, world rows);
  - fires and the plume model (legacy and Gaussian; the plume caveat is in contribution 1).
- **Sensor channel:**
  - drift, autocorrelated noise, heavy tails, the daytime noise factor (T1, M18–M19);
  - nuisance events (M20).
- **Regional haze:**
  - M20, synchronous;
  - M20b: moving, uneven, patchy and night-weighted (T1, M20b rows, with DATA/ASM/DER tags);
  - say which ranges came from public data and which are assumptions.
- **Provenance:**
  - every parameter carries a source tag;
  - T1 lists them, as inputs, not results.

## 4. Method under test (the decision chain)

- **Figure 1 (to draw; not generated):** the chain node layer → edge layer → confirmation.
  - Build it from [SPEC.md](../../SPEC.md), M24–M35.
- **Node layer:**
  - slow baseline (M24);
  - conformal p-values in time-of-day bins (M26);
  - CUSUM on −ln p, with a node target set by a budget (M28).
- **Edge layer:**
  - clustering within a window and radius (M30);
  - spatial common-mode rejection, SCMR (M31);
  - Fisher combination and the quorum (M32–M34). Label RAQ plainly as a prior-dependent quorum (direction fix 5);
  - graded escalation to confirmation (M35).
- **Common-mode strategies compared** (R2–R4 definitions):
  - SCMR ratio;
  - median subtraction;
  - median plus SCMR;
  - one-factor reference;
  - evidence gate;
  - Mei's network sum (raw, and on median-referenced evidence).
- **Knobs:**
  - two-stage pipelines have two knobs (node target and second-stage knob);
  - operating points are chosen on the Pareto front (direction fix 2).

## 5. Evaluation protocol

- **Pre-registration:**
  - each round's protocol commit precedes its result files;
  - fresh seeds per round;
  - selection seeds and test seeds are kept apart.
  - Cite the protocol pages and the [audit](../audit-2026-10-07.md) §1.
- **Equal false alarms:**
  - budgets in false incidents per network per month;
  - operating point = highest detection at or under the budget;
  - the floor, and the useful floor (R4).
- **Endpoints:**
  - detection within the confirmation window;
  - false incidents per month;
  - time to confirmation;
  - the inside/outside-haze split.
- **Statistics:**
  - per-seed paired differences;
  - seed-bootstrap intervals;
  - two-sided Wilcoxon;
  - Holm within each family.
- **The validity rule:** a setting is invalid if any seed has a false incident lasting 24 h or more (DECISIONS
  R2-D1). State why Mei's settings fail it.
- **The rounds in one table:** R1–R4, their questions, seeds and families. This is the "report everything" backbone
  of T2.

## 6. Results

### 6.1 The budgeted chain against classical detectors (contribution 1; SIM)

- **R1, family A:** the chain against a fixed threshold, v1 and the AR(1) chart, at the reachable budget.
- **The textbook ARL threshold misses its budget** by a wide margin.
- **Figure:** `f2_operating_curves`. **Table:** T2, R1 rows. Unreachable budgets are reported as an outcome.
- **Caveat:** absolute detection depends on the plume model.

### 6.2 Common-mode strategies and where each breaks (contribution 3; SIM)

- **Synchronous haze** (R1): median subtraction leads.
- **Uneven haze** (R2): median subtraction fails; median plus SCMR leads the valid methods at the selected budget.
- **The gate's low floor** comes at a near-silent setting (the floor estimand's weakness, [audit](../audit-2026-10-07.md)
  §4.3).
- **Head to head** (R3): the ranking of median plus SCMR and the gate changes with the budget.
- **R3's strict-budget result is not repeated in R4** (descriptive); with haze, P2 leads both at the strict budget.
- **Mei:** the network sum cannot hold a budget.
- **Figures:** `paper_strategies`, `r2_floor_H-mix`. **Table:** T2, R2 and R3 rows.

### 6.3 What limits false alarms: the decomposition (contribution 2; SIM, with the REAL premise)

- **(a) Node calibration meets its budget:** REAL quiet networks and the Delhi smoke season (T3; `paper_realdata` (a)).
- **(b) The floor, in either reading:**
  - R1's floor came from the fixed SCMR ratio; with the ratio free, it falls ([audit](../audit-2026-10-07.md) §4.1).
  - What remains starts inside haze (R1–R3 split).
  - **R4, family P, confirmatory:** the detection cost of haze at a strict budget.
  - The useful floors without and with haze.
  - With haze, stricter node targets leave every useful-floor setting unchanged.
  - The dose–response.
- **Figures:** `r4_price`, `r4_floors`, `r4_dose`. **Table:** T2, R4 rows.
- **Caveat:** the floors are conditional on geometry (SCMR's ratio ceiling).

### 6.4 Real-data checks (contribution 4; REAL)

- **Common-mode events:**
  - on the quiet N5 networks and in NW India they are rarer than the simulated H-mix rate (Stuttgart's urban PM is
    the exception);
  - where NW India events occur, they are mostly more even across stations than M20b's draws;
  - so, for crop-residue smoke, the simulated haze rate is a stress setting.
- **Near recorded fires,** a fire's own smoke looks common-mode at kilometre spacing (N5 WR).
- **Figure:** `paper_realdata` (b). **Table:** T3.
- **State what real data cannot show:** the floor's size (too few events; PM and CO, not MOX).

## 7. Limitations

- **Simulation-first:** no physical experiment, and no real MOX dataset.
  - The sensor channel's realism is assumed (the sim-to-real table was not done).
- **Which haze scenario is realistic for MOX networks is open.**
- **Grid bounds:**
  - floor and strict-budget settings at grid edges;
  - SCMR's ratio ceiling ([audit](../audit-2026-10-07.md) §4.2).
- **Selection noise at strict budgets** (audit §4.4).
- **The real data:**
  - spacing, cadence and pollutant differ from the simulated network;
  - small event counts;
  - licence notes (DL15; Aakash CC BY-NC-ND).
- **No scan-statistic baseline.**

## 8. Conclusion and the field programme

- **One line per contribution,** in the chosen reading.
- **What a field deployment must measure:**
  - MOX gain spread under smoke;
  - the haze event rate and evenness;
  - the false-alarm budget operators accept.

## 9. Acknowledgment, availability, disclosure

- **Code and data:** the repository branch, the release tag and the archived DOI (the developer's accounts).
- **Public datasets and their licences:** Thompson et al. 2026 (MIT); Sensor.Community (ODbL 1.0); Aakash
  (CC BY-NC-ND 4.0); Princeton CPCB (CC BY 4.0); CPCB via OpenAQ (credit CPCB and OpenAQ).
- **AI-assistance disclosure** (IEEE policy): simulator code, analyses, figures and outlines.
- **The prior poster** (IEEE IAS AM 2026), cited.

## Figures and tables (where each one goes)

| Item | File (figures in `docs/research/figures/`) | Section | Label |
| --- | --- | --- | --- |
| Fig. 1 | to draw (decision chain) | 4 | — |
| Fig. 2 | `f2_operating_curves` | 6.1 | SIM |
| Fig. 3 | `paper_strategies` | 6.2 | SIM |
| Fig. 4 | `r4_price` | 6.3 | SIM |
| Fig. 5 | `r4_floors` or `r4_dose` | 6.3 | SIM |
| Fig. 6 | `paper_realdata` | 6.3 (a), 6.4 | REAL |
| Table I | [T1](tables/T1_parameters.md) | 3 | inputs |
| Table II | [T2](tables/T2_main_results.md) | 5–6 | SIM |
| Table III | [T3](tables/T3_real_data.md) | 6.4 | REAL |

- **Spares** for a longer version: `r2_floor_H-mix`, `r2_scenarios`, `r3_scenarios`, `f3_time_to_confirm`,
  `f5_sensitivity`.
- **Page budget:** a six-page IEEE conference paper takes about six figures and tables in total, so choose between
  `r4_floors` and `r4_dose`.
