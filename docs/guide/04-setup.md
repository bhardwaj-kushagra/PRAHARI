# 4. Setup and running

## Before you start

| Need | Version used to build this | Notes |
| --- | --- | --- |
| Python | 3.11 (3.11 or newer required) | engine; NumPy, SciPy, PyYAML, pytest |
| Node.js | 22 (20 or newer recommended) | dashboard; npm 10 |
| Disk | about 400 MB with `node_modules` | recordings in the repo take about 12 MB |
| Browser | Chromium, Chrome, Edge or Firefox (recent) | the dashboard uses `DecompressionStream` to read `.gz` recordings |
| Network | only for `pip install` and `npm install` | the dashboard itself runs offline |

Things worth knowing first:

- **No server is needed to show the demo.** The dashboard replays files. `recordings/` and `results/summary.json` are
  committed, so a fresh clone can open the dashboard without running the engine at all.
- **Everything is deterministic.** The same configuration and seed give a byte-identical recording.
- **Configuration is layered.** `configs/default.yaml` holds every key; a scenario file (`configs/scenarios/*.yaml`)
  overrides only what it names. Unknown keys and parameter blocks without a `source` tag are rejected on purpose.

## Install

From the repository root:

```bash
python3 -m venv .venv && source .venv/bin/activate      # optional but recommended
pip install -e "engine[dev]"                            # quotes matter in zsh
cd dashboard && npm install && cd ..
```

Check the installation:

```bash
pytest engine/tests -q            # about 1 minute; golden tests are skipped unless PRAHARI_GOLDEN=1
cd dashboard && npm test && cd ..
```

## Look at the demo (no engine needed)

```bash
cd dashboard
npm run dev                       # http://localhost:5173 — copies recordings/ and results/ in first
```

Or a static build, closer to what a conference laptop would serve:

```bash
cd dashboard && npm run build && npm run preview       # http://localhost:4173
```

Pick a recording from the list at the top right, or drag any `*.prs.jsonl.gz` file onto the page. A direct link also
works: `http://localhost:5173/?rec=node_mature.prs.jsonl.gz`.

## Generate recordings

Each command simulates a scenario and writes a recording plus a `*.health.json` with per-module state and timings.

| Command | What it shows | Time |
| --- | --- | --- |
| `prahari run --config configs/scenarios/smoke.yaml --out recordings/smoke.prs.jsonl.gz` | framework check: one day, one scripted fire, stub detectors | ~2 s |
| `prahari run --config configs/scenarios/siting_greedy.yaml --out recordings/siting_greedy.prs.jsonl.gz` | greedy layout (also `siting_corridor`) | ~2 s |
| `prahari run --config configs/scenarios/signals_3day.yaml --out recordings/signals_3day.prs.jsonl.gz` | realistic signals, haze on day 2, real node layer | ~7 s |
| `prahari run --config configs/scenarios/fires_day.yaml --out recordings/fires_day.prs.jsonl.gz` | Poisson and scripted fires, legacy plume | ~2 s |
| `prahari run --config configs/scenarios/fires_day_gaussian.yaml --out recordings/fires_day_gaussian.prs.jsonl.gz` | the same fires with the Gaussian plume | ~2 s |
| `prahari run --config configs/scenarios/node_3day.yaml --out recordings/node_3day.prs.jsonl.gz` | a young network: calibration maturing, haze day 2, fire day 3 | ~7 s |
| `prahari run --config configs/scenarios/node_mature.yaml --out recordings/node_mature.prs.jsonl.gz` | a mature network: 31 days simulated, days 29–31 recorded, fire on day 31 | ~70 s |

Options: `--seed N` overrides the seed, `--days D` the length. Restart `npm run dev` (or rerun `npm run build`) after
generating, so the new files are copied into the dashboard.

## Run experiments

```bash
prahari experiment --preset golden                              # P0, P1, P1t + node metrics, seeds 11–55, ~8 min
prahari experiment --preset golden --seeds 11 --pipelines P1    # quick single-seed check
PRAHARI_GOLDEN=1 pytest engine/tests/golden                    # golden assertions (slow)
```

The experiment writes `results/<preset>_seed<N>.json` (ignored by git) and `results/summary.json` (committed), which
the dashboard's **Results** tab reads.

## Where things are

| Path | Contents |
| --- | --- |
| `engine/prahari/` | the simulator package (see [../architecture/02-engine.md](../architecture/02-engine.md)) |
| `engine/tests/` | unit, smoke and golden tests |
| `configs/` | `default.yaml`, scenarios, experiment presets |
| `recordings/` | committed demo recordings |
| `results/summary.json` | committed experiment summary |
| `dashboard/` | the React dashboard |
| `reference/` | the report's original simulation (read-only oracle) |
| `docs/` | the specification and this documentation |
