# Research paper from PRAHARI-SIM — feasibility analysis and roadmap

## Context

Written 24 September 2026 in answer to the question of whether the simulator can support a conference paper. It covers five things:

- whether the simulator's results can support a paper at a local or regional conference;
- what is novel, and how to prove it;
- what to change technically;
- how to collect data and results;
- how to frame the paper.

**Inputs reviewed:**

- the three FIRENET–PRAHARI documents: the Milestone 1 record, the Technical Framework and the v2 second-pass audit;
- `docs/SPEC.md` §5;
- the committed results, read-only: `results/summary.json` and its golden, ablation, `seeds20`, `spacing`, `learning` and `energy` sections.

Release 1.0 is locked. Everything below is **additive**:

- no model, parameter, default or recording changes;
- `scripts/check_all.sh` must keep passing, with all 20 recordings byte-identical.

**Status:** analysis only. No experiment below has been run yet; they start when the developer gives the go-ahead.
Every number quoted here is simulation output (SIM) from the committed results files.

## 1. Verdict

**Yes, the simulator can support a paper**, framed as an honest simulation-based design study with an open, reproducible testbed. It becomes clearly stronger with one real-data element.

**It is not ready in its current form, for three reasons:**

- the headline comparisons mix operating points;
- the main table rests on 5 development seeds;
- the noise, haze and nuisance models are assumptions (tagged ASM) that the detector was designed around.

### How scientific it is today

| Aspect | Current state | Paper-ready? |
| --- | --- | --- |
| Reproducibility | Deterministic seeds, byte-identical recordings, locked environment, 222 engine tests | Yes: a strength |
| Provenance | Every parameter is tagged LIT, VEN, DER, ASM or TGT | Yes: a strength |
| Protocol | 14 d calibration, 14 d tuning, 30 d test; the test period is never used for tuning | Yes |
| Statistics | Wilson and exact Poisson intervals; 5 golden seeds, a 20-seed sweep and a fresh-seed check | Partly. Poisson intervals ignore overdispersion between seeds: P0 ranges from 112 to 410 false incidents a month per seed |
| Comparisons | Each pipeline at its own operating point | No: needs equal-false-alarm curves |
| External validity | All signals synthetic, with ASM noise, haze and nuisance models | No: needs sensitivity sweeps and real quiet data |
| Honesty record | Differences are documented: the report against the engine, and golden 5 of 21 | Yes, but the paper must use a single source of numbers |

## 2. What already holds (SIM, committed results)

**Supported now:**

- **P2 dominates the replay-tuned v1 baseline** (seeds 11–30, 1,185 fires): it has fewer false alarms *and* more detections at the same time.
  - P2: 6.25 false incidents a month (95% CI 5.2–7.4); 72.7% confirmed within 3 h.
  - P1t: 17.1 a month (15.3–19.0); 60.4%.
- **SCMR is a Pareto gain.** Without it: 9.4 a month (8.1–10.8) at 73.2% confirmed. That is 50% more false incidents for no detection gain.
- **QCC and TTC are Pareto gains** (5 seeds):
  - P2: 3.4 a month, 71.3%;
  - without QCC: 8.8 a month, 67.3%;
  - without TTC: 8.4 a month, 59.9%.
- **RAQ is a trade, not a free win.** A fixed quorum of 2 gives 9.8 a month and 79.4%, against 6.25 and 72.7% for RAQ. Whether the prior helps at equal false alarms is unknown until operating curves exist.
- **The textbook threshold fails under autocorrelation.** P1, using Siegmund's h ≈ 8.8, gives 136–142 false incidents a month. Replay tuning (P1t) reduces this to 14–17.
- **Node calibration:**
  - achieved exceedance is 1.10% against a nominal 1% (0.6–1.6% per seed);
  - there are 0.65 local false candidates per node per 30 d, against a target of 1;
  - seed 22's h hit the cap, which is noted.
- **Density** (3 seeds): 63%, 33% and 5% confirmed within 3 h at 70, 100 and 150 m.
- **Learning:** at 3 false incidents a month, detection rises from 49% with the bound to 68% with K = 10 labelled burns, and 71% at K = 100. The legacy quorum reaches 80%, but at 7.7 a month.

