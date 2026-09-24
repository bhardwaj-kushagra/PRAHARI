# Architecture 4 — data contracts and files

The engine and the dashboard share nothing but these files. The frame schema is `prahari.frame/1`; since Phase 0 it
has only gained fields (additive changes), so older recordings still open.

## Recording: `recordings/<scenario>.prs.jsonl.gz`

Gzip (header time 0, no file name, so identical runs give identical bytes) of JSON lines:

```text
{"header": {...}}         line 1
{"t": 840, ...}           one frame object per recorded tick
{"trace": {...}}          evidence records, interleaved at the tick they were made
{"footer": {...}}         last line
```

### Header

| Field | Meaning |
| --- | --- |
| `schema`, `label` | `prahari.frame/1`, `SIMULATION` |
| `scenario`, `description`, `seed`, `start`, `days`, `tick_minutes`, `n_ticks`, `record_every` | run identity |
| `record_from_min` | only for warm-start recordings: the first recorded minute (Phase 5 follow-up) |
| `map` | width, height, `interfaces` (paths, village, road, power line), `lambda_grid` (ignition likelihood raster) |
| `layouts` | active layout, and nodes plus covered likelihood for grid, corridor and greedy (Phase 1) |
| `links` | per node: gateway, SF, distance, path loss, received power, `modelled` (Phase 1); `relay` (TS011 relay node, only when some node needs one — Phase 8) |
| `nodes`, `gateways` | positions |
| `spacing_m`, `radius_m`, `detection_radius_m`, `satellite_pixel_m` | geometry |
| `modules` | requested state of every module |
| `model_card` | per module: kind running, equation, tag, description, version, source, `notes` (stage snapshot) |
| `regime` | the Regime Card the run used (Phase 9): `name` (`none` without a card), `label`, `radio_plan`, `alert_format`, `lightning` |

### Frame

| Field | Meaning |
| --- | --- |
| `t` | minutes since start |
| `weather` | `T` °C, `RH` %, `wind_ms`, `wind_dir_deg` (direction the wind comes from), `rain_mm`, `ffmc`, `dew_c` |
| `prior` | `odds`, `quorum` (nodes that must agree today), `day_type` |
| `nodes.state` | per node: 0 normal, 1 elevated, 2 candidate, 3 confirmed, 4 fault (from Phase 9: health weight below `display.abstain_c` = 0.1, the sensor abstains), 5 low power |
| `nodes.reading`, `residual`, `p`, `cusum`, `health`, `soc`, `conc` | per-node values (4 significant figures); `conc` is the fire signal reaching the node |
| `nodes.baseline`, `nodes.n_cal` | TTC slow baseline and QCC calibration-set size (Phase 5); the p floor is 1/(n_cal + 1) |
| `nodes.queue`, `nodes.mode` | only with the real radio and energy models (Phase 8): frames waiting at each node (store-and-forward), and the power mode 0 standard, 1 ULP, 2 off |
| `cusum_h` | node CUSUM threshold in use (`h_default` until tuned) |
| `haze` | regional haze level |
| `fires` | active fires: id, position, area, age, source strength |
| `plume` | optional smoke grid: origin, cell size, shape, max, base64 float16 values (row 0 = south) |
| `packets` | uplink attempts: `from`, `to` (gateway id or `n<k>` for a relay), `ok`, `sf`; Phase 8 adds `kind` (candidate, heartbeat), `retry`, `toa_ms`, `relay`, `queued`, and `t` for packets carried from ticks between recorded frames |
| `gateways_down` | only with the real radio model: gateways out of service this minute (Phase 8) |
| `events` | `ignition` (Phase 9 adds `cause`: scripted, human or lightning), `candidate`, `p0_alarm`, `p1_alarm`, `p1t_alarm`, `haze_start`, `satellite_alert`, `degraded`, `module_switch` (live); Phase 9 adds `satellite_plan` (`fire`, `overpass_t`, `platform`, `alert_t`, `missed` overpass minutes) and `fault_start` (`node`, `kind`) |
| `alerts` | new alerts: level, cluster members, trace id, `incident` (Phase 6) |
| `health` | state of every module |

A frame is written every `record.every_k_ticks` ticks, at every tick with an event or alert, and at the last tick.

### Trace

Two kinds, linked from events and alerts by `trace_id`:

- `candidate` — node, p-value, CUSUM value and threshold, health weight.
- `decision` — level, cluster, `incident` and `anchor` (Phase 6), per-node evidence, SCMR (`f_loc`, `f_net`, `ratio`, `pass`, `modelled`), Fisher (`X`,
  `dof`, `p_cluster`, `method`), prior (λ, p_s, odds, day type), Bayes (bound, posterior odds, threshold, quorum,
  decision, `method`) and a generated `explanation` sentence. The `method` fields say when a stub made the decision
  (for example "fixed quorum (stub)"), so no explanation claims a calculation that did not happen.

### Footer

`frames`, `traces`, and each module's final health (requested, state, running, errors, last error, degraded at).

## Live stream (Phase 6)

The server's WebSocket `/frames` sends exactly the recording's lines as text messages: `{"header": …}` (with
`"live": true`), frames, `{"trace": …}`, and `{"footer": …}` (or `{"footer": {"stopped": true}}` /
`{"footer": {"error": …}}`). A client that connects late receives everything from the start.

