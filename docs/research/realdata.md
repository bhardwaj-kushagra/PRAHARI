# Real data — Thompson et al. (2026) N5 smoke-sensor networks (REAL, exploratory)

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
