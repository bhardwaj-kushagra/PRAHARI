# Research protocol R1 — equal-false-alarm evaluation (pre-registered)

**Status:** written and committed **before** any run on the seeds below. Any later change is a deviation: it is
logged in `DECISIONS.md` (ids R2-n) with its reason, and the paper reports it.

**Scope:** simulation only. Physical experiments (quiet logging, burns, negative controls) belong to a separate,
later study; see [paper-plan.md](paper-plan.md).

Everything this protocol produces is simulation output (**SIM**).

## 1. Question

At the **same false-alarm rate**, does the PRAHARI chain (P2) detect more fires, sooner, than:

- the baselines;
- its own ablations?

And how much do its results depend on the simulator's assumed (ASM) parameters?

## 2. Fixed set-up

| Item | Value |
| --- | --- |
| Configuration | `configs/experiments/golden.yaml` composed over `configs/default.yaml`: legacy mode, 100 nodes on a 10 × 10 grid at 70 m. Release 1.0 models and parameters, unchanged |
| Protocol per seed (M46) | 14 d calibration, 14 d tuning, 30 d test. A quiet pass counts false incidents; a fire pass on the same seed adds the protocol fires (6-hour slots, kept with p 0.8 on dry days and 0.2 on wet days) |
| False incident | M46 merge rule: alarms within 60 min and 2R form one incident. Reported per month (30 d) for the 100-node network |
| Detection | an alarm within 150 m of the ignition, within 180 min |
| Selection seeds | 901–920, used only to choose operating points |
| Test seeds | 1001–1100, used for every reported number |
| Sweep seeds | 1001–1010 (the first ten test seeds) |
| Bootstrap | 10,000 resamples of seeds; generator from `SeedSequence(20260924)`, stream `research` |

None of these seeds was used during development. Development used 11–55, 31–50, 41–42, 51–53 and 101–160.

## 3. Pipelines and their knobs

Every pipeline is evaluated offline from one recording pass per seed. The recording keeps:

- the raw and compensated readings;
- each node-layer variant's CUSUM input, elevated-node share and p-values.

Offline replay reuses the release-1.0 functions: the M22 and M23 rules, `cusum_replay`, `tune_h`, `edge_alarms`,
`incidents` and `detect`.

**Fidelity requirement.** At the configured default knob, every offline pipeline must reproduce the online counts
exactly on a test run. This is a unit test, and no seed in §2 is run until it passes.

| Id | Pipeline | Knob (grid) |
| --- | --- | --- |
| P0 | Fixed threshold μ + kσ on the raw channel (M22) | k ∈ {3, 3.5, 4, 4.5, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30} |
| P1 | v1 as written: uncapped EWMA z, CUSUM k 0.5, quorum 2 (M23) | h ∈ {8.8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 400, 600, 800} |
| P1t | v1 on the capped slow z, h replay-tuned (M23, M24, M28), quorum 2 | target r |
| AR | P1t with the z replaced by its AR(1) innovation (R1, R2): the classical residual chart | target r |
| P2 | PRAHARI: TTC → QCC → CUSUM (M24–M28) → cluster, SCMR, Fisher, RAQ (M30–M34) | target r |
| P2−SCMR | P2 with the SCMR stub | target r |
| P2−Q2 | P2 with a fixed quorum of 2 (the RAQ stub) | target r |
| P2−Q3 | P2 with a fixed quorum of 3 | target r |
| P2−med | P2 without SCMR, with the node layer fed x − median over nodes (R3): classical common-mode subtraction | target r |
| P2−QCC | P2 with the legacy "minus conformal" node layer (P7-12) | target r |
| P2−TTC | P2 with the legacy "minus two-timescale" node layer (P7-12) | target r |

**Target grid.** r ∈ {0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 4.3, 6, 10} node-local false candidates per node per
30 d.

For target knobs, h is replay-tuned per seed on its own tuning days (M28) with the batched bisection. The bisection's
upper bound is raised from 400 to 5,000 (22 iterations), so strict targets are reachable. The default-cap path is used
only in the fidelity test.

### Research equations

- **R1 — AR(1) coefficient.** Per node, from the capped slow z on the calibration days (t ∈ [1440, 20160)):
  φ_i = Σ z_t z_{t−1} / Σ z_{t−1}².
- **R2 — standardised innovation.** u_t = (z_t − φ_i z_{t−1}) / σ_i, where σ_i is the standard deviation of the
  calibration innovations.
