# Phase 9 — Regimes, satellite race, learning loop and faults

## Goal

Show four things the earlier phases could not:

- the system working in different fire regimes;
- how it compares with the satellites people already rely on;
- a system that gets better as evidence arrives;
- a network that handles its own broken sensors gracefully.

Each is a separate sub-feature that could be parked on its own. None had to be.

## What was built

- **Arrival-time fix** (approved at the start of the phase; closes the Phase 8 item):
  - Each delivered candidate carries the minute it was raised (`Delivered.t_detect`).
  - The cluster window uses that minute, so a frame delayed by the radio still meets the right neighbours.
- **Satellite race (M37):** `satellite/race.py` draws each fire's plan when it ignites:
  - the overpass that sees it, and any overpasses that miss it;
  - the alert time.

  The race timeline under the map compares that with PRAHARI's first candidate and its confirmation (View 4).
- **Faults and health weights (M21, M29):**
  - `sensors/faults_real.py` injects stuck, offset, spike and dropout faults.
  - `detect/prahari/score_real.py` gives each node a health weight from three checks: fresh data, a non-flat reading, and agreement with its neighbours.
  - A node below 0.1 abstains, and the map draws it as a fault.
- **Lightning (M3 λ_light) and the SCMR relaxation:**
  - Scripted storms drop Poisson strikes that can start fires.
  - While a storm is flagged, SCMR accepts a ratio of 1.5 instead of 3.
- **M33 integral prior:** `srp.form: integral` computes each cluster's own prior from the ignition map. It is an option; no scenario uses it yet.
- **Regime Cards:** `configs/regimes/` holds `india`, `canada`, `usa` and `australia`. Every recording header names its card, and the dashboard's regime selector filters the recording list (View 8).
- **Learning loop (M36):**
  - `detect/prahari/learn_real.py`: a logistic-regression likelihood ratio fitted by IRLS, used in place of the bound once K ≥ 10.
  - `eval/learning.py` and `prahari experiment --preset learning`: the learning curve over K = 5–100 burns on held-out seeds, and the calibration-maturity curve over 1–14 days of quiet data. Both are charted in Results.
- **Scenarios:**
  - `satellite_race` (India)
  - `sensor_fault` (India)
  - `lightning_storm` and `lightning_storm__no-relax` (Canada)
  - `power_line_corridor` (USA)
  - `bushfire_afternoon` (Australia)

## How it works

**Satellite race.** Satellites pass at fixed local times. When a fire starts, the model asks, pass by pass, whether the fire is yet big enough to be seen (500 m² at the M37 growth rate, which takes about 75 minutes). If it is, the model checks whether cloud or canopy hides it (one chance in five). The first pass that sees the fire starts a processing delay: 40–60 minutes for MODIS, 60–90 for VIIRS. Then the alert goes out. The plan is drawn once, at ignition, so the timeline can show the whole race from the first frame.

**Health weights.** Every minute each node's weight is the product of three checks:

- **Fresh data.** It has sent a reading in the last 5 minutes.
- **Not stuck.** Its reading has varied in the last hour, compared with its own usual variation.
- **Neighbour consensus.** Its slow baseline agrees with its neighbours' baselines. The weight falls smoothly beyond a robust z of 3.

The node's evidence is multiplied by its weight. At zero the node adds nothing, and the edge never hears from it.

**Learning loop.** The M46 protocol is run on two training seeds and three held-out seeds.

1. Every cluster window the edge forms is listed with four features: Fisher's X, cluster size, the SCMR ratio and the mean health weight.
2. The windows of the first K burns are labelled fire; every quiet-pass window is labelled no fire.
3. A logistic regression (L2, standardised features) is fitted. Its odds, divided by the training odds, become the likelihood ratio.
4. On the held-out seeds, each rule — the bound, and the fit for each K — gets the most permissive threshold that keeps false incidents within 3 a month.
5. The confirmation rate and median latency at that threshold are compared.

## Challenges and issues

1. **A stuck sensor's weight came back after about 13 hours.** The stuck test compares the last hour's variance with the node's median hourly variance. Once the stuck hours filled that history, the median itself fell to almost zero, and the flat window looked normal again.
2. **The health-weight stage was slow** at 0.77 ms per tick: neighbour lists, hourly medians and consensus were computed every minute.
3. **The storm relaxation held clusters after the storm.** Fires started late in a storm are still being detected an hour or two after it ends, and SCMR went back to 3 too soon.
4. **The first learning fit ignored Fisher's X.** Trained on every window, the fit learned that big, network-wide haze windows (large X, low SCMR ratio) are not fires. It weighted X to almost nothing and fell below the bound.
5. **The first full learning curve was not monotone:** 49, 54, 37, 37 and 71% confirmed for K = 5, 10, 20, 50 and 100 (SIM). The training loop stopped reading seeds once it had K burns. So the quiet (negative) data changed with K — 91 windows up to K = 50, 209 at K = 100 — and each K was fitted against a different prior.
6. **X and cluster size carry the same information in legacy mode.** Every candidate has the same M32 p-value, so X = 14.5 × |C| exactly. The fit splits the weight between them equally; L2 keeps that stable.
7. **A satellite overpass can be missed.** In `lightning_storm` one fire's 22:30 Terra pass misses it (cloud or canopy); the 01:30 Aqua pass sees it and the alert comes at 02:18 the next morning.
8. **Small offsets are not caught.** Node 77's +1.5 su offset keeps its weight.
9. **A stuck sensor can raise one candidate before it abstains.** Node 55 raised a candidate at 09:33 and abstained at 09:59; no alarm followed.
10. **Timing is data-dependent in the maturity curve.** With 14 days of calibration, one seed's CUSUM tuning ends at its cap (h = 400). This is the known seed issue from Phase 5, and it lengthens that point's median.

