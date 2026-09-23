# Results and validation

All numbers below are **simulation output (SIM)** from the files named, as of Phase 6. They change only when the
engine or configuration changes; regenerate them with the commands at the end.

## 1. Golden reproduction (legacy mode)

Configuration `configs/experiments/golden.yaml`: 100 nodes at 70 m, seeds 11, 22, 33, 44, 55, the M46 protocol
(14 calibration + 14 tuning + 30 test days per seed), legacy signal, source and plume models. Source:
`results/summary.json`.

| Pipeline | False incidents / month (95% CI, M45) | Report (SPEC §9.3) | Confirmed within 3 h (M44) | Report |
| --- | --- | --- | --- | --- |
| P0 fixed threshold | 340.6 (324.6–357.2) | 291 (277–307) — outside | 314/324 = 96.9% | 95% (93–97) |
| P1 v1 as written | 136.2 (126.2–146.8) | 132 (123–143) — **inside** | 322/324 = 99.4% | 99% (98–100) |
| P1t v1 replay-tuned | 14.4 (11.3–18.1) | 18.6 (15.0–22.8) — just outside | 197/324 = 60.8% | 59% (53–64) — inside |
| P2 PRAHARI | 3.4 (2.0–5.4) | 6.4 (4.4–9.0) — below | 246/324 = 75.9% (71–80%) | 83% (79–87) — below |

Per-seed false incidents per month: P0 299, 321, 388, 308, 387; P1 139, 145, 117, 140, 140; P1t 14, 12, 16, 19, 11;
P2 5, 5, 2, 0, 5. P2's median time from ignition to confirmation is 65 minutes.

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

**P2 (Phase 6)**, same 20 seeds, both passes (`equivalence_p2_seeds11_30.json`):

| P2 | Report simulation | Engine | Welch p | Mann–Whitney p |
| --- | --- | --- | --- | --- |
| False incidents / month | 7.20 (sd 5.20) | 6.25 (sd 2.73) | 0.48 | 0.84 |
| Confirmed within 3 h | 82.2% (sd 11.2) | 74.0% (sd 11.9) | 0.03 | 0.005 |

False alarms agree; detection does not. Our node and edge code reproduces the report simulation exactly on its own
data (seed 11: tuned h 238.13, 54/63 fires), so the difference lies in the simulated world: the engine's seeds drew
more haze in their calibration and tuning days (3.3 vs 2.25 episodes on average; detection falls about 4 points per
episode), and the engine carries smoke on its continuous weather wind while the report simulation gives each injected
fire a constant random wind (swapping in the report's fires on seeds 12–19 raises detection from 79.2% to 82.7%).
The proposed legacy per-fire wind option awaits approval (`DECISIONS.md` P6-11, `KNOWN_ISSUES.md`).
The golden tests keep the report's intervals as written, and their misses are documented rather than tuned away
(`DECISIONS.md` P4-6, P4-7, P5-11).

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
prahari experiment --preset golden                 # sections 1 and 3 → results/summary.json (~13 min)
PRAHARI_GOLDEN=1 pytest engine/tests/golden        # the golden assertions
prahari run --config configs/scenarios/node_mature.yaml --out recordings/node_mature.prs.jsonl.gz   # section 5
```

The 20-seed comparisons (section 2) were run with short scripts that call `eval.experiments.run_pass` and the oracle's
functions; their per-seed outputs are kept in `engine/tests/golden/equivalence_*.json`.
