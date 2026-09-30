# Real-data analysis plan — Thompson et al. (2026) N5 networks (exploratory, REAL)

**Status.** Written and committed **before** the analysis runs. It is exploratory: it has no hypothesis test and
fixes no simulation parameter by itself. Any value later carried into protocol R2 is tagged `DATA` and cites the
result file.

**Data:** `data/real/thompson2026/` (public, MIT). April 2024, 40 N5 sensors, PM₂.₅ every 5 minutes.

## Questions

1. **Common-mode events in real low-cost sensor networks.** How often do many stations of a network rise together? For
   how long? With what onset spread across stations, and what spread in amplitude? At what time of day? Could a
   recorded fire explain them?
2. **The floor on real data.** When PRAHARI's node layer runs on real PM₂.₅, what share of the node-level candidates in
   quiet data fall inside network-wide (common-mode) events?

## Networks

Four clusters have at least five stations: **WR** (Wainwright, AB; UTC−6 in April), **BC** (Quebec; UTC−4), **VC**
(Valcartier, QC; UTC−4) and **RC** (Rock Creek, BC; UTC−7). MR (3 stations) and KM (2) are excluded. Station
spacings are reported from `Sensor_Locs.csv`; they are kilometres, not the design's 70 m.

## Preprocessing

- **Grid:** each station's readings go onto a 5-minute grid (Unix time floored to 300 s; mean within a bin).
- **Gaps:** gaps of at most three bins are carried forward; longer gaps are missing, and the station is inactive
  there.
- **Channel:** y = ln(1 + PM₂.₅ [µg/m³]).
- **Inactive stations** count in no share at those ticks.

## Common-mode events (questions 1 and 2)

**Per-station deviation (causal):**

- Baseline: the rolling median of y over the previous 24 h, requiring at least 12 h of data.
- Scale: 1.4826 × MAD over the same window, floored at 0.05.
- z = (y − median) / scale. A station is *elevated* at z ≥ 3 (the M28 convention).

**Network share:** f(t) = elevated stations / active stations. Ticks with fewer than five active stations are
undefined.

**Event** (all thresholds fixed here):

1. The *core* is a run of f ≥ 0.5 lasting at least 3 ticks (15 min).
2. The *span* extends the core while f ≥ 0.25.
3. Spans less than 60 minutes apart merge.

**Per event, recorded:**

- start and end (UTC and local time) and duration;
- the share of active stations elevated at any tick of the span;
- the onset spread: the latest minus the earliest first-elevated tick among involved stations;
- the peak excess per involved station, as max(PM₂.₅) − its baseline median PM₂.₅ in µg/m³, reported as the median
  and the coefficient of variation across stations.

**Fire attribution (WR only):** an event is *fire-attributed* when a recorded WR fire (`WainwrightApr2024.csv`,
UTC−7) ignited within 20 km of the network, between 6 h before the event starts and its end. Otherwise it is
*unattributed*. The other clusters have no fire records; their events are reported as *unattributed (no records)*.

**Local excursions:** runs of at least 3 ticks in which exactly one station is elevated while f < 0.25. They are
counted per station-day as the single-station nuisance rate.

## Node-layer replay (question 2)

PRAHARI's node layer runs on y with the release-1.0 parameters, converted from minutes to 5-minute ticks:

| Stage | Setting |
| --- | --- |
| M24 slow baseline | 720 min (144 ticks), freeze at \|z\| ≥ 3, cap 180 min (36 ticks) |
| M25 fast residual | minus the mean of ticks t−36 … t−13 (the 180–61-minute lag) |
| M26 conformal p-values | six 4-hour time-of-day bins, from the calibration days |
| M28 CUSUM | on −ln p with k = 1.5, 30-minute refractory period (6 ticks) |

**Days:** the first 7 days calibrate, the next 7 tune, and the rest are the test period. Stations with fewer than 5
test days are dropped.

**Tuning:** h is replay-tuned per station to 1 node-local false candidate per node per 30 days. Common-mode ticks are
excluded exactly as M28 does: f ≥ 0.25 on the elevated-station share, padded by ±60 minutes.

**Reported on the test days:**

- candidates per node per 30 d;
- the share of candidates starting inside common-mode periods (f ≥ 0.25, and the event spans), with WR's
  fire-attributed periods reported separately;
- the achieved exceedance at a nominal 1% outside common-mode periods, as a calibration check.

## Outputs

- **`results/research/real_thompson2026.json`:** events, per-cluster rates, the node-replay decomposition, station
  spacings.
- **`docs/research/realdata.md`:** the write-up, with REAL labels.
- **Protocol R2:** event statistics carried into it become `DATA` parameters (event rate, duration, onset spread,
  amplitude spread and station share), with conversion to 70 m spacing stated as an assumption (`ASM`).

## Addendum B — a dense sub-kilometre network (Sensor.Community, Stuttgart)

**Status.** Written and committed before any Stuttgart data are fetched or analysed. Exploratory.

**Why.** The N5 networks are kilometres apart and had few regional events in April 2024. A dense urban low-cost PM
network gives common-mode statistics nearer the design's 70 m scale. Its events are regional PM episodes: inversions,
dust, smoke, and humidity artefacts of low-cost optical sensors. They are not specifically wildfire smoke; this
network is an analogue, not a validation.

**Data.** Sensor.Community open archive (`archive.sensor.community`), licence ODbL 1.0.

- Period: **1–31 October 2024**.
- Sensors: outdoor SDS011 PM sensors within **2.0 km** of Stuttgart centre (48.7758° N, 9.1829° E), located from the
  archive's own daily files.
- Selection: sensors with readings on at least 90% of the 5-minute bins. The 30 nearest to the centre are used, or
  all if fewer.
- The station list is saved with the results.

**Method.** The same as the N5 analysis:

- the 5-minute grid, and y = ln(1 + PM₂.₅) with PM₂.₅ = the SDS011 `P2` field;
- the rolling 24-hour robust z, the network share, the event definition (core ≥ 0.5 for 15 minutes, span ≥ 0.25,
  merge within 60 minutes) and local excursions;
- the node-layer replay with 7 calibration days, 7 tuning days and the rest as test days, at the M28 target of 1 per
  node per 30 days.
- Local time is UTC+2 until 27 October and UTC+1 after; bins use UTC+2 throughout, a documented approximation.
- No fire attribution is attempted.

**Outputs:** `results/research/real_sensorcommunity_stuttgart.json` and a section in `docs/research/realdata.md`.
