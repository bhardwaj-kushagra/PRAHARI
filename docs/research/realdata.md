# Real data — N5 networks (Canada), Stuttgart and north-west India (REAL, exploratory)

**Data:** Thompson, Fusina & Jackson, *Fire* 9(4):141 (2026); archive
[doi:10.5281/zenodo.18222779](https://doi.org/10.5281/zenodo.18222779) (MIT licence). Provenance:
[data/real/thompson2026/README.md](../../data/real/thompson2026/README.md).

**Plan:** [realdata-plan.md](realdata-plan.md), committed before this analysis ran.

**Numbers:** every number below is REAL, from `results/research/real_thompson2026.json`, produced by
`python -m prahari.research realdata`.

**Channel and geometry.** The channel is PM₂.₅ (the N5 gas score is zero almost everywhere). The stations are
kilometres apart, against the design's 70 m, so these networks are an *analogue* of the design, not a copy.

## 1. Networks

Four site clusters, April 2024, one reading every 5 minutes:

| Cluster | Stations | Days with ≥ 5 active | Spacing, km (min / median / max) |
| --- | --- | --- | --- |
| WR (Wainwright, AB) | 10 | 30.0 | 0.97 / 5.28 / 16.21 |
| BC (Quebec) | 10 | 30.0 | 0.40 / 7.20 / 16.91 |
| VC (Valcartier, QC) | 10 | 23.3 | 1.75 / 6.42 / 15.68 |
| RC (Rock Creek, BC) | 6 | 19.3 | 0.41 / 1.72 / 4.13 |

## 2. Common-mode events

These are the plan's definition: at least half the active stations at z ≥ 3 for 15 minutes or more.

| Cluster | Events | Start (local) | Duration | Stations involved | Onset spread | Peak excess (median) | Amplitude CV | Attribution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WR | 1 | 23:00 | 110 min | 100% | 100 min | 50 µg/m³ | 0.94 | fire WR-07 (ignited 23:06) |
| BC | 0 | — | — | — | — | — | — | — |
| VC | 2 | 05:00, 12:00 | 85, 355 min | 88%, 78% | 35, 15 min | 4, 8 µg/m³ | 0.25, 0.28 | no fire records |
| RC | 1 | 13:00 | 20 min | 50% | 5 min | 4 µg/m³ | 0.34 | no fire records |

**Reading:**

- **Unattributed network-wide events were rare in April 2024:** three in about 72 cluster-days, or 0–0.09 per day.
  The simulator's default haze rate is 0.1 a day. The paper's June 2023 regional-smoke episode is not in the public
  release.
- **Where they occur, they are near-synchronous and fairly even.** They involve 78–88% of stations, with onsets
  spread 15–35 minutes across networks about 6 km wide, and an amplitude CV of 0.25–0.28.
  - At 70 m spacing the same front would arrive almost simultaneously.
  - The spread across stations is close to the simulator's node-gain spread (σ = 0.2).
- **The one fire-attributed event (WR-07) is uneven:** CV 0.94, with a 100-minute onset spread as the smoke moved
  across the network.
- **Single-station excursions** occur 0.41–0.52 times per station-day (WR, BC, VC) and 1.23 at RC.

Three unattributed events are too few to fit distributions. Any value carried into protocol R2 is tagged `DATA` with
wide ranges, and the conversion from kilometres to 70 m is stated as an assumption.

## 3. PRAHARI's node layer on real PM₂.₅

**Set-up:**

- The node layer runs with the release-1.0 settings converted to 5-minute ticks.
- 7 days calibrate and 7 days tune, with h replay-tuned to 1 false candidate per node per 30 days.
- The remaining days are the test period.

| Cluster | Test days | Candidates / node / 30 d | Exceedance at nominal 1% (outside common mode) | Share of candidates while ≥ 25% of stations are elevated |
| --- | --- | --- | --- | --- |
| BC | 16.0 | 0.19 | 1.56% | 0% |
| VC | 16.0 | 1.69 | 0.42% | 22% |
| RC | 5.4 | 0.00 | 1.11% | — |
| WR | 16.0 | 6.38 (all within 24 h of a recorded fire; 0.00 outside) | 1.18% | 71% |

**Reading:**

- **Node calibration carries over to real data.** On the quiet networks (BC, VC, RC), node-level false candidates are
  0–1.7 per node per 30 days against a target of 1. Exceedance is 0.4–1.6% at a nominal 1%.

  This is the first half of the paper's decomposition, "node calibration meets its budget", seen on real sensors.
- **At Wainwright every candidate is real smoke.** All 34 fall within 24 hours of a recorded ignition within 20 km.

  71% of them came while at least a quarter of the stations were elevated. At kilometre spacing, a real fire's smoke
  itself looks common-mode, so a common-mode gate tuned for regional haze can also hide real fires. The simulator's
  70 m network puts that trade-off in a different place; protocol R2 should report fires that overlap haze separately.
- **Too few regional-smoke events in this month** to measure the common-mode floor on real data. The floor stays a
  SIM result. The real data support its premise (calibrated nodes, rare but synchronous common-mode events), not its
  size.

## 4. A dense sub-kilometre network: Sensor.Community, Stuttgart (addendum B)

**Data:** Sensor.Community open archive (ODbL 1.0), October 2024.

**Selection:**

- 28 outdoor SDS011 sensors were shortlisted within 3 km of the centre; 21 of them had archive files.
- The selection keeps sensors whose October 2024 location lies within 2.0 km and whose readings cover at least 90% of
  the 5-minute bins. **9 sensors**, 0.49–3.06 km apart (median 1.70).
- Sensor 850 was excluded: its October 2024 files place it about 316 km away, so it has moved since.

Source: `results/research/real_sensorcommunity_stuttgart.json`.

| Quantity | Value (REAL) |
| --- | --- |
| Common-mode events (plan definition) | 7 in 31 days (0.23 per day) |
| Start (local) | 23, 01, 06, 22, 08, 07 and 20 h: six of seven between 20:00 and 08:00 |
| Duration (10th / 50th / 90th percentile) | 68 / 80 / 277 min |
| Stations involved | 67–89% (median 78%) |
| Onset spread across stations | 15–140 min (median 40) |
| Amplitude CV across stations | 0.18–2.49 (median 0.42) |
| Single-station excursions | 0.62 per station-day |
| Node layer: candidates / node / 30 d | 0.00 over 17 test days |
| Node layer: exceedance at nominal 1% | 1.32% |

**Reading:**

- **Night-time pooling.** At sub-kilometre spacing, network-wide events are about three times more frequent than in
  the N5 networks, and they are mostly nocturnal: inversions trapping particles near the ground.
- **Slow, uneven development.** Onsets spread 15–140 minutes across a network only 1.7 km across, and amplitudes vary
  widely between stations (median CV 0.42). This is not a fast front. Real common-mode events at small spacing are
  *less* synchronous and *less* even than the simulator's haze.
- **Calibration holds.** The node layer again stays within its false-candidate budget: 0 candidates, and exceedance
  1.3% at a nominal 1%.

**Consequence for R2 (recorded in `protocol-r2.md` §7 before registration):** the haze scenarios widen three ways,
because the real events are uneven:

- per-node onset jitter;
- night-weighted episode starts;
- a per-episode spread of node amplitudes.

## 5. North-west India, crop-residue season (addendum C)

**Plan:** [realdata-plan.md](realdata-plan.md) addendum C, committed (`f08c5b4`) before any Indian measurement was
fetched. **Numbers:** every number here is REAL and comes from `results/research/real_india.json`, produced by
`python -m prahari.research realdata-india`. **Role:** a held-out check of R2's registered haze model M20b, which no
Indian data helped to set. **Nothing in R2 changes because of it.**

**Data:**

| Cluster | Source | Licence | Seasons (1 Oct–30 Nov) | Cadence |
| --- | --- | --- | --- | --- |
| AK | Aakash project (RIHN): low-cost CUPI-G stations, Punjab to Delhi | CC BY-NC-ND 4.0 | 2022, 2023, 2024 | 1 h |
| DL | CPCB stations within 25 km of central Delhi, Princeton archive (Sharma & Mauzerall 2021) | CC BY 4.0 | 2017, 2018, 2019 | 1 h |
| DL15 | The same kind of CPCB stations through OpenAQ | None listed by OpenAQ; used at the developer's decision (DECISIONS P-9) | 2025 | 15 min |

Raw data are not redistributed. Implementation notes are in DECISIONS P-10:

- AK has no file coordinates, so it has no front fit, and its observation operator uses the Singh et al. (2023)
  Table S1 layout.
- Two Princeton files with an ambiguous PM₂.₅ column are excluded.
- Ashok Vihar's file coordinates are used as given, so it falls outside the radius.

### 5.1 Common-mode events and the held-out comparison

The table gives, per cluster-year:

- stations (median spacing);
- events over days with ≥ 5 active stations;
- events per day, with the multiplier on H-mix's 0.1 per day;
- night share (Wilson 95%);
- the median amplitude CV, with the M20b observation operator's 5–95% interval in brackets;
- the median onset spread in minutes, with the operator's interval;
- the median duration in minutes.

| Cluster-year | Stations | Events | Per day | Night share | Amplitude CV [operator] | Onset spread, min [operator] | Duration, min |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AK-2022 | 23 (157.15 km) | 0 / 61.0 d | 0.0 (×0) | — | — [0.276–0.738] | — [420.0–4320.0] | — |
| AK-2023 | 23 (157.15 km) | 0 / 61.0 d | 0.0 (×0) | — | — [0.273–0.735] | — [420.0–4320.0] | — |
| AK-2024 | 24 (157.15 km) | 1 / 61.0 d | 0.016 (×0.16) | 1.0 (0.207–1.0) | 0.382 [0.277–0.74] | 240.0 [420.0–4320.0] | 480.0 |
| DL-2017 | 5 (21.16 km) | 1 / 38.92 d | 0.026 (×0.26) | 1.0 (0.207–1.0) | 0.089 [0.098–0.684] | 120.0 [0.0–300.0] | 300.0 |
| DL-2018 | 31 (16.5 km) | 2 / 61.0 d | 0.033 (×0.33) | 1.0 (0.342–1.0) | 0.192 [0.272–0.738] | 120.0 [60.0–420.0] | 390.0 |
| DL-2019 | 36 (17.93 km) | 2 / 61.0 d | 0.033 (×0.33) | 1.0 (0.342–1.0) | 0.242 [0.28–0.743] | 150.0 [60.0–480.0] | 330.0 |
| DL15-2025 | 45 (15.85 km) | 1 / 57.24 d | 0.017 (×0.17) | 0.0 (0.0–0.793) | 0.265 [0.287–0.736] | 75.0 [75.0–510.0] | 210.0 |

**Pooled per cluster:**

| Cluster | Events per day | Night share (Wilson 95%) |
| --- | --- | --- |
| AK | 0.005 (×0.05) | 1.0 (0.207–1.0) |
| DL | 0.031 (×0.31) | 1.0 (0.566–1.0) |
| DL15 | 0.017 (×0.17) | 0.0 (0.0–0.793) |

**Front fits:** only one event had a plane fit with R² ≥ 0.5 (DL 2017). Its apparent speed,
4.099 m/s, lies inside the registered 1–6 m/s.

**Why events are rare (diagnostics; exploratory, added after the first run):**

- Stations are elevated (z ≥ 3) on 1.4–1.8% of station-ticks (0.0144–0.0176).
- The robust within-day scale is large: 0.278–0.353 in ln(1 + PM₂.₅), roughly ±30–40%.
- The network share reaches 0.5 on only 0–7 ticks per season.

The seasonal smoke rise builds over days and is absorbed by the 24-hour baseline. Network-wide *sharp* rises are rare.

### 5.2 Gas channel (AK, CO)

| Season | CO stations | CO events | Per day | Night share | PM events overlapping a CO event | CO events overlapping a PM event |
| --- | --- | --- | --- | --- | --- | --- |
| AK-2022 | 7 | 3 | 0.06 | 0.0 | — (no PM events) | 0.0 |
| AK-2023 | 17 | 1 | 0.016 | 0.0 | — (no PM events) | 0.0 |
| AK-2024 | 9 | 5 | 0.09 | 0.8 | 1.0 | 0.2 |

**September pre-season (AK, descriptive only):**
AK-2022: 0 events, 22 stations; AK-2023: 0 events, 12 stations; AK-2024: 0 events, 16 stations.

### 5.3 PRAHARI's node layer on 15-minute Delhi data (DL15, 2025)

Calibration ran on 17–23 Sep and tuning on 24–30 Sep, with the target of 1 per node per 30 days. The test period was
1 Oct–30 Nov.

| Quantity | Value (REAL) |
| --- | --- |
| Nodes | 45 |
| Test days | 61.0 |
| Candidates per node per 30 d | 1.41 |
| Exceedance at a nominal 1% (outside common mode) | 0.0163 |
| Share of candidates while ≥ 25% of stations are elevated | 0.031 |
| Share of candidates inside event spans | 0.039 |
| Time share of common-mode periods in the test | 0.007 |

### 5.4 Provenance check (OpenAQ against Princeton, CPCB, Oct–Nov 2017)

5 stations matched within 1 km. Over 3731 station-hours, the median absolute relative difference
between OpenAQ's hourly means of 15-minute values and Princeton's hourly values is 0.0764.
Per station: ITO 0.0651, DTU 0.0903, Shadipur 0.084, Faridabad 0.1704, Punjabi Bagh 0.0.

### 5.5 Reading (REAL; descriptive, with small event counts)

- **Rate.** In all three networks, network-wide rises in October–November occur **less often** than the simulator's
  1 per 10 days: ×0.05–×0.31 of the H-mix rate.
  - Measured against a 24-hour baseline, the crop-residue smoke season is a slow regional build-up, not a series of
    sharp episodes.
  - By this measure, R2's haze rate is a *stress* setting, not an underestimate.
- **Unevenness.** Where events occur, their amplitude CV mostly falls **below** the operator's interval: real events
  are more even across stations than M20b draws.
- **Onset spreads.** Delhi's (DL, DL15) fall inside the operator's interval. AK's single event (240 min across a
  470 km network) is below it: more synchronous than M20b's 1–6 m/s fronts would be at that scale.
