# Phase 7 — Experiments and results

## Goal

Turn the simulator into an evaluation bench: run every pipeline and every "mechanism removed" variant under the
report's test protocol, sweep the operating point and the node spacing, repeat over many seeds, and show all of it in
the dashboard's Results tab — straight from result files, with the seeds and simulated days on every chart.

## What was built

- **Per-fire wind** (approved after Phase 6): `plume.wind: per_fire` gives each protocol fire its own constant random
  wind, exactly as the report simulation injects fires. Demo scenarios keep the weather-driven wind.
- **Offline replay** (`engine/prahari/eval/offline.py`): a recorder keeps each tick's node evidence and candidates;
  edge variants and the operating dial are replayed from that record through the same registered stages.
- **Harness** (`eval/experiments.py`): pipelines grouped by the node-layer modules they change; `--jobs N` runs seeds
  in parallel; spacing sweeps.
- **Report table** (`eval/report.py`): `results/summary.json` combines the golden, ablation, spacing and 20-seed
  presets and lists every pipeline beside the report's row.
- **Presets** (`configs/experiments/`): `golden` (P0, P1, P1t, P2, P2-SCMR, P2-RAQ, node metrics, dial), `ablation`
  (P2-QCC, P2-TTC), `spacing` (70/100/150 m) and `seeds20` (seeds 11–30).
- **Dashboard**: an ablation chart, the operating-dial chart and the spacing chart (`ExperimentCharts.tsx`); cleaner
  labels on all interval charts.
- **Tests**: unit tests for the offline replay (equal to the live edge and CUSUM), per-fire wind, grouping, dial and
  table order; golden tests for the ablations, detection and spacing.

## How it works

For each seed the harness runs a quiet pass (no fires) and a fire pass (protocol fires). While the node layer runs,
the recorder stores S = −ln p for every node and minute. The edge is not run live: afterwards, the recorded node
candidates are fed through the edge stages once for P2, once with SCMR as its stub and once with RAQ as its stub. The
operating dial re-tunes the node threshold h for four target false-candidate rates using the recorded evidence and
the same bisection the node CUSUM uses, replays the CUSUM and then the edge. Only ablations that change the node
layer (QCC, TTC) need passes of their own. Every result is pooled over seeds with the M44/M45 intervals.

## Challenges and issues

1. **Cost.** Five pipelines × five seeds × two passes, plus the dial and the spacing sweep, would take hours if every
   variant were simulated.
2. **The approved per-fire wind did not raise detection.** Golden P2 detection moved from 246/324 to 231/324.
3. **P2 detection stays below the report** (71.3% on the golden seeds; 72.8% against the report simulation's 82.2%
   over seeds 11–30), and so do the confirmation rates that depend on it (ablations, spacing).
4. **The node ablations are defined differently** in the report simulation.
5. **Chart clutter.** Value labels sat on top of the intervals and per-seed ticks; long titles ran into legends.
6. **One dial point looks inverted**: 1 per 60 days gave 4.0 false incidents per month, 1 per 30 days 3.4.

## Decisions and trade-offs

| Decision | Pros | Cons | Ids |
| --- | --- | --- | --- |
| Replay the edge and the dial offline from recorded evidence | one pair of passes serves P2, P2-SCMR, P2-RAQ and four dial points; tested equal to the live path | the harness no longer runs the edge live (recordings still do) | P7-2, P7-4 |
| Per-fire wind only in experiment presets | the report's fire model for evaluation; demos keep realistic weather wind | two wind modes to explain | P7-1 |
| Ablations = module stubs | the SPEC's meaning; the same switches as the dashboard | node ablations differ from the report simulation's | P7-10 |
| Report-only values tested the other way round (report value inside our interval) | a fair test where the report gives no interval | weaker than an interval check | P7-6 |
| Separate preset files combined into one summary | presets can be rerun independently; provenance recorded | one more file per preset | P7-5 |
| `--jobs` via the standard library | ~4× faster on 4 cores, identical results | memory per process | P7-7 |

## Resolution

