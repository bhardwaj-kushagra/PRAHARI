# 2. Background — the science and statistics you need

This page explains, in plain language, every idea the simulator relies on. Each section names the equations
(M-numbers) in [`SPEC.md`](../SPEC.md) §5 where the exact formulas live, and the code that implements them is listed in
[../architecture/03-models.md](../architecture/03-models.md). Terms in **bold** are also in the
[glossary](03-glossary.md).

---

## 2.1 Where fires start and why that matters for siting (M1–M4)

In the Terai and the lower Himalaya most fires are started by people: a discarded match on a footpath, a cooking fire
that escapes, burning to clear grazing land, sparks from a power line. So the chance that a fire starts at a point
falls off with distance from paths, villages, roads and power lines. The simulator models this as an
**ignition-likelihood map** λ(x): each "interface" contributes a term that decays exponentially with distance (M2
computes the distance fields, M3 combines them).

If the likelihood is uneven, where you place a limited number of nodes matters. M1 gives the simple layouts (a
regular grid; a corridor along paths), and M4 places nodes greedily to cover as much likelihood as possible within a
detection radius. The greedy algorithm is the classic answer to "maximum coverage" problems and is guaranteed to
reach at least about 63% (1 − 1/e) of the best possible coverage. On the default landscape (SIM): grid 24%,
corridor 49%, greedy 83% of likelihood covered by 100 nodes with a 50 m radius.

## 2.2 Weather and how dry the fuel is (M5–M8)

Smoke detection and fire risk both depend on weather:

- **Temperature** follows a daily cycle with slow day-to-day variation and minute-to-minute noise (M5).
- **Relative humidity** is computed from temperature and dew point with the Magnus formula (M6): as the afternoon
  warms, humidity falls even though the air's water content has not changed.
- **Fuel moisture** is summarised by the Canadian **Fine Fuel Moisture Code (FFMC)** (M7), a daily index of how dry
  the litter on the forest floor is. It runs from about 0 (soaked) to 101 (bone dry); above about 85 fine fuels catch
  easily. The simulator's FFMC was checked against the official `cffdrs` software's published test outputs and agrees
  within 0.005.
- **Sustained ignition** (M8): not every spark becomes a fire. A logistic curve turns FFMC into the probability that
  an ignition keeps burning (0.5 at FFMC 84 by default).

## 2.3 Fires, smoke and how it reaches a sensor (M9–M16)

A new surface fire grows over tens of minutes, and its smoke output rises with it (M9 legacy; M10 advanced). Under a
forest canopy the wind is weak and smoke creeps downwind; nodes downwind see much more than nodes upwind, and a node
only sees smoke once it has had time to drift there (M16: delay = distance / wind speed).

Two smoke models are available:

- **Legacy (M12, M13):** concentration falls exponentially with distance, multiplied by a directional factor that is
  1 straight downwind and 0.1 upwind. Calibrated so a node 50 m downwind of a fully grown fire reads about 2.5
  **sensor units (su)**. The report's numbers use this model, so it is the default.
- **Gaussian plume (M11, M14, M15):** the textbook atmospheric-dispersion formula, with plume widths from Briggs's
  stability classes and a reduced wind under the canopy. More physical, narrower plumes; an advanced option.

Real smoke is patchy: short-term concentration flickers around its mean, which the models reproduce with a random
"intermittency" factor.

## 2.4 What a cheap gas sensor actually reports (M17–M21)

A **metal-oxide (MOX) gas sensor** changes its electrical resistance when reducing gases (like those in smoke) touch
its heated surface. Its output is not a clean gas concentration. The simulator builds each reading from parts (M18):

- a **baseline** that drifts slowly as the sensor ages;
- a **daily cycle** driven by temperature and humidity (MOX sensors are cross-sensitive to both);
- **autocorrelated noise** — noise that persists from one minute to the next (AR(1) with lag-1 correlation 0.95,
  heavier in the daytime, with occasional heavy-tailed jolts) (M19);
- **nuisance events** — brief spikes from vehicles, cooking or dust, more often at roadside nodes (M20);
- **regional haze** — hours-long rises that hit every node together, like smoke from crop burning far away (M20);
- the **fire signal** from §2.3, passed through the sensor's response curve (M17);
- optionally **faults**: stuck readings, offsets, spike bursts, dropouts (M21, advanced).

The last two bullets are why detection is hard: haze looks like smoke, but it arrives everywhere at once.

## 2.5 The old way: thresholds and textbook CUSUM (M22, M23)

- **P0, fixed threshold (M22).** Learn each node's mean and spread from its first day, then alarm whenever a reading
  goes above mean + 3 standard deviations. Simple, but the daily cycle, drift and haze all cross that line.
