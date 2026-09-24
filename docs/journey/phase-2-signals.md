# Phase 2 — Weather, fuel moisture and sensor signals

## Goal

Make the sensor streams realistic enough that detection is genuinely hard: weather with daily cycles, a verified
fuel-dryness index, and sensor readings with drift, autocorrelated noise, nuisance spikes and regional haze.

## What was built

- `weather` (M5, M6): diurnal temperature, humidity from dew point, wind, rain events.
- `ffmc` (M7): the daily Fine Fuel Moisture Code, verified against the official cffdrs outputs.
- `sensor` (M17–M19), `nuisance` and `haze` (M20), with scenario-scriptable haze episodes.
- Dashboard **Signals** tab: weather strip, haze level, one node's reading with haze bands, eight nodes as small
  multiples.
- Scenario `signals_3day`.

## How it works

Each reading is built from a drifting baseline, a daily cycle, AR(1) noise with a heavier daytime component and a
heavy tail, random nuisance spikes (more at roadside nodes), and haze episodes that raise every node together. The
signal parameters match the report's simulation so that golden comparisons stay possible.

## Challenges and issues

1. **The FFMC formula in the specification was slightly wrong.** With the moisture constant 147.2, the daily chain
   drifted up to 0.12 FFMC away from cffdrs over 48 days, beyond the 0.1 tolerance.
2. **A verification dataset was needed** for M7 without adding a dependency.
3. **Weather random walks drift away** over 58-day experiments.
4. **The stub detectors flooded.** With realistic signals the Phase 0 CUSUM stub raised about 2,000 candidates a day
   and the haze episode lit the whole network.
5. **Recording size.** A week-long recording with that flood was 11 MB compressed and 65 MB raw.

## Decisions and trade-offs

| Decision | Pros | Cons |
| --- | --- | --- |
| Use cffdrs's constant 147.27723 and record erratum E-6 | matches cffdrs to 0.005 | a SPEC change |
| Ship cffdrs's published test outputs as a fixture with provenance (P2-1) | real verification, no dependency | a data file under GPL-2 provenance (numbers only) |
| Mean-reverting daily weather instead of a pure random walk (P2-2) | stable over long runs | an assumption (ASM) |
| Match signal parameters to the report's simulation (P2-3) | golden comparability | the signal model inherits the report's assumptions |
| Framework scenarios keep stub signals (P2-4) | their fires stay readable | two kinds of scenario to explain |
| Leave the flood visible in `signals_3day`; do not patch the stub (P2-4) | it *is* the report's P1 failure, a useful demo; accepted Phase 0 code untouched | a noisy recording until Phase 5 |
| Three days instead of a week (P2-5) | 5.6 MB, loads fast | fewer days shown |
| ECharts loaded only when the Signals tab opens (P2-6) | the map stays light | a short load on first open |

A trial fix to the TTC stub's warm-up did not reduce the flood materially and was reverted, keeping the accepted
Phase 0 file unchanged.

## Resolution

The FFMC issue was fixed and verified. The flood was left as a documented, expected behaviour; the real node layer
(Phase 5) removed it: `signals_3day` shrank from 5.9 MB to 2.3 MB when the real TTC, QCC and CUSUM took over.

## Acceptance results

| Test | Result (SIM) |
| --- | --- |
| AR(1) lag-1 correlation 0.95 ± 0.02 | pass |
| Nuisance counts within Poisson 95% bounds | pass (roadside and interior groups) |
| M6: RH at 30 °C with dew point 10 °C | 28.9% (expected ≈ 29%) |
| M7 against cffdrs | max error 0.005 over 48 days (tolerance 0.1) |

## What to show

`signals_3day`, *Signals* tab: daily cycles, FFMC, the haze band on day 2; click through nodes to see how different
roadside and interior nodes look.
