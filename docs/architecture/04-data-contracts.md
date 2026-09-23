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
| `links` | per node: gateway, SF, distance, path loss, received power, `modelled` (Phase 1) |
| `nodes`, `gateways` | positions |
| `spacing_m`, `radius_m`, `detection_radius_m`, `satellite_pixel_m` | geometry |
| `modules` | requested state of every module |
| `model_card` | per module: kind running, equation, tag, description, version, source, `notes` (stage snapshot) |

### Frame

| Field | Meaning |
| --- | --- |
| `t` | minutes since start |
| `weather` | `T` °C, `RH` %, `wind_ms`, `wind_dir_deg` (direction the wind comes from), `rain_mm`, `ffmc`, `dew_c` |
| `prior` | `odds`, `quorum` (nodes that must agree today), `day_type` |
| `nodes.state` | per node: 0 normal, 1 elevated, 2 candidate, 3 confirmed, 4 fault, 5 low power |
| `nodes.reading`, `residual`, `p`, `cusum`, `health`, `soc`, `conc` | per-node values (4 significant figures); `conc` is the fire signal reaching the node |
| `nodes.baseline`, `nodes.n_cal` | TTC slow baseline and QCC calibration-set size (Phase 5); the p floor is 1/(n_cal + 1) |
| `cusum_h` | node CUSUM threshold in use (`h_default` until tuned) |
| `haze` | regional haze level |
| `fires` | active fires: id, position, area, age, source strength |
| `plume` | optional smoke grid: origin, cell size, shape, max, base64 float16 values (row 0 = south) |
| `packets` | uplink packets this tick |
| `events` | `ignition`, `candidate`, `p0_alarm`, `p1_alarm`, `p1t_alarm`, `haze_start`, `satellite_alert`, `degraded`, `module_switch` (live) |
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
  protocol fire; the protocol fires themselves; the `node` block when node metrics are on.
- `results/summary.json` (committed), read by the Results tab:

| Field | Meaning |
| --- | --- |
| `label`, `preset`, `scenario`, `seeds`, `n_nodes`, `spacing_m`, `days` | run identity |
| `pipelines.<P>.false_incidents_per_month` | `rate`, `ci95` (M45), `count`, `days`, `per_seed` |
| `pipelines.<P>.confirmed_within_3h` | `k`, `n`, `rate`, `ci95` (M44) |
| `pipelines.<P>.latency_median_min` | median minutes from ignition to confirmation |
| `node.per_seed[]` | `exceed`, `p_min`, `cand_per_node_30d`, `local_cand_per_node_30d`, `cm_time_frac_test`, `h`, `h_tuned`, `h_at_cap`, `p1t_h`, `p1t_at_cap`, module `states` |
| `node` summary | `exceed_mean`, `local_cand_mean`, `local_cand_median`, `h_mean`, `targets`, `pass` |
| `reference` | the report's values, copied from `engine/tests/golden/report_reference.json`, labelled as such |

## Configuration files

`configs/default.yaml` (every key), `configs/scenarios/*.yaml` (demo runs), `configs/experiments/*.yaml` (experiment
presets). See [02-engine.md](02-engine.md#configuration).
