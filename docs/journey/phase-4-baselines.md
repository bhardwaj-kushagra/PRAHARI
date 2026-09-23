# Phase 4 — Baselines and evaluation harness

## Goal

Run the "old ways" on the same signals and build the machinery to measure any pipeline: false incidents per month and
fires confirmed within three hours, with proper confidence intervals, reproducing the report's published baseline
numbers in legacy mode.

## What was built

- `baseline_p0` (M22, fixed threshold) and `baseline_p1` (M23, v1 as written), each with a stub and an off, running in
  every scenario; their alarms are recorded as `p0_alarm` / `p1_alarm` events.
- `eval/stats.py`: Wilson (M44) and exact Poisson (M45) intervals, incident merging and the detection rule (M46).
- `eval/experiments.py` and `prahari experiment`: per seed a quiet pass and a fire pass over 14 + 14 + 30 days, with
  protocol fires drawn from a new `protocol` random stream.
- Dashboard **Results** tab and a **Baselines** map layer (grey ▲ for P0, grey ○ for P1).

## How it works

The harness calls exactly the same signal code as a recording run but builds no frames. It merges alarms into
incidents (within 60 minutes and 2R), counts them over the 30 test days, and checks each protocol fire for a
confirmation within 150 m and three hours.

## Challenges and issues

1. **Exact semantics.** Small details of the report's code — the refractory counter, how v1 initialises its baseline
   with a whole day of hindsight — change the numbers.
2. **A tick loop cannot look ahead**, but v1's initialisation uses the whole first day.
3. **P0 missed the report's interval.** P1 came out at 136.2 per month (report 123–143, pass) but P0 at 340.6 (report
   277–307).
4. **Why the miss?** Either a code difference or randomness.
5. **Chart polish**: legend colour, label alignment and clipping in the results chart.

## Decisions and trade-offs

| Decision | Pros | Cons |
| --- | --- | --- |
| Copy the oracle's semantics line by line and test on identical inputs (P4-1) | proves the code equals the report's | inherits the report's quirks |
| Buffer day 1, initialise at its end, replay it (P4-2) | exact equivalence in a tick loop | no baseline alarms on day 1 |
| New `protocol` stream appended at the end (P4-3) | no other module's numbers change | engine and oracle draw different fires |
| Split the tick into `step_signals` and the rest (P4-4) | the harness runs identical code | a small change to an accepted file (approved) |
| Report values stored only in `tests/golden/`, copied into the summary with a label (P4-5) | no hard-coded results in code | one indirection |
| **Do not tune to hit the report**; investigate instead (P4-6) | scientific honesty | a visible miss in the golden test |

## Resolution — the P0 investigation

Because the baseline code matched the oracle exactly on identical inputs, the gap had to be statistical. False alarms
come in bursts (a haze episode causes many), so seed-to-seed spread is far wider than the report's Poisson interval.
Two measurements settled it:

- The oracle itself over seeds 11–30 averages P0 = 321.9 per month (standard deviation 49.6); the report's 5-seed 291
  is a low draw from its own distribution.
- Running our engine over the same 20 seeds gives P0 = 310.9 against the oracle's 321.9 (Welch p = 0.58) and P1 = 141.8
  against 139.1 (p = 0.40): no detectable difference.

The golden test keeps the report's interval as written and is expected to miss P0 with these five seeds; the
explanation lives in `DECISIONS.md` P4-6/P4-7 and [../results/validation.md](../results/validation.md).

## Acceptance results

| Test | Result (SIM) |
| --- | --- |
| P1 within the report's interval | pass — 136.2 (126.2–146.8) vs 123–143 |
| P0 within the report's interval | miss — 340.6 (324.6–357.2) vs 277–307; sampling, not code (see above) |
| M44 reference: 272/328 | 82.9% (78.5–86.6%) |
| M45 reference: 32 in 150 days | 6.4 per month (4.4–9.0) |
| Detection within 3 h | P0 314/324, P1 322/324 |

## What to show

*Results* tab (P0 and P1 with the report's intervals as hollow diamonds); `signals_3day` with the *Baselines* layer on
during the haze episode.