**Not usable as is:**

- "P0 341 against P2 3.4" as a headline: P0 detects 98%, so the operating points differ.
- The report numbers (6.4 a month, 83%, "45×") mixed with engine numbers.
- The 5-seed golden table as the main result.
- The satellite race, which is illustrative.

## 3. Novelty and how to prove it

**Defensible contribution.** A budgeted, two-tier statistical decision chain for low-power gas-sensor wildfire networks, in which every threshold is derived from an explicit false-alarm budget instead of being hand-tuned:

- at the node: conformal calibration and a replay-tuned CUSUM;
- at the edge: spatial common-mode rejection and a prior-adaptive quorum;
- plus a quantified account of what each part buys.

Each piece has prior art: conformal anomaly detection, CUSUM, Fisher's method, the Sellke–Bayarri–Berger bound, and scan statistics. The novelty is the assembly for this problem, the budget derivation and the evidence.

| Claim | Evidence needed | Status |
| --- | --- | --- |
| C1: P2 beats the best baseline at equal false alarms | False-alarm–detection curves for all pipelines, with the threshold chosen on separate seeds | To do (A1, A2) |
| C2: SCMR removes regional-smoke false alarms at no detection cost, more so as haze grows | Paired ablation over 100 seeds; dose–response over haze rate; break point under node-gain spread; comparison with median subtraction | Partly done (20 seeds) |
| C3: ARL-derived CUSUM thresholds fail under autocorrelation, and replay tuning fixes it | False alarms against the AR coefficient φ; φ measured on real logs | Partly done |
| C4: about 10–20 labelled burns lift detection at a fixed budget | Learning curve with more test seeds | Done (SIM); extend |
| C5: a spacing design limit near 70 m | Spacing sweep from 50 to 200 m, legacy and Gaussian plumes | Partly done |
| C6: an open, deterministic, provenance-tagged testbed | Repository plus an archived DOI | Done; archive it |

**Risk.** A simpler baseline might match P2 at equal false alarms. The paper then becomes "what actually matters": replay tuning and spatial confirmation carry the gain, and conformal calibration gives calibrated rates without a Gaussian assumption. Pre-registration keeps either outcome credible. No tuning is done to make a chart win (rule 10).

**Never claim:**

- "first" or "no one else has";
- "N× fewer false alarms" at unequal detection;
- field performance or real-world lead time;
- a conformal guarantee under autocorrelation;
- satellite lead times.

## 4. What reviewers will attack, and the fix

| Weakness | Fix |
| --- | --- |
| Circularity: detector and data share the same assumptions | Misspecification sweeps (A3); semi-synthetic runs on real backgrounds (B6); state it plainly |
| Unequal operating points | Equal-false-alarm curves; thresholds chosen on separate seeds (A1) |
| Few seeds, all used during development | Pre-registered fresh seeds: 901–920 for selection, 1001–1100 for test; paired tests |
| Overdispersed false-alarm counts | Seed-level bootstrap intervals (A4) |
| Report numbers differ from engine numbers | Use engine numbers only; cite the earlier poster |
| Simplified physics and a single channel | Gaussian-plume robustness check; limitations section |
| Obvious baselines missing | AR(1)-prewhitened CUSUM, network-median subtraction, fixed quorum 2 and 3; a scan statistic if time allows (A2) |
| RAQ's prior is correct by construction | Day types mislabelled at 10, 20 and 30% (A3) |
| No real data | V1 quiet logs; public datasets (B1, B5, B6) |

## 5. Work plan

### Step 0 — documents (first, once the go-ahead is given)

- `docs/research/protocol.md`: the pre-registration, committed before any fresh-seed run. It fixes:
  - the seeds, endpoints, budgets, comparisons, tests and sweep ranges;
  - that any deviation is logged in `DECISIONS.md`.
- `DECISIONS.md`: research-track rules (additive, lock preserved); matplotlib as an optional `[paper]` extra (rule 13).
- Journey page `docs/journey/research-1-paper-experiments.md`, plus a row in its README (rule 16).
- Commit and push.

### Phase A — simulation experiments (1.5–2 weeks; additive only)

**Layout.**

