# 5. Troubleshooting

Symptoms first, then the likely cause and the fix. Several of these were met while building the project; the
[journey](../journey/challenges-and-lessons.md) tells those stories.

## Engine

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `config error: params.X: missing 'source' (one of …)` | A parameter block without a provenance tag. This is deliberate (CLAUDE.md rule 9). | Add `source: "ASM …"` (or LIT, DER, VEN, TGT) to the block. |
| `config error: …: unknown key '…'` | A scenario overrides a key that is not in `configs/default.yaml` (often a typo). | Fix the spelling, or add the key with a default and a source to `default.yaml`. |
| `config error: …: key '…' expects float, got int` | Scenario values must have the default's type. | Match it, for example `1.0` for a float default. |
| `modules: missing states for [...]` | A module was added to the pipeline but not to `configs/default.yaml → modules`. | Add `name: stub` (or `real`, `off`). |
| A module shows **degraded** in the health table | Its real version raised an exception or returned NaN, the wrong shape or an out-of-range value; the stub took over. | Read `last_error` in `recordings/<name>.health.json` or the Health tab. The run itself is fine. |
| `real` requested but health shows `stub` | That module has no real implementation yet. | Expected until its phase; see [../architecture/03-models.md](../architecture/03-models.md). |
| Two runs of the same scenario differ | Something used unseeded randomness, or the scenario or code changed between runs. | All randomness must come from `core/rng.py`; compare the configs. |
| `record.from_day … is not inside the run` | The warm-start day is at or after the end of the run. | Lower `record.from_day` or raise `run.days`. |
| `prahari: command not found` | The package is not installed in the active environment. | `pip install -e "engine[dev]"` and activate the venv. |
| The golden experiment takes many minutes | It simulates 5 seeds × 58 days × 2 passes. | Use `--seeds 11` for a quick check; the full run is about 8 minutes. |
| Golden test reports P0 or P1t outside the report interval | A known sampling effect, documented and checked against the oracle over 20 seeds. | See [../results/validation.md](../results/validation.md); do not tune to make it pass. |

## Dashboard

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| A new recording is not in the list | Recordings are copied into `dashboard/public/` only when `dev` or `build` starts. | Restart `npm run dev`, or run `npm run sync-recordings`. |
| Results tab says "No results yet" | `results/summary.json` is missing, or was not copied. | Run `prahari experiment --preset golden`, then restart the dashboard. |
| `unsupported schema …; expected prahari.frame/1` | The file is not a PRAHARI recording, or it came from an incompatible engine version. | Regenerate it with the current engine. |
| Blank page when opening `dist/index.html` directly | Browsers block module scripts on `file://`. | Use `npm run preview` or any static file server (offline `file://` support is planned for Phase 10). |
| A `.gz` recording fails to load in an old browser | `DecompressionStream` is missing (older Safari or Firefox). | Use a current Chromium, Chrome, Edge or Firefox. |
| Charts do not appear at first | The chart code loads when its tab opens. | Wait a moment; check the browser console for errors. |
| Port 5173 or 4173 already in use | A previous dev or preview server is still running. | Stop it (Ctrl-C in its terminal). If you script it, find the process ID first; a pattern-based `pkill` can match and kill your own shell. |
| `npm install` fails resolving vitest peers | Some npm 10 releases fail on vitest 4.1.x optional peers. | The project pins vitest 5 (DECISIONS Dep-2); run `npm install` from `dashboard/` with the committed lock file. |
| `npm audit` warnings about echarts or vitest | Older versions carried advisories. | The project uses echarts 6.1 and vitest 5, which report none (Dep-2, Dep-5). |
| The node inspector is empty | No node is selected. | Click a node on the map (the tab switches to Node automatically). |
| The floor line or baseline is missing from the inspector | The recording predates Phase 5. | Regenerate the recording. |

## Live mode

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| "server not reachable — replay still works" | The server is not running, or on another port. | `uvicorn server.app:app --port 8000` from the repository root; check the URL in the Live panel. |
| `ModuleNotFoundError: fastapi` / `uvicorn` | The optional server extra is not installed. | `pip install -e "engine[dev,server]"`. |
| `ModuleNotFoundError: server` | uvicorn was started outside the repository root. | Start it from the root (the `server` package lives there). |
| Live run stops advancing | The run finished, or a new run replaced it. | Status shows "live run finished"; press Start again. |
| A switch in replay is greyed out | No pre-recorded variant exists for that module. | Use live mode, or record the variant (`<scenario>__<module>-stub.yaml`). |
| After switching QCC live, candidates stop for a while | Switching rebuilds the module; QCC restarts its calibration. | Expected (DECISIONS P6-8). |

## Before a demo

1. `pytest engine/tests -q` and `cd dashboard && npm test` pass.
2. `npm run build && npm run preview`, then open each recording you plan to show.
3. Turn off Wi-Fi and reload: everything should still work.