- **R3 — network-median reference.** x̃_i(t) = x_i(t) − median_j x_j(t).
- **R4 — operating point.** For budget B, the knob is the most permissive grid value whose pooled false incidents per
  month on the selection seeds are ≤ B. If no grid value reaches B, the pipeline "cannot reach B" and is reported as
  such.
- **R5 — seed bootstrap.** Resample the test seeds with replacement. Pooled detection is Σk / Σn; pooled false
  incidents are Σ count / Σ days × 30. The interval is the 2.5–97.5 percentiles.
- **R6 — paired comparison.** Per seed, Δ_s = detection share of P2 − detection share of X at each pipeline's own
  selected knob. Report:
  - the mean Δ with its paired-bootstrap interval;
  - Wilcoxon signed-rank, two-sided (SciPy default `zero_method="wilcox"`).
- **R7 — Holm step-down** within each family (§4).
- **R8 — partial AUC.** Detection against log₁₀(false incidents a month) over [0.5, 10], from the pooled test curve:
  - linear interpolation in log FA;
  - below a pipeline's lowest achieved FA, detection counts as 0 (not reachable);
  - above its highest, detection is held at the last value;
  - normalised to [0, 1].

## 4. Endpoints and hypotheses

**Budgets:** B ∈ {1, 3, 10} false incidents a month.

- **Primary endpoint:** detection within 3 h at B = 3, on the test seeds.
- **Secondary endpoints:**
  - detection at B = 1 and B = 10;
  - realised test false incidents at each selected knob (with R5 intervals and exact Poisson intervals);
  - median latency and time-to-confirmation curves (share detected by minute 0–180);
  - pAUC (R8).

**Family A (primary):** H1: P2 detects more than P0, P1, P1t and AR at B = 3. Four comparisons, Holm at α 0.05.

**Family B (ablations):** H2: P2 differs from P2−SCMR, P2−Q2, P2−Q3, P2−med, P2−QCC and P2−TTC at B = 3. Six
comparisons, Holm at α 0.05. The direction is reported as found.

**Descriptive (no tests):** the operating curves and every sweep in §5.

**Reporting.** Both outcomes are reported. If a baseline matches or beats P2, that is the finding. No model, parameter,
grid or budget is changed after the test seeds have been run.

## 5. Sensitivity sweeps (misspecification)

**Seeds:** 1001–1010. One parameter changes at a time, from the golden configuration.

**Pipelines:** all offline pipelines of the main node layer (P0, P1, P1t, AR, P2, P2−SCMR, P2−Q2, P2−Q3).

**Reported for each point:**

- (a) false incidents and detection at the knob selected for B = 3 on the default model (deployment view);
- (b) detection at 3 false incidents a month, interpolated from the point's own curve (equal-FA view).

| Sweep | Configuration key | Values (default in bold) |
| --- | --- | --- |
| Noise memory | `sensor.ar_phi` | 0.80, 0.90, **0.95**, 0.98 |
| Noise level | `sensor.sigma_e` | 0.025, **0.05**, 0.10 |
| Haze frequency | `haze.crop_burning_multiplier` | 0 (no haze), **1**, 3, 6 |
| Node-gain spread | `haze.gain_sd` | 0.1, **0.2**, 0.4 |
| Nuisance rate | `nuisance.rate_roadside_per_day` and `rate_other_per_day`, both scaled | ×0.5, **×1**, ×2, ×4 |
| Drift | `sensor.drift_step_sd` and `ageing_sd`, both scaled | **×1**, ×2, ×4 |
| Plume model | `modules.plume` | **stub (legacy M12)**, real (Gaussian M11) |
| Spacing | `world.spacing_m` | 50, **70**, 100, 150, 200 |
| Wrong prior | srp day types flipped with probability q (edge only, all test seeds) | **0**, 0.1, 0.2, 0.3 |

## 6. Outputs

- `results/research/`:
  - per-seed files (regenerable, not committed);
  - `r1_selection.json`, `r1_test.json` and `r1_sweeps.json` (committed): per-seed counts per knob, the selected
    knobs, and latencies at the selected knobs;
  - `r1_analysis.json`: every number the paper quotes.
- Figures: `docs/research/figures/`, built only from those files. Each footer states SIMULATION, the seeds and the
  simulated days.

## 7. Not in this round

- The learning curve (M36) with more test seeds. The existing `results/learning.json` (seeds 41–53) is quoted as
  development evidence only.
- A space-time scan-statistic baseline.
- Any field data.