- New package `engine/prahari/research/`, run as `python -m prahari.research <cmd>`, so `cli.py` stays untouched.
- Pure functions; each file under 300 lines.
- Configs in `configs/research/`; results in `results/research/` (un-ignore it in `.gitignore`); figures in `docs/research/figures/`.

**A1. Operating curves** (`operating.py`)

- A recording observer, following the `ScoreRecorder` pattern in `engine/prahari/eval/offline.py`, keeps raw x, z and S for every tick.
- Offline threshold sweeps:
  - P0: k in μ + kσ (M22);
  - P1: h (M23);
  - P2: the node target via `tuned_h`, and the edge via `edge_alarms`.
- Outputs: false incidents a month, confirmed within 3 h, and time-to-confirmation curves.
- Reuse: `run_pass` and `protocol_config` (`eval/experiments.py`); `cusum_replay` and `tune_h` (`detect/prahari/tuning.py`); `incidents`, `detect`, `per_month` and `wilson` (`eval/stats.py`).
- **Fidelity test:** at the default knobs, the offline counts equal the online pipelines exactly.

**A2. Baselines** (`baselines.py`)

- AR(1)-prewhitened CUSUM: φ fitted on the calibration days, h replay-tuned.
- Network-median subtraction before the node test.
- Fixed quorum of 2, and of 3.
- Optional: a prospective space–time scan statistic.

**A3. Sweeps** (`sweeps.py`) — configuration overrides only:

| Parameter | Range |
| --- | --- |
| AR φ | 0.5–0.98 |
| Noise σ | ×0.5–2 |
| Haze | rate 0–1 per day, and amplitude |
| Node-gain standard deviation | 0.1–0.4 |
| Nuisance rate | ×0.5–4 |
| Drift | ×0.5–2 |
| Plume model | legacy or Gaussian |
| Spacing | 50–200 m |
| Day-type mislabelling | 0–30% |

It also produces a tornado chart of the primary endpoint across the ASM parameters.

**A4. Statistics** (`pstats.py`)

- seed bootstrap;
- Wilcoxon signed-rank test on per-seed differences;
- Holm correction;
- rate ratios;
- partial AUC over 0.5–10 false incidents a month.

**A5. Figures** (`figures.py`)

- Built from results JSON only.
- Footers show SIM, the seeds and the simulated days (rule 15).

**A6. Runs**

1. Time one seed first.
2. Run the selection seeds 901–920.
3. Run the test seeds 1001–1100: several hours on 4 cores, in the background.

### Phase B — real data (starts now, in parallel; 3–5 weeks of calendar time)

**B1. V1 quiet logging**

- Set-up:
  - at least 5 nodes (8–10 is better), 30–100 m apart, with one co-located pair;
  - once a minute: raw resistance or ADC, heater voltage, T, RH, supply voltage, UTC time and node id.
- Duration: at least 28 days. Drop the first 48 h (MQ preheat) and keep an event diary.
- **Start now:** the October–November crop-residue burning season brings real regional haze, a natural test of SCMR.

**B2. V8 power:** measure each mode with a USB power meter (MQ-2 now). This gives a MEASURED row in the energy table.

**B3. V5 negative controls:** incense, a cooking stove and vehicle exhaust at 2–10 m.

**B4. V3 controlled burns** (only with permission and safety cover): 5 repeats at 5, 10, 25 and 50 m downwind. This gives:

- signal against distance for the plume and sensor models;
- a real labelled set for the learning curve.

**B5. Public data** — verify access, licence and resolution before use:

| Dataset | What it offers |
| --- | --- |
| UCI Air Quality (De Vito) | Hourly MOX readings, one site |
| UCI gas sensors for home activity monitoring | MOX plus T and RH, continuous |
| Kaggle smoke-detection IoT dataset | SGP30 raw readings, labelled |
| PurpleAir or Sensor.Community PM2.5 clusters during smoke episodes | The spatial structure of regional smoke (a different channel) |
| CPCB or SAFAR AQI; NASA FIRMS | Ground truth for haze days and fires |

**B6. Semi-synthetic runs** (`semisynth.py` plus a CSV loader)