## Decisions and trade-offs

| Decision | Pros | Cons | Ids |
| --- | --- | --- | --- |
| Phase 9 modules real only in their scenarios and preset | every earlier result and recording unchanged | the default demo has no faults, lightning or satellite | P9-1 |
| Draw the satellite plan at ignition and publish it as an event | the race timeline needs no look-ahead; one stream, deterministic | the plan cannot react to later fire behaviour | P9-3 |
| Fault glyph from the health weight, not the injected fault | shows what an operator would see ("this sensor abstains") | an undetected fault shows no glyph (the offset case) | P9-6 |
| Hold the storm flag for 180 min after a storm | clusters from late strikes are not held | a genuine haze event right after a storm meets the relaxed ratio | P9-7 |
| Train only on SCMR-passed windows | the fit learns about the windows the rule is applied to | the fit cannot help with windows SCMR rejects | P9-10 |
| Compare rules at a fixed false-alarm budget on held-out quiet runs | a fair comparison; the curve shows learning, not a moved threshold | the budget threshold is set on the evaluation seeds' quiet runs | P9-11 |
| Quiet data fixed across K; K counts burns only | K measures the scarce resource (controlled burns) | assumes a network already has two months of quiet data | P9-10 |

## Resolution

- **1:** Hours already stuck are stored as missing and skipped by the median, and a window flatter than 1e-9 su² counts as stuck on its own. The stuck node now stays below 0.1 for the whole fault.
- **2:** Neighbour lists became padded arrays, the hourly reference is cached, and the day-long consensus is refreshed every 10 minutes. The stage now takes 0.14 ms per tick.
- **3:** The storm flag is held for 180 minutes after the storm (`storm_hold_min`, ASM). With the hold, SCMR holds none of the 20 storm-afternoon decisions, against 4 without the relaxation (`lightning_storm__no-relax`); 6 of the 8 fires are confirmed within 3 h in both runs (SIM).
- **4:** Training uses only the windows that pass SCMR, since M34 is applied to no others.
- **5:** Fixed as a bug: every K now uses all training seeds' quiet windows. The curve became monotone (acceptance 2 below). The numbers from the buggy run are kept here, not charted.
- **6:** Documented; the features are kept as SPEC M36 lists them, because they separate once health weights or other p-values are in play.
- **7:** Shown on the timeline as a cross at the missed overpass.
- **8 and 9:** `KNOWN_ISSUES.md`, with proposals.
- **10:** Reported as is; the seeds were not changed.

## Acceptance results

| # | Test | Result (SIM) |
| --- | --- | --- |
| 1 | The race timeline reports correct deltas on scripted fires | **pass**:<br>• `satellite_race`: ignition 14:00, first node candidate 14:55, confirmation 15:14, Terra overpass 22:30, satellite alert 23:20.<br>• The deltas are checked against the events in `race.test.ts` and in the M37 unit tests (overpass choice, threshold, miss and delay). |
| 2 | The learning curve is monotone within noise from K = 5 to K = 100 | **pass**:<br>• Confirmed within 3 h at 3 false incidents a month on held-out seeds 51–53 (183 fires): 49% (bound, K = 5), 68%, 68%, 68%, 71% for K = 10, 20, 50, 100.<br>• Median latency 75 → 58.5–60 min.<br>• No step down. |
| 3 | A stuck sensor's health weight falls below 0.1 within 90 minutes | **pass**:<br>• 58 min in the unit test.<br>• 59 min for node 55 in `sensor_fault`.<br>• A dropout abstains after 5 min. |

The calibration-maturity curve (M26), SIM:

- The floor p_min falls from 4.1e-3 with 1 day of quiet data to 3.0e-4 with 14 days.
- The median time to the first node candidate falls from 92.5 min to 46–47 min at 4–7 days.
- At 14 days it is 59 min, lengthened by the capped seed (challenge 10).

More outcomes and the reproduce commands are in [../results/validation.md](../results/validation.md) §7.

## What to show

- **`satellite_race`, day 31.** Scrub from 14:00. The race timeline fills in as the fire is seen by nodes, confirmed at 15:14, and finally alerted by the satellite at 23:20: about eight hours later (SIM).
- **`sensor_fault`, day 31 from 09:00.** Node 55 turns grey at 09:59 ("this sensor abstains"); node 23 at 11:05. The 13:00 fire is still confirmed by its healthy neighbours.
- **`lightning_storm`.** Eight fires in an afternoon, several confirmed at once; compare the "why" panel with `lightning_storm__no-relax`.
- **The regime selector.** Pick Canada, USA or Australia and open their recordings.
- **Results.** The learning curve steps up from the bound as soon as ten burns are available, then holds. The maturity chart shows the floor falling with every quiet day.
