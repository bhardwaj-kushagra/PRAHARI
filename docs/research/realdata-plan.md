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

## Addendum C — north-west India, crop-residue season (three networks)

**Status.** Written and committed on 1 Oct 2026, before any Indian measurement is fetched or analysed. Exploratory,
with no hypothesis test. Only station metadata (positions, sensor date ranges, licences) was read beforehand; the
OpenAQ shortlist is committed with this addendum (`data/real/openaq_cpcb_delhi/shortlist.json`).

**Role.** A **held-out check** of R2's registered haze model M20b (protocol R2 §2, `configs/research/r2.yaml`).
- R2 was registered (`a24bfbd`) before any Indian measurement was seen, so these data set no R2 parameter (charter
  rule 7).
- **Nothing in R2 changes because of this analysis.** Discrepancies are reported as limitations and carried to a
  future round.

**Questions.**

1. How often do network-wide PM₂.₅ rises occur in north-west India in October–November, compared with the simulator's
   1 per 10 days?
2. Do their timing, unevenness, coverage, onset spread and front speed fall inside the registered H-mix ranges?
3. Does a gas channel (CO) show the same common-mode structure?
4. On 15-minute data, what share of PRAHARI's node-level candidates in the smoke season falls inside network-wide
   periods?

### Networks and licences

| Cluster | Source | Licence | Window | Cadence |
| --- | --- | --- | --- | --- |
| **AK** | Aakash project, RIHN: 32 CUPI-G low-cost stations, Punjab to Delhi; PM₂.₅ and CO | CC BY-NC-ND 4.0 | 1 Oct–30 Nov 2022, 2023, 2024 (primary); 1–30 Sep of each year (pre-season, descriptive only) | 1 h |
| **DL** | CPCB stations, Princeton archive (Sharma & Mauzerall 2021, doi:10.34770/60j3-yp02) | CC BY 4.0 | 1 Oct–30 Nov 2017, 2018, 2019 | 1 h |
| **DL15** | CPCB stations through the OpenAQ v3 API | None listed by OpenAQ (checked 1 Oct 2026); used at the developer's decision of 1 Oct 2026 (DECISIONS P-9) | 1 Oct–30 Nov 2025 (events), fetched from 17 Sep 2025 | Native (15 min expected) |

**Licence conditions:**

- **No redistribution.** No raw or modified series is committed or shared, from any of the three sources. Raw files
  stay under `data/real/<dataset>/raw/` (gitignored), with committed manifests.
- **Credits:** RIHN Aakash; Sharma & Mauzerall (Princeton); CPCB with OpenAQ.

**Why the seasons differ.** OpenAQ's Delhi CPCB sensors have date ranges ending in February 2018 or starting in
February 2025, with none spanning the 2023 or 2024 seasons. So DL15 uses 2025, and DL (Princeton, licence-clean)
covers 2017–2019.

**Station selection:**

- **DL and DL15:** CPCB PM₂.₅ stations within **25 km of 28.6129° N, 77.2295° E**.
  - *DL15:* per location, the PM₂.₅ sensor whose own date range spans the window. If several do, the lowest id; if
    none, the location is skipped.
  - *DL:* the Princeton `Delhi*` files and the NCR-district files, kept when their coordinates fall within the radius.
- **AK:** every station in the files.
- **Inclusion (all clusters):**
  - a station enters a cluster-year with valid values on ≥ 75% of the window's ticks;
  - a cluster-year is analysed with ≥ 5 stations.

**Provenance check (no statistic uses it).** The 10 OpenAQ locations whose older sensor spans 1 Oct–30 Nov 2017 are
fetched for that window and matched to Princeton DL stations (same CPCB station, within 1 km). The median absolute
relative difference of their hourly means is reported.

### Preprocessing

- **Time:**
  - Indian sources report IST (UTC+5:30), and times are read as given; a file's own statement of its time zone
    governs.
  - OpenAQ values are placed at their period start (`period.datetimeFrom.utc`).
  - Night is 20:00–08:00 IST.
- **Channel:** y = ln(1 + PM₂.₅ [µg/m³]); for AK's CO, y = ln(1 + CO) in the file's unit.
- **Quality control:**
  - values < 0 become 0;
  - non-numeric values are missing;
  - identical consecutive values lasting ≥ 6 h are missing (stuck instruments; the same in time at every cadence).
- **Grid:** the cluster's cadence; DL15 uses the native `period.interval`.
  - Gaps of ≤ 15 min are carried forward: none at 1 h, 1 bin at 15 min.
  - Longer gaps are missing.
- **Baselines** start from the first data before the window (AK from 1 Sep, DL from 1 Sep, DL15 from 17 Sep), so the
  24 h baseline is warm on 1 Oct. Only events starting inside the window count.