- Method: inject simulated plumes into real backgrounds and run the same node and edge stages.
- Outputs:
  - a sim-to-real table comparing measured φ, tails, daily cycle and cross-node correlation with the ASM values;
  - achieved exceedance on held-out real quiet data;
  - real false candidates per node-month;
  - the V11 replay of v1 against v2.

### Phase C — figures and tables

**Figures:**

- F1: the decision-chain diagram.
- F2: false-alarm–detection curves on a log x-axis, with budget lines.
- F3: time-to-confirmation curves at 3 a month.
- F4: robustness, with a φ panel and the SCMR haze dose–response.
- F5: spacing.
- F6: the learning curve.

**Tables:**

- T1: parameters with their provenance tags and measured values.
- T2: main results at equal false alarms, with paired intervals.
- T3: ablations.

### Phase D — writing (the authors) and submission

**Title options:**

- "Budgeted False-Alarm Control for Gas-Sensor Wildfire Networks: A Reproducible Simulation Study"
- "How Many Nodes Must Agree? Spatial Common-Mode Rejection and Risk-Adaptive Quorum for Wildfire Gas-Sensor Networks"

**Structure** (6-page IEEE format, about 20–25 references):

1. Introduction: the gap left by satellites and cameras; false alarms as the operational limit; 3–4 contributions.
2. Related work: WSN fire detection; SPC under autocorrelation; conformal anomaly detection; scan statistics; evidence calibration.
3. System and signal model, with provenance.
4. Method: node layer, edge layer and the budget derivation.
5. Protocol.
6. Results.
7. Limitations.
8. Conclusion and the field programme.
9. Acknowledgment, including the AI disclosure.

**Venue:** an IEEE-sponsored regional conference with IoT, sensor or disaster tracks, published in IEEE Xplore. Candidates to check: INDICON, UPCON, CONECCT, TENCON, SPICES, IEEE SAS. Verify dates on IEEE's conference listing to avoid fake "IEEE" events.

## 6. Integrity

- **The authors write the text.** I supply results, figures, bullet outlines, a number-to-source table, and reviews of their drafts.
- **Do not paste from the repository docs, the poster or the reports.** A public repository is indexed, so pasted text will match.
- **Similarity check:** IEEE checks with CrossCheck (iThenticate). Quote sparingly, cite everything, and run a similarity check before submission.
- **AI disclosure:** disclose AI assistance in the acknowledgments, as IEEE policy requires. This covers text, figures and code; the simulator itself was built with AI coding assistance.
- **Prior poster:** cite the IEEE IAS AM 2026 poster and abstract. The paper adds substantial new work. Check both venues' prior-publication rules.
- **References:** open and read every reference before citing it. No unchecked suggested references.

## 7. Timeline (from 24 September 2026)

| Week | Work |
| --- | --- |
| 1 | Approve; protocol; start V1 logging; V8; A1 |
| 2 | A2 and A4; runs on the selection and test seeds |
| 3 | A3 sweeps; A5 figures; literature table; V1 reaches 14 days |
| 4 | B6 semi-synthetic runs; V5; the authors' first draft |
| 5–6 | V1 passes 28 days, including the haze season; real-data results; revision; similarity check; submission |

A simulation-only version is possible in about 3 weeks.

## 8. Verification

- **The lock holds:**
  - `scripts/check_all.sh` passes;
  - all 20 recordings are byte-identical;
  - the existing results files are unchanged.
- **Fidelity:** offline replay at the default knobs equals the online counts (unit test).
- **Unit tests:** every new function has tests with reference values (bootstrap, Wilcoxon wrapper, AR fit, sweep overrides).
- **Determinism:** research runs regenerate byte-identical JSON, and `--jobs 1` equals `--jobs 4`.
- **Traceability:** every number in the paper maps to a results file and key, in a number-to-source table.

## 9. Defaults unless the developer says otherwise

Open decisions: the venue and its deadline, how many nodes can log quiet data, and which sensor.

| Setting | Default |
| --- | --- |
| Primary endpoint | Confirmed within 3 h at 3 false incidents a month (100 nodes, 70 m) |
| Secondary endpoints | The same, at 1 and at 10 a month |
| Seeds | Selection 901–920; test 1001–1100 |
| Figures | matplotlib as an optional extra |
| Venue and deadline | Chosen by the developer. If the deadline is under 4 weeks away, the scope is simulation-only, with real data as a pilot |

