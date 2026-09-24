# Architecture 3 — the models (M1–M46)

Every equation in [`SPEC.md`](../SPEC.md) §5, where it lives in `engine/prahari/`, and its state after Phase 9.
"Default" is the implementation that `configs/default.yaml` runs. Plain-language explanations are in
[../guide/02-background.md](../guide/02-background.md).

## World and siting (setup, run once)

| M | What it does | File | Default | Since |
| --- | --- | --- | --- | --- |
| M1 | Grid and corridor layouts | `world/siting.py`, `world/geometry.py` | real | Phase 1 |
| M2 | Distance fields to each interface (paths, village, road, power line) | `world/landscape.py`, `world/interfaces.py` | real | Phase 1 |
| M3 | Ignition-likelihood map λ(x, t) from the distance fields; lightning term λ_light from scripted storms (Poisson strikes over a disc) | `world/landscape.py` (static), `fire/ignition.py` (with a(t) and storms) | real (no storms by default) | Phases 1, 3a, 9 |
| M4 | Greedy maximum-coverage siting | `world/siting.py` | real (used when `world.layout: greedy`) | Phase 1 |
| M38 | Path loss and spreading factor per node; shadowing X_σ and TS011 relays when `links.shadowing_sd_db` > 0 (Phase 8 scenarios: 6 dB) | `comms/pathloss.py` (`links` module), `comms/lora.py` | real (σ = 0 by default) | Phase 1, 8 |

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
| M21 | Faults (stuck, offset, spikes, dropout) at the SPEC rates, or scripted; a dropout holds the last value and marks it missing | `sensors/faults_real.py`; `faults.py` (none) | stub; real in `sensor_fault` | Phase 9 |

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
| M27 | Node score −Σ c ln p | `detect/prahari/score.py`; with M29 weights `score_real.py` | stub (exact with one channel and c = 1) | Phases 0, 9 |
| M28 | −ln p CUSUM, k 1.5, replay-tuned h | `detect/prahari/cusum_real.py`, `tuning.py` (stub: v1 CUSUM in `cusum.py`) | real | Phase 5 |
| M29 | Health weight: fresh data, not stuck (rolling variance), neighbour consensus; c < 0.1 means the sensor abstains | `score_real.py` | stub (c = 1); real in `sensor_fault` | Phase 9 |

**Legacy ablation forms (Phase 7 follow-up, `DECISIONS.md` P7-12).** To reproduce the report simulation's two
node-layer ablations, three parameters switch a node stage into that simulation's variant; every default leaves the
design above unchanged:

| Parameter | Effect | Used by |
| --- | --- | --- |
| `ttc.detect_on: slow` | the detection residual is the capped slow z (M24) instead of the fast residual (M25) | P2 minus TTC |
| `qcc.form: robust_z` | no ranks: z = (r − median) / (1.4826 · MAD) per node over the calibration days, p = Φ(−z) | P2 minus QCC |
| `cusum.statistic: z`, `cusum.k_z: 0.5` | the CUSUM adds the signed z with k 0.5 instead of −ln p with k 1.5 | P2 minus QCC |

The signed z travels in two optional contract fields, `PValues.z` and `Scores.z` (the score stub passes it on). An
experiment picks the forms with `experiment.ablation_form: legacy` (the `ablation` preset); `stub` swaps the whole
module for its stub, as the dashboard's mechanism switches do.

## PRAHARI edge layer

| M | What it does | File (real; stub) | Default | Since |
| --- | --- | --- | --- | --- |
| M30 | Clustering within R over 30 minutes (legacy: around each new candidate; advanced: connected components) | `detect/prahari/edge_real.py`; `cluster.py` | real (legacy form) | Phase 6 |
| M31 | Spatial common-mode rejection, ratio ≥ 3 (≥ 1.5 while a lightning storm is flagged, ASM) | `edge_real.py`; `scmr.py` (always passes) | real | Phases 6, 9 |
| M32 | Fisher combination of candidate p-values p_i ≈ r·W | `edge_real.py`; `fisher.py` (Bonferroni) | real | Phase 6 |
| M33 | Prior: legacy day type (1e-4 dry, 1e-6 wet); per-cluster integral form λ × p_s × a(t) over the cells within R (`srp.form: integral`) | `decide_real.py`; `srp.py` (constant) | real (legacy) | Phases 6, 9 |
| M34 | SBB Bayes-factor bound and risk-adaptive quorum (legacy 2/3 or Bayes) | `learn.py` (bound), `decide_real.py`; `raq.py` (fixed 2) | real (legacy quorum) | Phase 6 |
| M35 | Incident ladder WATCH → CANDIDATE → CONFIRMED → ESCALATED | `escalate_real.py`; `escalate.py` | real | Phase 6 |
| M36 | Fitted likelihood ratio from controlled burns: logistic regression (L2, IRLS) on [X_C, \|C\|, ln ρ_C, c̄], used once K ≥ 10 | `learn_real.py`, harness `eval/learning.py` | stub (the bound); real with a model file | Phase 9 |

## Satellite, communications, energy (Phases 8–9)

| M | What it does | File | Default |
| --- | --- | --- | --- |
| M37 | Satellite alert time: fixed-time overpasses, 500 m² threshold, p_miss 0.2, MODIS or VIIRS processing delay | `satellite/race.py`; `overpass.py` (fixed delay) | stub; real in the Phase 9 scenarios |
| M39, M40 | LoRa time on air; ALOHA collisions with the 6 dB capture effect, retries, TS011 relay hops, store-and-forward during gateway outages | `comms/lora.py`, `comms/lorawan_real.py` (stub: perfect link in `lorawan.py`) | stub; real in `gateway_outage`, `cloudy_days` (Phase 8) |
| M41–M43 | Energy budget by power mode and radio airtime; half-sine solar harvest with cloudy days; supercapacitor store with ULP (< 20%) and stop (< 5%) modes | `energy/power.py`, `energy/budget_real.py` (stub: infinite energy in `budget.py`) | stub; real in the Phase 8 scenarios |

Communications and energy stay stubs in the default configuration, the golden presets and every earlier scenario, so
their results and recordings are unchanged; the two Phase 8 scenarios switch them on (`DECISIONS.md` P8-1). The Phase 9
models follow the same rule: `faults`, `score`, `satellite` and `learn` are stubs by default and real only in the
scenarios and presets that show them (`DECISIONS.md` P9-1).
`prahari energy` writes the M41–M43 comparison to `results/energy.json` for the Results view.

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