- 1: offline replay and `--jobs`. The four presets run in about 45 minutes on four cores (SIM development machine).
- 2 and 3: investigated, not tuned (`DECISIONS.md` P7-9):
  - the fire path is now identical — a seed-11 check gives the same number of nodes lifted per fire in both
    simulators (8.2 / 5.2 / 2.9 against 8.2 / 5.1 / 3.0 at 0.5 / 1 / 2 su), so the Phase 6 transport explanation was
    withdrawn;
  - over seeds 11–30 false alarms agree for all six pipelines, and detection agrees for P0, P1 and P1t; only the
    pipelines with the conformal node layer detect less;
  - the engine's quiet fast residual carries a much heavier upper tail in the calibration days (seed 11: 2.2% of
    minutes above 1 su against 0.29%), almost all of it from haze; the haze model is the same, and the engine's
    seeds drew more haze episodes (66 against 45 in days 0–27).
  - on fresh seeds 31–50 the gap halves (79.4% against 84.4%) and is no longer significant on its own, while false
    alarms are identical (7.05 per month each); over all 40 seeds a gap of about 7 points remains (p 0.007). Part of
    the Phase 6 gap was sampling; the follow-up below (reverse swap) traced the rest to sampling as well.
- 4: legacy forms built after approval (follow-up below); the stub forms remain the default switch.
- 5: labels moved past each interval, legends below titles, the x axis pinned to the bottom.
- 6: explained — with few incidents, a higher h can shift when two nodes' candidates coincide; detection and latency
  along the dial are monotone.

## Follow-up: legacy ablations and the reverse swap

After reviewing Phase 7 the developer approved two follow-ups.

**Legacy ablations.** The report's simulation removes QCC and TTC differently from our module stubs: "minus
conformal" runs the CUSUM directly on a median/MAD-scaled fast residual, and "minus two-timescale" ranks the capped
slow z. Three parameters now reproduce those variants (`ttc.detect_on`, `qcc.form`, `cusum.statistic`), selected by
`experiment.ablation_form: legacy`; the signed z travels in two new optional contract fields. Every default run is
unchanged (frames identical). On the report simulation's own seed-11 signals the engine gives its results — exactly
for P2 minus QCC, and for P2 minus TTC once its day-1 look-ahead is accounted for (a causal system cannot see the
whole first day before scoring it). On the golden seeds: P2 minus QCC 8.8 and P2 minus TTC 8.4 false incidents per
month (report 17.4 and 11.8); over seeds 11–30 both agree with the report simulation's distribution (p 0.48 and
0.44) (SIM).

**Reverse swap.** Every combination of the two backgrounds and the two fire sets went through the same chain over
seeds 11–30:

| Confirmed within 3 h (SIM) | Engine fires | Report-simulation fires |
| --- | --- | --- |
| Engine background | 72.7% | 77.4% |
| Report-simulation background | 81.1% | 81.4% |

Both ingredients matter, and neither is a model difference: the haze process is statistically the same (200
histories each), the fire sets match in geometry and timing but the report's seeds happened to draw fewer wet-day
fires (16.7% against the expected 20%), and the calibration tails of the two backgrounds do not differ significantly
on 60 fresh seeds. The detection gap is therefore treated as sampling (`DECISIONS.md` P7-14).

**Lesson.** A 2 × 2 swap is worth its compute: it split one unexplained number into two named, testable causes,
and each was then checked against the model itself on fresh seeds rather than on the seeds that showed the gap.

## Acceptance results

| # | Test | Result (SIM) |
| --- | --- | --- |
| 1 | Golden-number tests pass (§9.3) | **not met** — after the follow-up 5 of 21 golden tests pass (P1 false incidents; P1 and P1t detection; both node-layer targets; with the stub ablations P2-QCC detection had also passed); 16 miss: P2-QCC detection (legacy 67.3% vs 78%), false incidents for P0, P1t, P2 and the four ablations, P0 and P2 detection, three ablation-detection checks and all three spacing checks. Documented, not tuned (DECISIONS P7-9, P7-10; KNOWN_ISSUES) |
| 2 | Charts render from files | **pass** — every chart reads `results/summary.json`; no result values in the dashboard code |
| 3 | Each chart shows seeds and days | **pass** — footers name the seeds and "14 + 14 + 30 simulated days per seed" |

## What to show

Dashboard ▸ *Results*: the false-alarm chart (P0 → P2, about 100× fewer false incidents than P0 in simulation), the
ablation chart (every mechanism removed raises false alarms), the operating dial (the design point and what faster
confirmation costs), and the spacing chart (why 70 m). Every footer states the seeds and simulated days.
