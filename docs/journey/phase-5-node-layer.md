# Phase 5 — PRAHARI node layer

## Goal

Turn each node's raw reading into calibrated evidence: a baseline that cannot lock up, a residual that ignores the
daily cycle, a p-value that is honest whatever the noise looks like, and a CUSUM whose threshold is tuned on the
network's own quiet days. Also the tuned version of v1 (P1t) and the dashboard's Node Inspector.

## What was built

- `ttc` real (`ttc_real.py`): slow baseline with the 180-minute freeze cap (M24); fast residual against the lagged
  60–180-minute mean, computed in constant time per tick (M25).
- `qcc` real (`qcc_real.py`): conformal p-values per node and 4-hour time-of-day bin (M26), calibrated for 14 days,
  then frozen and searched with one vectorised binary search; an optional 28-day sliding window.
- `cusum` real (`cusum_real.py`, `tuning.py`): CUSUM of −ln p with k = 1.5 (M28); h tuned by bisection on the tuning
  days with common-mode periods excluded; `h_default` until then.
- `baseline_p1t` (`v1t.py`): v1 with the capped baseline and a tuned threshold.
- Harness: P1t and node metrics (exceedance, local candidates, tuned h). Dashboard: Node Inspector, calibration
  badge, node-layer table in Results. Scenarios `node_3day` and, as a follow-up, `node_mature` (warm start).

## How it works

See [../guide/02-background.md](../guide/02-background.md#26-praharis-node-layer-m24m29). In short: residual → rank
among the node's own history at this time of day → p-value → −ln p accumulated by a CUSUM → candidate when it crosses
a threshold tuned for one node-local false candidate per node per 30 days.

## Challenges and issues

1. **Matching the report exactly** in a tick loop: hindsight initialisation of the slow baseline, the report's
   refractory rule, the bisection's exact bounds.
2. **Speed.** A naive conformal p-value would compare each score with thousands of stored values for every node every
   minute.
3. **The common-mode rule needs the slow z**, but the CUSUM stage only receives scores.
4. **The framework scenarios changed meaning.** With the real node layer the smoke scenario's stub-pipeline
   confirmation disappeared (a Phase 0 acceptance test failed).
5. **P1t's bisection ends at its search cap** (h = 400) on every golden seed, in the oracle too.
6. **Seed 22: the node CUSUM's tuning hit the cap.** A second network-wide rise right after a long haze episode was not
   recognised as common mode.
7. **Only one node flagged the fire in the young `node_3day` network**, so the stub quorum of two never confirmed it.
8. **SPEC wording**: M28 said |z| ≥ 3, the report's code uses one-sided z ≥ 3.

## Decisions and trade-offs

| Decision | Pros | Cons |
| --- | --- | --- |
| Real stages in new files beside unchanged stubs (P5-1) | accepted code untouched; stubs still sacred | more files |
| Identical-input tests against the oracle for every function (P5-2) | proves equality | ties the engine to the oracle's details |
| Freeze-and-sort calibration with a row-offset binary search (P5-3) | 0.14 ms per tick | the default set is static after 14 days (sliding is optional) |
| Slow z shared through `RunContext.z_slow` (P5-7) | no stage signature changes | one shared per-tick value |
| Framework scenarios pin the stub node layer (P5-8) | their Phase 0 demos keep working | two behaviours to explain |
| `h_default` = mean tuned h of the oracle (DER) (P5-6) | sensible behaviour before tuning | young networks are slower to detect |
| Keep P1t's cap result, as the oracle does (P5-6, P5-11) | faithful reproduction | P1t is not "tuned" in practice |
| Seed-22 finding: document and defer, don't change the method (P5-10) | golden stays reproducible | a known weakness remains |
| Warm-start recordings for a mature network (P5-14) | the demo shows the designed operating point | 65 s to generate instead of 7 s |
| Apply erratum E-7 (P5-5) | SPEC matches the code | a SPEC version bump (1.0.3) |

## Resolution

- 1–3 were solved in the design (exact tests pass; the node layer costs about 0.3 ms per tick).
- 4: framework scenarios pin the stub node layer; the Phase 0 runner test's example module moved from `qcc` to
  `energy`.
- 5: reported, and checked against the oracle over 20 seeds (below).
- 6: diagnosed — during a long haze the capped baseline inflates its spread, so in the next rise only about 10% of
  nodes reach slow z ≥ 3, below the 25% threshold, while every node's p-value sits near its floor. The engine's slow z
  equals the oracle's exactly, so it is the method's behaviour. Logged in `KNOWN_ISSUES.md` (improvement backlog) with
  a proposal to define common mode from the detection evidence, to revisit after Phase 7.
- 7: `record.from_day` added; `node_mature` simulates 31 days and records days 29–31. With mature calibration (3,360
  values per bin) and tuned h 226.6, nodes 41 and 31 raise candidates 67 and 108 minutes after ignition and the fire is
  confirmed at 134 minutes (SIM). No model parameter changed.
- 8: SPEC updated (E-7).

## Acceptance results (golden seeds 11, 22, 33, 44, 55)

| Test | Result (SIM) | Report simulation, same seeds |
| --- | --- | --- |
| QCC exceedance at p ≤ 0.01, target 0.8–2.0% | **1.10%** — pass | 1.54% |
| Local false candidates per node per 30 d, target 0.5–1.5 | **0.65** (median 0.70) — pass | 1.70 (misses; seed 55 gives 4.25) |
| TTC stub reproduces lock-up and daily-cycle leakage | pass: stub frozen after a +2 su step; keeps 0.953 of a daily cycle vs 0.52 for the fast residual | — |
| P1t false incidents per month | 14.4 (11.3–18.1) vs report 18.6 (15.0–22.8); 20-seed check: engine 17.1 vs oracle 18.3, Welch p = 0.58 | 18.6 |
| P1t confirmed within 3 h | 61% vs report 59% (53–64) | — |

## What to show

`node_mature`: day 31 at 13:00, click node 41 or 31 and open the *Node* tab. `node_3day` shows the same story in a
young network, with the p floor falling day by day. *Results* shows the node-layer table.
