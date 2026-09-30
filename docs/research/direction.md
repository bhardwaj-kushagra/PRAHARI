# Research direction (governs the paper branch)

**Source.** The developer's document "PRAHARI Research Direction" (25 Sep 2026, `research_paper_direction.pdf`,
written with an AI assistant in a separate chat), plus the developer's decisions of 30 Sep 2026.

**Priority.** Where this page and older planning pages (`paper-plan.md` §1–11) conflict, this page wins.

## The direction in brief

**Keep the method, change the claim.** Keep the pre-registered, equal-false-alarm simulation study: simulation first,
a protocol fixed before any run, fresh seeds, equal-false-alarm comparisons, both outcomes reported. The paper's story
is **what limits false alarms**: regional smoke leaking past common-mode rejection sets a floor that node thresholds
cannot move. It is not "a detector that beats every baseline".

**Novelty.** No single component is new. Every PRAHARI component has close prior art:

- residual charts and CUSUM under autocorrelation;
- conformal anomaly detection and the conformal CUSUM;
- bootstrap control limits;
- correlated-noise distributed detection;
- k-of-n counting rules.

The contribution is the evidence. None of the ground-sensor wildfire studies reviewed reports detection at a fixed
*network* false-alarm rate, and a 2026 Canadian field evaluation (Thompson et al., *Fire* 9:141) hit the same problem:
alerts from smoke 300–500 km upwind.

**Working titles:**

- *The Common-Mode Floor: Regional Smoke, Not Sensor Noise, Limits False Alarms in Low-Cost Gas-Sensor Wildfire
  Networks*;
- *Budgeted False-Alarm Control for Wildfire Gas-Sensor Networks: A Pre-Registered Simulation Study*.

**Contributions to claim:**

1. A pre-registered, equal-false-alarm evaluation of ground gas-sensor wildfire detection, on an open, deterministic
   testbed.
2. A decomposition of the network false-alarm rate: node calibration meets the independence budget, while regional
   smoke sets a floor that node thresholds cannot move.
3. A comparison of common-mode strategies under synchronous and under moving, uneven haze, including where each one
   breaks.
4. A real-data check of common-mode events and of the node layer's quiet false-alarm rate.

## Ten fixes the direction asks for, and their status

| # | Fix | Status |
| --- | --- | --- |
| 1 | The primary budget (3 a month) is below P2's floor; report it as a registered outcome and test at 10 a month | Done in R1 (`DECISIONS.md` R2-8) |
| 2 | P2 has one knob for a two-stage detector; give two-stage pipelines two knobs and choose on the Pareto front | Round R2 |
| 3 | The haze model is kinder than reality (synchronous, 20% gain spread); add moving, uneven haze with ranges from real data | Round R2 |
| 4 | No network-level baseline; add Mei's sum of local CUSUMs (and a scan statistic if time allows) | Round R2 |
| 5 | Label RAQ plainly: with one p-value per candidate, Fisher's combination is a count and RAQ a prior-dependent quorum | R1 close-out (docs) |
| 6 | Update the motivation: FireSat, the XPRIZE result, the two 2026 N5 evaluations | The authors' introduction |
| 7 | Record the haze level per minute, so false incidents split into inside and outside haze reproducibly | R1 close-out (R2-10) |
| 8 | Commit the R1 outputs; tag or merge; archive a Zenodo DOI | Outputs committed; tag and DOI need the developer's accounts |
| 9 | Add real data | Public datasets (below) |
| 10 | No separate simulator paper yet (JOSS asks for six months of public history) | Adopted: one paper |

## Experiments

- **A. Close R1 as registered.**
  - Report the unreachable budgets as a finding.
  - Add the inside/outside-haze split as a logged, descriptive deviation.
  - Read the haze sweep (multiplier 0, 1, 3, 6) as the floor's dose–response.
- **B. Pre-register R2** on common-mode handling, with new seeds, and run it:
  - haze scenarios: synchronous, wider gain spread, advected fronts, spatial gradients;
  - methods: SCMR, median subtraction, an evidence-level gate, a median-plus-SCMR hybrid;
  - two-dimensional knobs for two-stage pipelines;
  - Mei's baseline;
  - AMOC curves, and fires that overlap haze reported separately.
- **C. Real data.** Public data only, catalogued and replayed as described below.

**Additions agreed on 30 Sep:**

- The false-alarm floor itself is a registered estimand in R2.
- Two more haze patterns: patchy swaths and night pooling.
- A one-factor, gain-weighted common-mode reference.
- Mei's baseline on raw and on median-referenced evidence.
- The budget rule {1, 3, 10, 30}, applied as "the smallest budget every compared method reaches on the selection
  seeds".
- Secondary scenarios on 50 test seeds each.

## Decisions of 30 Sep 2026 (developer)

- **Agreed:** the direction and the plan built on it, including the rule changes in this branch's `CLAUDE.md`.
- **Venue:** decided later. The work is not tied to a deadline yet.
- **No physical experimentation.** No own logging, burns or measurements.
- **Real data:** public datasets, used scientifically, in this order:
  1. Thompson et al. 2026 (N5 smoke sensors, Canada; MIT licence) for common-mode events and a node-layer replay;
  2. Chwalek et al. 2023 (BME680 units at a prescribed burn), for real gas-sensor background and smoke response;
  3. dense PM networks over NW India in the stubble season, and OpenAQ, if available.

## Integrity

- The authors write the prose, and AI use is disclosed in the acknowledgments.
- Every cited paper is read before citing, using the published version.
- The institution's similarity check runs before submission.
- Drafts and version history are kept.