- **Night.** All 5 DL events start at night, consistent with the registered 0.7 (pooled Wilson interval
  0.566–1.0). The single DL15 event starts by day.
- **Node layer.** It stays near its budget in the smoke season (1.41 per node per 30 d
  against a target of 1). Only 0.031 of its candidates fall in common-mode periods, against 71% at
  Wainwright, where the candidates were nearby fire smoke.
- **Gas channel.** CO events are of the same order as PM events, and the one PM event of 2024 coincided with a CO
  event. Counts are too small for more.
- **Limits:**
  - PM₂.₅ and CO, not MOX;
  - hourly cadence for AK and DL;
  - kilometre to regional spacing;
  - 1–5 events per cluster, so every comparison is descriptive;
  - DL15's licence is not listed;
  - Pusa IMD and Pusa DPCC are two monitors at the same site, both included;
  - no fire attribution.

## Additions to the plan (labelled)

For WR, the share of candidates within 24 hours after a recorded ignition within 20 km is also reported, together with
the candidate rate outside those windows. The plan's fire attribution applied only to network-wide events, and WR's
test days contain six recorded fires (WR-11 to WR-16).

Nothing in the plan's definitions was changed after seeing the results.

## Limits

- One spring month, with no regional-smoke episode in the public data.
- PM₂.₅, not the MOX gas channel.
- Kilometre spacing.
- Fire records exist for Wainwright only.
- Unrecorded agricultural or residential burning elsewhere cannot be excluded.