## Health: `recordings/<scenario>.health.json`

Written beside each recording by `prahari run`: seconds, frame and trace counts, and per module the health record plus
`mean_step_ms`. Timings live here, not in the recording, so recordings stay byte-identical. Ignored by git.

## Experiment results

- `results/<preset>_seed<N>.json` (ignored by git): per pipeline the false incidents, alarms, latencies of each
  protocol fire; the protocol fires themselves; the tuned h; the `node` block when node metrics are on; the `dial`
  points when the preset has a dial.
- `results/<preset>.json` (committed): the pooled result of one preset (`golden`, `ablation`, `spacing`,
  `seeds20`); a spacing preset holds one pooled result per spacing under `by_spacing`.
- `results/summary.json` (committed), read by the Results tab, built by `eval/report.py`:

| Field | Meaning |
| --- | --- |
| `label`, `preset`, `scenario`, `seeds`, `n_nodes`, `spacing_m`, `days` | run identity (of the golden preset) |
| `pipelines.<P>.false_incidents_per_month` | `rate`, `ci95` (M45), `count`, `days`, `per_seed` |
| `pipelines.<P>.confirmed_within_3h` | `k`, `n`, `rate`, `ci95` (M44) |
| `pipelines.<P>.single_node_within_3h` | fires with at least one node candidate within 3 h (P2 variants) |
| `pipelines.<P>.latency_median_min` | median minutes from ignition to confirmation |
| `pipelines.<P>.h_per_seed` | the tuned node threshold per seed (P2 variants) |
| `node.per_seed[]` | `exceed`, `p_min`, `cand_per_node_30d`, `local_cand_per_node_30d`, `cm_time_frac_test`, `h`, `h_tuned`, `h_at_cap`, `p1t_h`, `p1t_at_cap`, module `states` |
| `node` summary | `exceed_mean`, `local_cand_mean`, `local_cand_median`, `h_mean`, `targets`, `pass` |
| `dial[]` | per target (false candidates per node per 30 d): `h_per_seed` and the same pooled fields as a pipeline |
| `spacing` | `seeds` and `rows[]`: `spacing_m`, `confirmed_within_3h`, `single_node_within_3h`, `false_incidents_per_month`, `latency_median_min` |
| `seed_sweep` | `seeds` and `pipelines` of the 20-seed sweep |
| `sources` | which preset file supplied which part, with its seeds |
| `table[]` | one row per pipeline in the report's order: `pipeline`, `label`, our rate and intervals, and `report` (the report's row) |
| `learning` | Phase 9, from `results/learning.json` (`prahari experiment --preset learning`): `train_seeds`, `test_seeds`, `fa_budget_per_month`, `bound` and `rows[]` per K (`rule`, `n_pos`, `n_neg`, `weights`, `confirmed`, `fires`, `rate`, `ci95`, `latency_median_min`, `false_incidents`, `ln_threshold`), and `maturity.rows[]` per calibration length (`cal_days`, `n_cal`, `p_min`, `candidate_rate`, `candidate_latency_median_min`, `h`). The fitted models are written beside it as `learning_model_k<K>.json` |
| `energy` | Phase 8, from `results/energy.json` (`prahari energy`): M41 `rows` (sensor, mode, `wh_day`, `autonomy_days`), M42 `harvest_wh_day` (clear, cloudy range), M43 `store_wh`, `frames_per_day`, `toa_ms` |
| `reference` | the report's values, copied from `engine/tests/golden/report_reference.json`, labelled as such |

## Storyboard: `dashboard/public/storyboard.json` (Phase 10)

`title` and `steps[]`, one per key. Each step: `key` (1–9), `title`, `recording` (a file in `recordings/`; omitted =
keep the open one), a bookmark as `day` (1-based) and `time` (`HH:MM`) or `t` (minutes since the start), `speed`,
`play`, `panel` (`health`, `signals`, `node`, `alerts`, `results`), `layers` (map layers to set), `scroll` (a
`data-testid` to bring into view), `seconds` (planned speaking time) and `caption` (the line on screen). Checked on load
and by `presenter.test.ts`: keys unique, times well formed, recordings present, total planned time ≤ 180 s.

## Configuration files

`configs/default.yaml` (every key), `configs/regimes/*.yaml` (Regime Cards, Phase 9: merged between the defaults and
the scenario when a scenario names `regime:`), `configs/scenarios/*.yaml` (demo runs), `configs/experiments/*.yaml`
(experiment presets). See [02-engine.md](02-engine.md#configuration).

## Stage contracts added in Phase 9

All additive, with defaults, so every earlier stage and test is unchanged (CLAUDE.md rule 3):

| Contract | New field | Meaning |
| --- | --- | --- |
| `Readings` | `missing` | per node: no data this minute (a dropout); the last value is held |
| `Delivered` | `t_detect` | per delivered candidate: the minute it was raised (the cluster window uses it) |
| `SatelliteAlerts` | `plan` | overpass plans drawn this minute, one per new fire |
| `Prior` | `lightning`, `lam_map`, `disk` | storm flag for SCMR; the integral prior's rate map and the raster cells within R of each node |
| `Raq` | `odds_c`, `lam_c` | per-cluster prior odds and expected sustained fires (integral prior only) |
