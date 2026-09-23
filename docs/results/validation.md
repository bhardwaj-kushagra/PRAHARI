# Results and validation

All numbers below are **simulation output (SIM)** from the files named, as of Phase 7. They change only when the
engine or configuration changes; regenerate them with the commands at the end.

## 1. Golden reproduction (legacy mode)

Configuration `configs/experiments/golden.yaml` and `ablation.yaml`: 100 nodes at 70 m, seeds 11, 22, 33, 44, 55, the
M46 protocol (14 calibration + 14 tuning + 30 test days per seed), legacy signal, source and plume models, and the
report simulation's fire injection (a constant random wind per fire, `DECISIONS.md` P7-1). Source:
`results/summary.json` (`table`).

| Pipeline | False incidents / month (95% CI, M45) | Report (SPEC §9.3) | Confirmed within 3 h (M44) | Report |
| --- | --- | --- | --- | --- |
| P0 fixed threshold | 340.6 (324.6–357.2) | 291 (277–307) — outside | 317/324 = 97.8% | 95% (93–97) — just above |
| P1 v1 as written | 136.2 (126.2–146.8) | 132 (123–143) — **inside** | 318/324 = 98.1% | 99% (98–100) — **inside** |
| P1t v1 replay-tuned | 14.4 (11.3–18.1) | 18.6 (15.0–22.8) — just outside | 198/324 = 61.1% | 59% (53–64) — **inside** |
| P2 PRAHARI | 3.4 (2.0–5.4) | 6.4 (4.4–9.0) — below | 231/324 = 71.3% | 83% (79–87) — below |
| P2 minus QCC (legacy form) | 8.8 (6.4–11.8) | 17.4 (13.9–21.5) | 218/324 = 67.3% | 78% |
| P2 minus TTC (legacy form) | 8.4 (6.1–11.4) | 11.8 (9.0–15.2) | 194/324 = 59.9% | 66% |
| P2 minus SCMR | 5.0 (3.2–7.4) | 12.0 (9.2–15.4) | 232/324 = 71.6% | 84% |
| P2 minus RAQ | 5.4 (3.6–7.9) | 10.0 (7.4–13.2) | 250/324 = 77.2% | 88% |

Per-seed false incidents per month: P0 299, 321, 388, 308, 387; P1 139, 145, 117, 140, 140; P1t 14, 12, 16, 19, 11;
P2 5, 5, 2, 0, 5. Median minutes from ignition to confirmation: P2 62, P2-QCC 42, P2-TTC 74, P2-SCMR 62, P2-RAQ 59.5.

**What holds and what does not.** The report's qualitative result holds: P2 has about 100× fewer false incidents
than P0, and removing any mechanism raises them. The absolute P2-family numbers do not match the 5-seed report
values: false alarms are lower on these five seeds (over 20 seeds they agree, section 2), and detection is lower
(section 2 traces why). The QCC and TTC rows use the report simulation's own ablation forms (`ablation_form: legacy`,
`DECISIONS.md` P7-12); as module stubs they gave 30.8 and 8.2 false incidents per month with 74.7% and 72.2% confirmed
(P7-9). Over seeds 11–30 the legacy ablations' false incidents match the report simulation's (P2 minus QCC 10.25 vs
12.40, Welch p 0.48; P2 minus TTC 12.75 vs 11.20, p 0.44).

## 2. Why some 5-seed results miss — and why that is not a code error

**Step 1 — same code.** The engine's P0, P1 and P1t, every node-layer function and the legacy edge decision give
identical outputs to the report's own simulation (`reference/prahari_simulation.py`) when fed identical inputs (unit
tests in `engine/tests/unit/test_eval_phase4.py`, `test_node_phase5.py` and `test_edge_phase6.py`).

**Step 2 — the spread is large.** False alarms come in bursts, so seed-to-seed variation is far wider than a Poisson
interval on the pooled count assumes. Even the oracle's own P0 over seeds 11–30 has a standard deviation of about 50
incidents per month.

**Step 3 — same distribution.** Engine and oracle over the same 20 seeds (quiet pass; per-seed values in
`engine/tests/golden/equivalence_seeds11_30.json` and `equivalence_p1t_seeds11_30.json`):

| Pipeline | Oracle mean (SE) | Engine mean (SE) | Welch p | Mann–Whitney p |
| --- | --- | --- | --- | --- |
| P0 | 321.9 (11.1) | 310.9 (15.9) | 0.58 | 0.71 |
| P1 | 139.1 (2.5) | 141.8 (2.1) | 0.40 | 0.44 |
| P1t | 18.3 (1.6) | 17.1 (1.5) | 0.58 | 0.66 |

