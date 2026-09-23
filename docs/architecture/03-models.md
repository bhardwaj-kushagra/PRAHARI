# Architecture 3 — the models (M1–M46)

Every equation in [`SPEC.md`](../SPEC.md) §5, where it lives in `engine/prahari/`, and its state after Phase 5.
"Default" is the implementation that `configs/default.yaml` runs. Plain-language explanations are in
[../guide/02-background.md](../guide/02-background.md).

## World and siting (setup, run once)

| M | What it does | File | Default | Since |
| --- | --- | --- | --- | --- |
| M1 | Grid and corridor layouts | `world/siting.py`, `world/geometry.py` | real | Phase 1 |
| M2 | Distance fields to each interface (paths, village, road, power line) | `world/landscape.py`, `world/interfaces.py` | real | Phase 1 |
| M3 | Ignition-likelihood map λ(x, t) from the distance fields | `world/landscape.py` (static), `fire/ignition.py` (with a(t)) | real | Phases 1, 3a |
| M4 | Greedy maximum-coverage siting | `world/siting.py` | real (used when `world.layout: greedy`) | Phase 1 |
| M38 | Path loss and spreading factor per node (no shadowing yet) | `comms/pathloss.py` (`links` module) | real | Phase 1 |

## Environment and fire

| M | What it does | File | Default | Since |
| --- | --- | --- | --- | --- |
| M5 | Diurnal temperature, wind, rain | `env/weather.py` | real | Phase 2 |
| M6 | Relative humidity from dew point (Magnus) | `env/weather.py` | real | Phase 2 |
| M7 | Fine Fuel Moisture Code, verified against cffdrs | `env/ffmc.py` | real | Phase 2 |
| M8 | Sustained-ignition probability from FFMC | `fire/ignition.py` | real | Phase 3a |
| M9 | Legacy source strength (growth ramp) | `fire/growth.py` | stub = legacy model | Phase 0 |
| M10 | Advanced growth | — | not implemented (optional) | — |
| M11, M14, M15 | Gaussian plume, Briggs dispersion, sub-canopy wind | `fire/gaussian.py` | real, opt-in (`plume: real`) | Phase 3b |
| M12, M13, M16 | Legacy exponential-directional plume, directional factor, transport delay | `fire/plume.py` | stub = legacy model (default) | Phase 0 / 3a |

## Sensor signals

| M | What it does | File | Default | Since |
| --- | --- | --- | --- | --- |
| M17 | MOX response (linear, legacy) | `sensors/mox.py` | real | Phase 2 |
| M18 | Composite reading: baseline, drift, cycle, noise, events, haze, fire | `sensors/mox.py` | real | Phase 2 |
| M19 | AR(1) heteroscedastic noise with a heavy tail | `sensors/mox.py` | real | Phase 2 |
| M20 | Nuisance events; regional haze | `sensors/nuisance.py`, `sensors/haze.py` | real | Phase 2 |
| M21 | Faults (stuck, offset, spikes, dropout) | `sensors/faults.py` | stub (none) | Phase 9 |

## Baselines

| M | What it does | File | Default | Since |
| --- | --- | --- | --- | --- |
| M22 | P0 fixed threshold μ + 3σ from day 1 | `detect/baselines/fixed.py` | real | Phase 4 |
| M23 | P1 v1 as written: EWMA z, CUSUM k 0.5, h 8.8, 2 nodes within R | `detect/baselines/v1.py` | real | Phase 4 |
| M23 + M28 | P1t: capped slow z, replay-tuned h | `detect/baselines/v1t.py` | real | Phase 5 |

## PRAHARI node layer

| M | What it does | File | Default | Since |
| --- | --- | --- | --- | --- |
| M24 | Slow EWMA baseline with the 180-minute freeze cap | `detect/prahari/ttc_real.py` (stub: `ttc.py`, v1 without the cap) | real | Phase 5 |
| M25 | Fast residual against the lagged 60–180-minute mean | `detect/prahari/ttc_real.py` | real | Phase 5 |
| M26 | Conformal p-value per node and 4-hour bin | `detect/prahari/qcc_real.py` (stub: Gaussian p in `qcc.py`) | real | Phase 5 |
| M27 | Node score −Σ c ln p | `detect/prahari/score.py` | stub (exact with one channel) | Phase 0 |
| M28 | −ln p CUSUM, k 1.5, replay-tuned h | `detect/prahari/cusum_real.py`, `tuning.py` (stub: v1 CUSUM in `cusum.py`) | real | Phase 5 |
| M29 | Health weight | — | stub (c = 1) | Phase 9 |

## PRAHARI edge layer (Phase 6)

| M | What it does | File | Default |
| --- | --- | --- | --- |
| M30 | Clustering within R over 30 minutes | `detect/prahari/cluster.py` | stub (all candidates in the window form one cluster) |
| M31 | Spatial common-mode rejection | `detect/prahari/scmr.py` | stub (always passes) |
| M32 | Fisher combination | `detect/prahari/fisher.py` | stub (Bonferroni) |
| M33 | Prior from activity and fuel (legacy: day type) | `detect/prahari/srp.py` | stub (constant prior odds from configuration) |
| M34 | Bayes-factor bound and risk-adaptive quorum | `detect/prahari/learn.py` (bound), `raq.py` | stub (fixed quorum 2) |
| M35 | Graded escalation | `detect/prahari/escalate.py` | stub (CONFIRMED when the quorum is met) |
| M36 | Fitted likelihood ratio (learning loop) | `detect/prahari/learn.py` | stub (Phase 9) |

## Satellite, communications, energy (Phases 8–9)

| M | What it does | File | Default |
| --- | --- | --- | --- |
| M37 | Satellite alert time | `satellite/overpass.py` | stub (fixed delay) |
| M39, M40 | LoRa time on air, collisions | `comms/lorawan.py` | stub (perfect link) |
| M41–M43 | Energy budget, solar harvest, supercapacitor | `energy/budget.py` | stub (infinite energy) |

## Evaluation

| M | What it does | File |
| --- | --- | --- |
| M44 | Wilson interval | `eval/stats.py` |
| M45 | Exact Poisson interval | `eval/stats.py` |
| M46 | Incident merging, detection rule, test protocol | `eval/stats.py`, `eval/experiments.py` |

## Where each model's numbers come from

Every parameter block in `configs/default.yaml` carries a `source` string. Examples: `ffmc` is LIT (Van Wagner, as
implemented in cffdrs); the sensor, nuisance and haze parameters are ASM matched to the report's simulation;
`cusum.h_default` is DER (mean tuned h of the report's simulation on the golden seeds); `evaluation` targets are TGT
(the SPEC's acceptance criteria). The dashboard's model card shows each module's equation, tag, state and notes.
