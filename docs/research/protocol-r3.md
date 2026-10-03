# Research protocol R3 — median + SCMR against the evidence gate, head to head

**Status: DRAFT (3 Oct 2026), for the developer's review.** No R3 seed has been run. Once approved, this page is marked
REGISTERED in a commit that precedes every R3 result file (charter rule 1); any later change is a logged deviation in
`DECISIONS.md`.

**Configuration:** [`configs/research/r3.yaml`](../../configs/research/r3.yaml). **Code:** `python -m prahari.research
r3-run | r3-analyse | r3-figures` (`engine/prahari/research/analysis_r3.py`; the R2 runner, replay and methods are
reused unchanged: `operating_r2.py`, `runner_r2.py`, `edge2.py`, `gate.py`).

**Scope.** Simulation only. Every number R3 produces is labelled **SIM**.

**Why R3.** In R2 ([results-r2.md](results-r2.md)) the two strongest common-mode strategies pulled in opposite
directions on H-mix:

- median + SCMR (P2-medSCMR) gave the highest detection at B* = 10, with a floor above P2's;
- the evidence gate (P2-gate) gave the lowest floor, with detection slightly below P2's.

R2 compared each method only with P2, never with each other. R3 compares the two directly, on fresh seeds. R2's
results were used only to choose this question; no R3 seed has been seen, and no model, grid or scenario has changed.

## 1. Questions

1. **Detection.** At a false-alarm budget both methods can meet, which confirms more fires within 3 h?
2. **Floor.** Which has the lower false-alarm floor?
3. **Across haze types.** Does the ranking hold under synchronous, uneven-gain and narrow-patch haze?

## 2. Data-generating scenarios

R2's scenarios ([protocol-r2.md](protocol-r2.md) §2), copied unchanged into `r3.yaml`: the M20b haze with R2's
defaults and per-scenario overrides, on the golden base configuration.

| Scenario | Role | Haze | Seeds (fresh) |
| --- | --- | --- | --- |
| H-mix | primary (confirmatory) | M20b defaults | selection 3901–3920; test 4001–4100 |
| H-sync | secondary (descriptive) | release-1.0 M20 | test 4101–4150 |
| H-gain | secondary | σ_g = 0.4 | test 4151–4200 |
| H-patch | secondary | coverage always partial, U(0.2, 0.5) | test 4201–4250 |

H-mix with the Gaussian plume is not repeated: in R2 the plume scaled detection but left false alarms unchanged.

No R3 seed range overlaps any seed used by R1 (901–920, 1001–1100), R2 (1901–1920, 2001–2300) or the development
seeds (11–33); a unit test checks this.

## 3. Methods

The registered R2 definitions, with the same code, grids and fast two-knob replay:

| Id | Role | Common-mode handling | Knobs |
| --- | --- | --- | --- |
| P2-medSCMR | compared | median-referenced node input (R3 of protocol R1) plus SCMR (M31) | r × ρ, ρ ∈ {0 (off), 1.5, 2, 3, 4, 6, 10} |
| P2-gate | compared | main node layer, SCMR off, plus the R10 evidence gate | r × θ, θ ∈ {0.05, 0.1, 0.15, 0.2, 0.3, 0.5, off} |
| P2 | reference only | main node layer plus SCMR | r × ρ |

- r uses R1's target grid {0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 4.3, 6, 10}, with h replay-tuned per seed (M28).
- R10: the gate's p-level 0.01 and window 30 min, as in R2.
- P2 is evaluated for continuity with R1 and R2. It is not part of any confirmatory test.
- Not evaluated in R3: P2-med, P2-factor, Mei, Mei-med and AR. Only the `main` and `med` node layers run.

## 4. Validity rule (registered from the start)

R2's deviation R2-D1 is part of R3 from the start: a setting is **invalid** when, on any seed of the stage, one of its
false incidents lasts ≥ 24 h (first to last alarm). Only valid settings can be selected as a floor setting or an
operating point.

## 5. Selection (H-mix selection seeds, pooled)

- **Floor setting** (per method): the lowest false incidents per month; ties go to the higher detection, then to the
  first cell in grid order.
- **B\*:** the smallest of {1, 3, 10, 30} false incidents a month that **both** P2-medSCMR and P2-gate reach.
- **Operating point** at a budget B (per method): the highest detection among cells with false incidents ≤ B; ties go
  to the lower false incidents, then to the first cell.
- **Secondary budgets:** the operating points at every budget in {1, 3, 10, 30} that both methods reach.
- The selection (`r3_selection.json`) is committed **before any test seed runs**.

## 6. Endpoints and tests (H-mix test seeds 4001–4100)

All differences are **P2-medSCMR − P2-gate**, per seed.

- **H1 (primary), detection at B\*:** the per-seed share of fires confirmed within 3 h, each method at its own
  operating point.
- **H2, floor:** the per-seed false incidents per month, each method at its own floor setting.
- **Test:** paired, two-sided Wilcoxon signed-rank on the per-seed differences, with a paired seed-bootstrap 95%
  interval of the mean difference (10,000 resamples, bootstrap seed 20261003).
- **Multiplicity:** Holm across {H1, H2}, α = 0.05.
- If B* is undefined (no budget both methods reach), H1 is reported as not testable and Holm runs over H2 alone.

**Descriptive only:**

- the paired detection difference at every secondary budget;
- equal-false-alarm detection along each Pareto front (R8 on the knob surface) at 1, 3, 10 and 30 a month;
- AMOC curves (mean time to confirmation, a miss counting as 180 min);
- the inside/outside-haze split of each floor (E3) and detection for fires overlapping haze (E5), as in R2;
- every secondary scenario, in both the deployment view (H-mix's settings) and the equal-false-alarm view, with the
  same paired comparison;
- P2 as the reference.

Every comparison is reported, whatever its outcome. No model, grid, budget, rule or seed changes after the first R3
result file.

## 7. Compute and records

About 270 seed-runs with two node-layer variants each: roughly 4–5 hours on 4 processes, in resumable, supervised
blocks. Each seed file is written atomically and deterministically under `results/research/r3/<stage>/<scenario>/`,
with R2's per-setting records (false incidents, first-alarm minutes, latencies, `fi_longest_min`, haze episodes and
overlaps).

**Outputs:** `results/research/r3_{selection,test,analysis}.json`; figures `docs/research/figures/r3_*`;
`docs/research/results-r3.md`; rows in `docs/research/numbers.md`.

## 8. Implementation checks before registration (no protocol seed used)

- **Subset fidelity:** on development seed 11 (short configuration), evaluating only {P2, P2-medSCMR, P2-gate} gives
  the same cells as the full R2 evaluation (`engine/tests/unit/test_research_r3.py`).
- **R2 unchanged:** with the refactored code, the registered R2 default regenerates R2 test seed 2102 (H-sync) byte for
  byte, and the R2 figures regenerate byte for byte.
- **Configuration:** `r3.yaml`'s M20b defaults, scenarios, grids, budgets and cap equal `r2.yaml`'s, and its seeds are
  fresh (unit test).
- **Analysis:** the H1/H2 tests and Holm step are unit-tested on synthetic seed files.