No difference is detectable. The report's 5-seed P0 (291) is itself a low draw from its simulation's distribution.

**PRAHARI pipelines (Phase 7)**, seeds 11–30, both passes, with per-fire wind
(`engine/tests/golden/equivalence_p7_seeds11_30.json`; per-seed means, Welch and Mann–Whitney p-values):

| Pipeline | False incidents: report simulation | Engine | Welch p | Confirmed: report simulation | Engine | Welch p | Mann–Whitney p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | 321.9 | 310.9 | 0.58 | 98.8% | 97.1% | 0.053 | 0.11 |
| P1 | 139.1 | 141.8 | 0.40 | 99.7% | 99.6% | 0.64 | 0.47 |
| P1t | 18.3 | 17.1 | 0.59 | 61.6% | 60.0% | 0.51 | 0.75 |
| P2 | 7.20 | 6.25 | 0.48 | 82.2% | 72.8% | 0.015 | 0.002 |
| P2 minus SCMR | 10.05 | 9.40 | 0.71 | 82.4% | 73.3% | 0.017 | 0.002 |
| P2 minus RAQ | 10.15 | 9.80 | 0.86 | 86.1% | 79.6% | 0.088 | 0.012 |

False alarms agree everywhere; detection agrees for the baselines and is lower for the pipelines that use the
conformal node layer. What we established:

- **Same code.** Our node and edge stages give the report simulation's exact result on its own signals (seed 11:
  tuned h 238.13, 54 of 63 fires).
- **Same fires.** With per-fire wind the fire term is the same model; a direct check on seed 11 finds the same
  footprint — on average a fire lifts 8.24 / 5.19 / 2.92 nodes by ≥ 0.5 / 1 / 2 su in the engine and 8.17 / 5.10 /
  3.02 in the report simulation. Per-fire wind lowered golden P2 detection slightly (246 → 231 of 324), so the Phase 6
  wind explanation was withdrawn.
- **Different calibration tails.** On seed 11 the engine's quiet fast residual exceeds 1 su in 2.2% of calibration
  minutes against 0.29% in the report simulation; with haze switched off the engine's share drops to 0.18%. Haze in
  the calibration window widens each node's conformal reference set, so a fire's lift earns a less extreme p-value
  and fewer neighbours confirm within 30 minutes. The haze model is the same; the engine's seeds 11–30 drew 66
  episodes in days 0–27 (56 expected) against the report simulation's 45.
- **Independent seeds.** On fresh seeds 31–50 false incidents are identical for P2 (7.05 vs 7.05 per month) and
  P2 detection is 79.4% against 84.4% (Welch p 0.16, Mann–Whitney p 0.29). Over all 40 seeds the PRAHARI pipelines
  detect about 7 points less (P2 76.1% vs 83.3%, Welch p 0.007) while P0 and P1t agree. Part of the Phase 6 gap was
  therefore sampling.
- **Reverse swap (2 × 2).** Every combination of background and fire set, seeds 11–30, through the same engine chain
  (`reverse_swap` in the evidence file; the two anchor cells reproduce 862/1185 and 1000/1228 exactly):

  | Confirmed within 3 h | Engine fires | Report-simulation fires |
  | --- | --- | --- |
  | Engine background | 72.7% | 77.4% |
  | Report-simulation background | 81.1% | 81.4% |

  The engine backgrounds cost 4.6–7.4 points and the engine fire sets 2.0–4.8 points.
- **No model difference behind either.** The haze process agrees over 200 independent histories each (episodes 5.76 vs
  5.68, durations 449 vs 453 min, amplitudes 1.64 vs 1.64 su; all KS p > 0.6). The fire sets agree in geometry and
  timing; the report simulation's seeds drew fewer wet-day fires, which need three nodes (16.7% against the engine's
  21.9%; the protocol expects 20%). On 60 fresh seeds the calibration tails of the two backgrounds do not differ
  significantly (share above 1 su 0.80% vs 0.65%, KS p 0.51; 99.97% quantile 2.35 vs 2.29 su, p 0.18), although the
  engine is slightly higher on every measure. The gap is recorded as sampling (`DECISIONS.md` P7-14).

The golden tests keep the report's intervals as written, and their misses are documented rather than tuned away
(`DECISIONS.md` P4-6, P4-7, P5-11, P7-9).

## 3. Node-layer calibration (Phase 5 acceptance)

Quiet pass, held-out test days, golden seeds. Source: `results/summary.json → node`.