- **Coordinates:** spacings come from the files' coordinates. If AK's files lack coordinates, the station table of
  Singh et al. (Sci Rep 2023) is used. If neither exists, AK's front fit is skipped.

### Events

As in the plan, with durations kept in minutes:

- rolling 24 h robust z, with ≥ 12 h valid;
- elevated at z ≥ 3;
- ≥ 5 active stations;
- **core** f ≥ 0.5 for ≥ 15 min: 1 tick at 1 h, 1 tick at 15 min;
- **span** f ≥ 0.25;
- **merge** spans less than 60 min apart: contiguous at 1 h, 4 ticks at 15 min;
- local excursions as defined.

**Per event:** the plan's statistics (start, duration, share involved, onset spread, and the median and CV of peak
excess), plus:

- **Front fit** (events with ≥ 5 involved stations):
  - a least-squares plane t_i = t₀ + s·x_i, where t_i is the first elevated tick and x_i the station position in km
    on a local tangent plane;
  - it gives the apparent speed 1/|s| (m/s), the direction, the residual SD (min) and R²;
  - at 1 h, quantisation alone gives a residual SD of about 17 min.
- **CO (AK):** the same catalogue on CO, with the share of PM events whose span overlaps a CO event, and the reverse.

### Held-out comparison with the registered H-mix model

**Observation operator:**

- For each cluster-year, 10,000 episodes are drawn from the **unchanged registered class**
  `prahari.sensors.haze.M20b`. Its parameters are `r2.yaml`'s `m20b` block with H-mix's (empty) overrides, applied to
  the cluster's station coordinates.
- Randomness: stream `research` of `make_rngs(20261003)`.
- **Parameter mapping:**
  - scale-free parameters are kept: σ_g, s_e, coverage f;
  - physical parameters are kept: front speed (m/s), jitter (min), and the 200 m gain correlation, under which gains
    are independent at these spacings;
  - the swath width uses the cluster's own span (`network_width_m` unset) instead of 630 m.
- **Per drawn episode:**
  - stations with coverage c ≥ 0.5 count as involved;
  - the CV across involved stations of g·u·c;
  - the onset spread of their delays, floored to the cluster's tick;
  - the share involved.

**Comparisons:**

| Quantity | Registered reference | Indian estimate | Reading |
| --- | --- | --- | --- |
| Event rate per day | H-mix 0.1; R1 dose–response 0–0.6 | Events per day with ≥ 5 active stations | Multiplier on the default rate |
| Night share | 0.7 | Pooled share with a Wilson 95% interval | Inside if the interval contains 0.7 |
| Amplitude CV | Operator's 5–95% interval | Median, and share of events inside | — |
| Onset spread | Operator's 5–95% interval | Median, and share of events inside | — |
| Share involved | Operator distribution; P(f = 1) = 0.5 | Share of events with ≥ 90% involved | The ≥ 0.5 core truncates the real values |
| Front speed | 1–6 m/s | Share of fits with R² ≥ 0.5 inside the range (all fits listed) | — |
| Duration | 300–840 min (trapezoid plus ramps) | Share of event spans inside | Span and trapezoid differ in definition |

**Bias stated in advance:** real CV and onset spread also contain measurement noise and local sources, so they are
biased upward relative to the model.

### Node-layer replay (DL15 only)

- **Settings:**
  - release settings converted to the native tick, as for N5 and Stuttgart;
  - six 4-hour conformal bins (112 calibration values per bin per week at 15 min, minimum p 0.0088);
  - M28 k = 1.5, a 30-minute refractory period and 60-minute padding.
- **Days:** calibration on 17–23 Sep 2025 and tuning on 24–30 Sep 2025 (target 1 per node per 30 d). The test is
  1 Oct–30 Nov 2025, before and into the smoke season, as a deployed network would face it.
- **Reported:**
  - candidates per node per 30 d;
  - exceedance at a nominal 1% outside common mode;
  - the shares of candidates while ≥ 25% of stations are elevated and inside event spans.
- **Not run at 1 h (AK, DL).** The 4-hour bins would hold at most 28 calibration values per week and the p-values
  could not go below 0.034, so nominal levels could not be reached. If DL15's native interval turns out to be 1 h,
  the same rule applies to it.

### Outputs

- `results/research/real_india.json`, with REAL labels. No per-station series are included.
- `docs/research/realdata.md` §5.
- `numbers.md` rows.
- DECISIONS P-9.

**Fetch scripts** (committed with this addendum, run after it): `scripts/fetch_aakash.py`,
`scripts/fetch_cpcb_princeton.py`, and `scripts/fetch_openaq_cpcb.py` (`shortlist` already run for metadata; then
`fetch` and `provenance`).
