# Results and validation

All numbers below are **simulation output (SIM)** from the files named, as of Phase 5. They change only when the
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

Per-seed false incidents per month: P0 299, 321, 388, 308, 387; P1 139, 145, 117, 140, 140; P1t 14, 12, 16, 19, 11.

## 2. Why some 5-seed results miss — and why that is not a code error

**Step 1 — same code.** The engine's P0, P1 and P1t (and every node-layer function) give identical outputs to the
report's own simulation (`reference/prahari_simulation.py`) when fed identical arrays (unit tests in
`engine/tests/unit/test_eval_phase4.py` and `test_node_phase5.py`).

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

31 days simulated, days 29–31 recorded; tuned h 226.6; calibration sets of 3,360 values per bin. The day-31 fire
(13:00) gave node candidates at nodes 41 (+67 min) and 31 (+108 min) and was confirmed at +134 min by the current stub
edge (two agreeing nodes). Source: `recordings/node_mature.prs.jsonl.gz`.

## Reproduce

```bash
prahari experiment --preset golden                 # section 1 and 3 → results/summary.json (~8 min)
PRAHARI_GOLDEN=1 pytest engine/tests/golden        # the golden assertions
prahari run --config configs/scenarios/node_mature.yaml --out recordings/node_mature.prs.jsonl.gz   # section 5
```

The 20-seed comparisons (section 2) were run with short scripts that call `eval.experiments.run_pass` and the oracle's
functions; their per-seed outputs are kept in `engine/tests/golden/equivalence_*.json`.
