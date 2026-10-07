# Research protocol R4 — the price of haze at strict false-alarm budgets

**Status: DRAFT (7 Oct 2026), for the developer's review.** No R4 code beyond R2/R3's exists yet, and no R4 seed has
been run. Once approved, the implementation checks of §9 run on development seeds only. This page is then marked
REGISTERED in a commit that precedes every R4 result file (charter rule 1).

**Why R4.** The audit of 7 Oct 2026 ([audit-2026-10-07.md](audit-2026-10-07.md) §4) found four things:

- **R1's floor came from a fixed value.** R1's "floor of about 5 false incidents a month" belongs to SCMR's fixed ratio
  ρ = 3. With ρ as a second knob, P2's floor is 0.22–1.28 a month across R2 and R3.
- **The remaining false alarms are still haze:** for P2, 83.5–100% start inside haze.
- **Strict budgets cost detection.** P2 confirms about 90% at 10 a month but 57–70% at 1 a month (R3).
- **That cost is attributed to haze only indirectly**, through R1's ten-seed, one-knob no-haze sweep: 90.1% at 1 a
  month.

R4 measures the cost directly. It runs the same seeds with and without haze, under the final methods. The earlier
results were used only to choose the question. All R4 numbers are **SIM**.

## 1. Questions

1. **The price of haze.** At 1 false incident a month, how much detection does regional haze cost each method?
2. **The floor without haze.** What false-alarm rate remains when there is no haze at all (noise, drift, nuisance),
   and how much does haze add?
3. **Node thresholds.** Do stricter node thresholds (target r below 0.1) lower the floor, or the useful floor?
4. **Dose–response.** How does the price grow with the haze rate (×0, ×0.3, ×1, ×3)?

## 2. Scenarios and the paired design

All scenarios use R2's golden base and the M20b haze with R2's H-mix parameters (`configs/research/r2.yaml`). Only the
episode rate changes, through `params.haze.crop_burning_multiplier`:

| Scenario | Haze rate | Role | Selection seeds | Test seeds |
| --- | --- | --- | --- | --- |
| H-none | ×0 (no episodes) | primary contrast | 5901–5950 | 6001–6100 |
| H-mix | ×1 (R2's H-mix) | primary contrast | 5901–5950 | 6001–6100 |
| H-mix×0.3 | ×0.3 | dose–response (descriptive) | — | 6001–6050 |
| H-mix×3 | ×3 | dose–response (descriptive) | — | 6001–6050 |

**Pairing.**

- The haze module draws only from its own `haze` random stream, which no other module reads.
- So a seed's fires, sensor noise, drift, nuisance events and day types are identical in every scenario; only the haze
  differs.
- The same seed numbers are therefore used in every scenario, and every comparison between scenarios is paired by
  seed. §9 checks this.

**Fresh seeds.** None of 5901–5950 or 6001–6100 has been used before: development 11–33; R1 901–920 and 1001–1100;
R2 1901–1920 and 2001–2300; R3 3901–3920 and 4001–4250.

**On the ×0.3 rate.** The point lies inside the range of the real NW-India rates (×0.05–×0.31 of H-mix, pooled per
cluster; [realdata.md](realdata.md) §5). It is a dose–response point, tagged `ASM`, not a parameter estimated from
those data. Those data validated M20b and are not used to set it (charter rule 7).

## 3. Methods

The registered R2 definitions and code (`operating_r2.py`, `edge2.py`, `gate.py`), with the method subset of R3:

| Id | Common-mode handling | Knobs |
| --- | --- | --- |
| P2 | main node layer and SCMR (M31) | r × ρ |
| P2-medSCMR | median-referenced node input and SCMR | r × ρ |
| P2-gate | main node layer, SCMR off, evidence gate (R10) | r × θ |

**Grids:**

- **Node target r:** {**0.03, 0.05**, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 4.3, 6, 10}. R2's grid plus two
  stricter values, for question 3.
- **ρ:** {0, 1.5, 2, 3, 4, 6, 10}, unchanged.
  - An interior cluster's ratio cannot exceed 100/9 ≈ 11.1 (64 of 100 nodes have 9-node neighbourhoods at R = 1.6 ×
    70 m; DER).
  - So ρ = 10 is already the strictest useful value. A larger ρ would hold every interior fire.
- **θ:** {0.05, 0.1, 0.15, 0.2, 0.3, 0.5, off}, unchanged. 0.05 is about 5 nodes, close to a fire's own footprint.
- **Gate settings and bisection cap:** as R2.
- **At r = 0.03:** the replay-tuning target is about 1.4 expected candidates across the network over the tuning days,
  so h is set by the extreme tail. The share of thresholds that reach the cap is reported per seed.

## 4. Validity rule

As R3 (registered from the start): a setting is invalid when, on any seed of the stage, one of its false incidents
lasts ≥ 24 h. Only valid settings can be selected.