- **P1, "v1 as written" (M23).** Track a slow **exponentially weighted moving average (EWMA)** baseline and spread,
  turn each reading into a z-score, and feed the z-scores into a **CUSUM**. Its threshold h ≈ 8.8 comes from a
  textbook formula (Siegmund's approximation) that promises one false alarm per 30 days — *if* the z-scores were
  independent standard normal values. They are not: the noise is autocorrelated, so false alarms come far more often.
  Two nodes near each other must agree to raise an alarm.

**CUSUM** in one sentence: keep a running total of "how much more suspicious than normal" each new sample is,
never let it go below zero, and raise a candidate when the total crosses a threshold h. It is very good at catching
small, persistent changes. The number k subtracted each step is the "allowance" for normal wobble; the **average run
length (ARL)** is how long, on average, a quiet node goes before a false crossing.

## 2.6 PRAHARI's node layer (M24–M29)

- **Two-timescale conditioning, TTC (M24, M25).** Keep a slow EWMA baseline (12-hour time constant) for drift and
  health, but detect on a **fast residual**: the reading minus the average of the window 1 to 3 hours ago. A slow
  baseline alone leaves about 95% of a daily cycle in the residual; the lagged window removes much more of it
  (about half remains in the simulator's pure-sine test, and the next step absorbs the rest by time of day). The slow
  baseline is frozen while a node is extreme, but only for up to 3 hours — without that cap, v1's baseline could stay
  frozen forever after a lasting change ("lock-up").
- **Quantile-calibrated conformal p-values, QCC (M26).** Instead of assuming residuals are normal, compare each new
  residual with the node's own history at the same time of day (six 4-hour bins) from the calibration days. The
  **p-value** is the share of past residuals at least as large as the new one: p = (1 + count) / (n + 1). This is a
  **conformal** p-value: if quiet data are exchangeable, it is honestly calibrated whatever their distribution. Its
  smallest possible value, the **floor**, is 1/(n + 1), so evidence strengthens as calibration grows ("maturity").
- **Node score (M27)** turns p into evidence, −ln p (with one channel), and **health weights (M29)** can discount a
  node that looks faulty (advanced).
- **Node CUSUM with a replay-tuned threshold (M28).** Accumulate −ln p − 1.5. The threshold h is not taken from a
  formula; it is found by replaying the node network's own quiet "tuning" days and searching (bisection) for the h that
  gives the design rate of one node-local false candidate per node per 30 days. Periods when a quarter of the network
  is elevated at once are left out of that count, because they are common-mode events for the edge to handle.

## 2.7 PRAHARI's edge layer (M30–M35, Phase 6)

- **Clustering (M30):** candidate nodes within R = 1.6 × spacing of each other in the last 30 minutes form a cluster.
- **Spatial common-mode rejection, SCMR (M31):** a fire is local, haze is everywhere. A cluster passes only if the
  share of candidate nodes around it is at least three times the share across the whole network.
- **Fisher combination (M32):** combine the cluster's p-values into one, X = −2 Σ ln pᵢ, which follows a chi-square
  distribution with 2k degrees of freedom when nothing is happening.
- **Prior (M33):** how likely a fire is right now, from people's activity and fuel dryness (legacy: a fixed prior for
  "dry, busy" and "wet, quiet" days).
- **Risk-adaptive quorum, RAQ (M34):** convert the combined p-value into an upper bound on the **Bayes factor**
  (Sellke–Bayarri–Berger bound, 1/(−e p ln p)), multiply by the prior odds, and alarm if the result beats the ratio of
  false-alarm cost to miss cost. In plain terms: on a dry, busy day two agreeing nodes are enough; on a wet, quiet day
  three are needed.
- **Graded escalation (M35):** WATCH → CANDIDATE → CONFIRMED → ESCALATED, each step with a written explanation.

## 2.8 Radio and power (M38–M43, Phase 8)

Nodes talk to a gateway over **LoRaWAN**. Under forest canopy the signal fades fast (about 100 dB of path loss at 200 m,
120 dB at 400 m at 922 MHz). LoRa trades data rate for range with the **spreading factor (SF7–SF12)**: higher SF
reaches farther but keeps the radio on longer. Nodes run on a small solar panel and supercapacitors, so energy per
message matters.

## 2.9 Judging the results fairly (M44–M46)

- **False incidents per month:** alarms close together in time and space are merged into one incident (M46), then
  counted over the test days.
- **Exact Poisson interval (M45):** the 95% interval for a count of rare events.
- **Wilson interval (M44):** the 95% interval for a proportion such as "fires confirmed within 3 hours".
- **Test protocol (M46):** 14 calibration days, 14 tuning days, 30 test days per seed; a quiet pass without fires for
  false alarms and a pass with scripted fires for detection.
- **Overdispersion:** false alarms come in bursts (a haze episode can cause many), so results vary much more from seed
  to seed than a Poisson interval suggests. This is why the project compares distributions over 20 seeds when a
  5-seed result misses a report interval (see [../results/validation.md](../results/validation.md)).