| Seed | QCC exceedance at p ≤ 0.01 | Local false candidates / node / 30 d | All candidates / node / 30 d | Tuned h | P1t h |
| --- | --- | --- | --- | --- | --- |
| 11 | 0.88% | 0.70 | 5.04 | 226.6 | 400 (cap) |
| 22 | 1.58% | 0.03 | 3.29 | 400 (cap) | 400 (cap) |
| 33 | 1.03% | 1.02 | 4.09 | 210.7 | 400 (cap) |
| 44 | 0.61% | 0.83 | 0.83 | 214.6 | 400 (cap) |
| 55 | 1.39% | 0.69 | 9.46 | 207.1 | 400 (cap) |
| **Mean** | **1.10%** (target 0.8–2.0%) — pass | **0.65** (target 0.5–1.5) — pass | | 251.8 | |

The report's simulation on the same seeds: exceedance 1.54%, local candidates 1.70 (seed 55 alone gives 4.25).
"All candidates" includes common-mode periods such as haze, which the edge layer handles in Phase 6. Seed 22's cap is
explained in `KNOWN_ISSUES.md` (improvement backlog) and `DECISIONS.md` P5-10.

## 3b. Operating dial and node spacing (Phase 7)

**Operating dial** (golden seeds, P2; source `summary.json → dial`). Each point re-tunes h for another node-local
false-candidate target and replays the same runs:

| Target (false candidates per node) | Mean h | False incidents / month | Confirmed within 3 h | Median minutes |
| --- | --- | --- | --- | --- |
| 1 per 60 days | 277.2 | 4.0 | 222/324 | 67 |
| 1 per 30 days (design) | 251.8 | 3.4 | 231/324 | 62 |
| 1 per 14 days | 198.1 | 7.6 | 267/324 | 55 |
| 1 per 7 days | 158.6 | 14.2 | 280/324 | 46 |

**Node spacing** (seeds 11, 22, 33, P2; source `summary.json → spacing`):

| Spacing | Confirmed within 3 h | Report | Single-node alert within 3 h | False incidents / month |
| --- | --- | --- | --- | --- |
| 70 m | 119/189 = 63% | 85% | 181/189 = 96% | 4.0 |
| 100 m | 63/189 = 33% | 56% | 160/189 = 85% | 4.0 |
| 150 m | 10/189 = 5% | 13% | 112/189 = 59% | 4.0 |

The fall with spacing matches the report's shape; the levels are lower for the reason in section 2. False alarms do
not change with spacing because the neighbourhood radius scales with it (R = 1.6 s) on a regular grid.

## 4. Model checks against published references

| Check | Result |
| --- | --- |
| FFMC (M7) vs cffdrs `fwi_01`, 48 days | max error 0.005 (tolerance 0.1) |
| Relative humidity (M6), 30 °C with dew point 10 °C | 28.9% |
| Path loss (M38) | 100 dB at 200 m, 120 dB at 400 m |
| Legacy plume | 2.5 su at 50 m downwind, 0.25 su upwind |
| Gaussian plume crosswind profile | within 0.1% of the tabulated σ_y |
| Wilson / Poisson intervals | 272/328 → 82.9% (78.5–86.6); 32 in 150 days → 6.4/month (4.4–9.0) |
| Conformal floor | n = 1000 → p_min = 1/1001 |
| Greedy siting | ≥ (1 − 1/e) of a brute-forced optimum |

## 5. Demo recording outcome (`node_mature`)

31 days simulated, days 29–31 recorded; tuned h 226.6; calibration sets of 3,360 values per bin; day 31 set to a dry,
busy day. The day-31 fire (13:00) gave node candidates at nodes 41 (+67 min) and 31 (+108 min) and was confirmed at
+134 min by the real edge layer (SCMR ratio 11.1, Fisher p_C 7.5e-6, posterior odds 0.42 ≥ 0.01). On the haze day
(day 30) SCMR leaves 3 alerts; the same run with SCMR off (`node_mature__scmr-stub`) has 15. Source:
`recordings/node_mature.prs.jsonl.gz` and its variant.

## Reproduce

```bash
prahari experiment --preset golden --jobs 4        # sections 1, 3, 3b (dial) → results/golden.json, summary.json
prahari experiment --preset ablation --jobs 4      # section 1 (P2 minus QCC, minus TTC)
prahari experiment --preset spacing --jobs 4       # section 3b (spacing)
prahari experiment --preset seeds20 --jobs 4       # section 2 (engine side of the 20-seed comparison)
PRAHARI_GOLDEN=1 PRAHARI_JOBS=4 pytest engine/tests/golden   # the golden assertions
prahari run --config configs/scenarios/node_mature.yaml --out recordings/node_mature.prs.jsonl.gz   # section 5
```

The report simulation's side of the 20-seed comparisons was run with short scripts that call
`reference/prahari_simulation.py`'s `run`; the per-seed outputs of both sides are kept in
`engine/tests/golden/equivalence_*.json`.