## 5. Selection (per scenario, on its own selection seeds, pooled)

Each of H-none and H-mix is selected on its own runs of seeds 5901–5950. A network deployed in either condition would
be tuned for it.

- **Operating point at budget B:** the highest detection among valid cells with false incidents ≤ B; ties go to the
  lower false incidents, then to the first cell in grid order.
  - Budgets: {0.3, 1, 3, 10} a month.
  - If a budget is not reached in a scenario, that is recorded.
- **Floor setting:** the lowest false incidents; ties go to the higher detection, then to the first cell.
- **Useful-floor setting (new):** the lowest false incidents among valid cells whose pooled detection is at least 50%;
  ties go to the higher detection, then to the first cell. None if no cell reaches 50%.
- **Floors with r < 0.1 removed:** the floor and useful-floor settings are also selected with the cells r < 0.1 left
  out, for question 3.
- The H-mix×0.3 and H-mix×3 scenarios use the H-mix selection (deployment view).
- **The selection is committed before any test seed runs.**

## 6. Endpoints and tests (test seeds)

### Family P, the price of haze (confirmatory)

For each method m in {P2, P2-medSCMR, P2-gate}:

- **Δ_m:** per seed, detection at 1 a month in H-none minus detection at 1 a month in H-mix.
  - Detection is the share of that seed's fires confirmed within 3 h.
  - Each scenario is measured at its own selected operating point.
  - Seeds 6001–6100, paired.
- **Test:** two-sided Wilcoxon signed-rank on the 100 per-seed differences, with a paired seed-bootstrap 95% interval
  of the mean difference (10,000 resamples; bootstrap seed 20261007).
- **Multiplicity:** Holm across the three methods, α = 0.05.
- **If a method does not reach 1 a month** on either scenario's selection seeds, its Δ is reported as not computable
  and Holm runs over the others.

### Descriptive (no confirmatory claim)

1. **Δ_m at 0.3, 3 and 10 a month**, in both views:
   - deployment: each scenario's own operating point;
   - equal false alarms: R8 on each scenario's test-seed curve.
2. **Floors.** In each scenario, with seed-bootstrap intervals:
   - the floor, the useful floor, and both with r < 0.1 left out;
   - the inside/outside-haze split for H-mix. In H-none every incident is outside haze, so the H-none floor is the
     floor that noise, drift and nuisance set.
3. **Node thresholds (question 3):**
   - the floor and useful floor with and without the cells r < 0.1, with their detection;
   - the share of capped thresholds at r = 0.03 and 0.05.
4. **Dose–response:** detection at 1 and 3 a month and the floors, across ×0, ×0.3, ×1 and ×3 on seeds 6001–6050.
   This uses the deployment view (H-mix settings for ×0.3 and ×3, H-none's for ×0) and the equal-false-alarm view.
5. **Other measures, as in R2:**
   - fires whose first 3 h overlap haze (E5);
   - mean time to confirmation (AMOC);
   - the per-seed detection difference between methods within each scenario (the R3 comparison, now in both
     conditions).

Every comparison is reported, whatever its outcome. No model, grid, budget, rule or seed changes after the first R4
result file.

## 7. What each outcome would mean for the paper

| Family P outcome | Reading |
| --- | --- |
| Δ > 0, rejected for a method | For that method, regional haze costs detection at 1 a month. That is the claim "smoke sets the price of strict budgets" |
| Not rejected, with an interval near zero | At 1 a month, haze is not what limits that method. The limit lies elsewhere (noise, nuisance, the geometry); the H-none floor shows where |
| Rejected with Δ < 0 | Haze helps detection at 1 a month: unexpected. It would need explanation before any claim |

## 8. Compute and records

- **Size:** 100 selection runs (50 seeds × 2 scenarios) and 300 test runs.
- **Time:** about 5–6 hours on 4 processes, in resumable, supervised 2-hour blocks, each at the developer's go-ahead.
- **Seed files:** `results/research/r4/<stage>/<scenario>/seed<N>.json`, with R2's per-setting records.
- **Outputs:**
  - `results/research/r4_{selection,test,analysis}.json`;
  - figures `docs/research/figures/r4_*`;
  - `docs/research/results-r4.md`;
  - rows in `docs/research/numbers.md`.

## 9. Implementation checks before registration (development seeds only)

1. **Pairing.** On a development seed with a short configuration:
   - H-none and H-mix have the same fire list;
   - their sensor readings are byte-identical before H-mix's first haze episode.
2. **Unchanged registered path.** With R3's grids, the R4 runner reproduces R3's cells for the three methods on a
   development seed.
3. **Strict targets.** The tuning at r = 0.03 and 0.05 runs, and the share of capped thresholds is recorded.
4. **Analysis.** Selection per scenario, the useful floor, the paired family P with Holm, and the dose–response
   tables are unit-tested on synthetic seed files.
5. The full engine suite passes.