## 10. One paper or two? (added after the go-ahead)

The developer chose a **simulation-only** paper for now. Physical experiments become a separate study.

**Recommendation: the simulator can be a second paper, but only with a distinct contribution.**

| | Paper A: method (this one) | Paper B: the simulator as a tool |
| --- | --- | --- |
| Question | Does budgeted, derived-threshold detection beat the alternatives at equal false alarms, and why? | Can wildfire sensor-network detection be evaluated reproducibly, with every assumption visible and every component swappable? |
| Evidence | Operating curves, paired statistics, ablations, sensitivity sweeps (protocol R1) | Architecture (stub/real/off registry, isolation and degradation), determinism, provenance tags, agreement with an independent reference implementation, performance, the replay dashboard |
| Venue type | Regional IEEE conference, sensors/IoT track | Tool or demo track, or a software journal |
| Overlap rule | Owns the detection results | Cites Paper A for results; its own claims concern the tool |

**Order:**

1. Write Paper A first.
2. Paper B follows once Paper A is submitted, and reuses no results table.
3. Physical experiments become Paper C.

Keeping everything in one paper is also acceptable. The simulator then appears as a contribution bullet and a
reproducibility section, which is what Paper A does in any case.

## 11. What protocol R1 found, and how it changes the paper (added after the test seeds)

The results are in [results-r1.md](results-r1.md): SIM, 100 fresh test seeds, operating points chosen on separate
seeds. Sections 2–3 above were written before these runs. Where they differ, this section is the current evidence.

**Claims now supported:**

| Claim | Evidence |
| --- | --- |
| C1 | At 10 false incidents a month, the budgeted chain (P2) confirms 83.3% of fires within 3 h. That is +33 to +52 points over a fixed threshold, an AR(1) residual chart and replay-tuned v1 (Holm p ≤ 1.2e-15) |
| C2 (revised) | Common-mode rejection matters, but the better tool is **network-median referencing at the node input**, not SCMR. P2-med detects 92.1% at 10 a month (+8.8 points over P2), and it is the only variant that reaches 3 a month (66.0%) |
| C3 | The textbook ARL threshold fails. P1 cannot get below 9.4 false incidents a month at any h in its grid, and has the lowest pAUC (0.01) |
| C4 | Components: TTC (+39.1 points), SCMR (+17.7), QCC (+13.8) and RAQ against a fixed quorum of 2 (+9.2) each add detection. RAQ is not better than a fixed quorum of 3 |
| C5 | A wrong prior degrades gracefully: 30% of days mislabelled costs 3.6 points |

**Claims to drop or soften:**

- "PRAHARI meets one false confirmation per network per month." P2 does not, in this simulator; its floor is about
  5 a month.
- "SCMR is the right common-mode defence."
- "RAQ beats any fixed quorum."

**Suggested framing:** "Budgeted, derived thresholds with network common-mode referencing". Possible titles:

- "Budgeted false-alarm control for gas-sensor wildfire networks: an equal-false-alarm simulation study";
- "What makes ground-sensor wildfire detection work at a fixed false-alarm budget?"

The honest story has three parts:

1. The two-timescale residual plus replay tuning and spatial confirmation beat the classical detectors by a wide
   margin.
2. The spatial rule we designed (SCMR) is outperformed by the simpler median reference.
3. The prior-adaptive quorum is no better than choosing 3.

Reviewers tend to trust a paper that reports its own design losing an ablation.

**What the sweeps added** ([results-r1.md](results-r1.md) §5):

- Median subtraction wins under frequent haze: P2 cannot reach 10 a month at ×3 haze, while P2-med keeps 72%.
- It loses under large node-gain spread: 65.8% against P2's 81.5% at a standard deviation of 0.4.
- So the two common-mode defences fail in opposite conditions. That is a clean, novel design lesson for the paper, and
  it motivates a combined or gain-normalised reference as future work.
- Absolute detection roughly halves with the Gaussian plume. Report detection as conditional on the plume model; the
  rankings are the robust result.

The learning-curve extension (M36) stays out of this paper, as the protocol states.
