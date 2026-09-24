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
| `config error: run.days: must be > 0` (or `world.n_nodes`, `world.spacing_m`, `record.from_day`, …) | A value the simulator cannot run with; release 1.0 checks these when the configuration loads. | Fix the named key. A grid layout needs a square number of nodes (100 = 10 × 10); a warm start (`record.from_day`) must lie inside the run. |
| `config error: unknown preset '…'; presets: …` | `--preset` names no file in `configs/experiments/`. | Use one of the listed presets, or `--config path/to/preset.yaml`. Presets are found from any folder. |
| `file error: …` | The output path cannot be written (no such folder, no permission, a folder instead of a file, disk full). | Fix the path. Outputs are written atomically: an existing recording or result is never left half-written. |
| `interrupted — nothing was written for the unfinished run` (exit 130) | Ctrl-C during a run. | Start the run again; the previous recording, if any, is untouched. |
| `prahari: command not found` | The package is not installed in the active environment. | `pip install -e "engine[dev]"` and activate the venv. |
| The golden experiment takes many minutes | It simulates 5 seeds × 58 days × 2 passes, plus the dial replays. | Add `--jobs 4` on a 4-core machine (about 5 minutes); use `--seeds 11` for a quick check. The four presets together take about 45 minutes with `--jobs 4`. |
| Golden test reports P0 or P1t outside the report interval | A known sampling effect, documented and checked against the oracle over 20 seeds. | See [../results/validation.md](../results/validation.md); do not tune to make it pass. |
| Golden tests fail for P2, the ablations or spacing | Known and documented: P2 detection is below the report (haze in calibration windows, `KNOWN_ISSUES.md`); node ablations are defined as module stubs. | See [../results/validation.md](../results/validation.md) and `DECISIONS.md` P7-9, P7-10. |
| No packets or energy rings on the map | Only recordings made with the real radio and energy models carry them (`gateway_outage`, `cloudy_days`). | Open one of those, or run a scenario with `modules.comms: real` and `modules.energy: real`. |
| `config error: config file not found: …/regimes/…` or a card key rejected | `regime:` names a file that is not in `configs/regimes/`, or a card sets a key missing from `default.yaml`. | Use `india`, `canada`, `usa` or `australia`, or add the new card's keys to `default.yaml` with a source. |
| Results tab lacks the learning and maturity charts | `results/learning.json` has not been written. | `prahari experiment --preset learning --jobs 4` (about 5 minutes), then restart the dashboard. |
| `learn: real` behaves exactly like the bound | No model file is set (`params.learn.model_file`), or the model was fitted on fewer than `k_min` = 10 burns. | Point `model_file` at `results/learning_model_k100.json`; the model card notes show `fitted_in_use`. |
| Results tab lacks the energy chart | `results/energy.json` has not been written. | `prahari energy`, then restart the dashboard. |
| Results tab lacks the spacing or ablation chart | Only `golden` has run; `summary.json` is rebuilt from whichever preset files exist. | Run the `ablation` and `spacing` presets, then restart the dashboard. |

## Dashboard

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| A new recording is not in the list | Recordings are copied into `dashboard/public/` only when `dev` or `build` starts. | Restart `npm run dev`, or run `npm run sync-recordings`. |
| Results tab says "No results yet" | `results/summary.json` is missing, or was not copied. | Run `prahari experiment --preset golden`, then restart the dashboard. |
| `unsupported schema …; expected prahari.frame/1` | The file is not a PRAHARI recording, or it came from an incompatible engine version. | Regenerate it with the current engine. |
| Blank page when opening `dist/index.html` directly | Browsers block module scripts on `file://`. | Use `npm run preview` or any static file server (offline `file://` support is planned for Phase 10). |
| A `.gz` recording fails to load in an old browser | `DecompressionStream` is missing (older Safari or Firefox). | Use a current Chromium, Chrome, Edge or Firefox. |
| Charts do not appear at first | The chart code loads when its tab opens. | Wait a moment; check the browser console for errors. |
| Port 5173 or 4173 already in use | A previous dev or preview server is still running. | Stop it (Ctrl-C in its terminal). If you script it, list the processes in one command and kill the exact process ID in another: `pkill -f` or `pgrep -f` with the pattern in the same command line also matches, and kills, your own shell. |
| `npm install` fails resolving vitest peers | Some npm 10 releases fail on vitest 4.1.x optional peers. | The project pins vitest 5 (DECISIONS Dep-2); run `npm install` from `dashboard/` with the committed lock file. |
| `npm audit` warnings about echarts or vitest | Older versions carried advisories. | The project uses echarts 6.1 and vitest 5, which report none (Dep-2, Dep-5). |
| The node inspector is empty | No node is selected. | Click a node on the map (the tab switches to Node automatically). |
| A panel shows "The … view could not be drawn. The other views still work." | That view raised an error (for example a recording from an incompatible version). The rest of the dashboard keeps running. | Press "Try again", or open another recording; the message and the browser console name the error. |
| The footer says "incomplete recording (no footer …)" | The recording's last line was cut off (an interrupted copy or run); the frames before it are shown. | Regenerate the recording (`prahari run …`) or copy it again. |
| The race headline says "Satellite side not modelled in this recording (stub …)" | The recording was made with the satellite stub (a fixed delay after ignition, not the M37 model), so no race is claimed. | Open `satellite_race` (or another Phase 9 scenario) for the M37 race. |
| On a small screen the left column scrolls | Release 1.0 keeps the map at least 360 px tall; below that the map, layers and race timeline scroll. | Use the browser zoom (Ctrl/Cmd −) to fit everything on a projector. |
| No race timeline under the map | The recording has no fire, or predates Phase 9's satellite events. | Open `satellite_race` (or any Phase 9 recording); without `satellite_plan` events the strip shows PRAHARI's side only. |
| No regime selector next to the recording list | The bundled recordings carry only one regime, or `index.json` was written before Phase 9. | Restart `npm run dev` (or rebuild) so the sync script rereads the headers. |
| A faulty node is not drawn as a fault | The glyph shows the system's view (health weight below 0.1), not the injected fault; small offsets keep their weight. | See the `fault_start` events on the time bar and `KNOWN_ISSUES.md`. |
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

## Presenter mode and launchers

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Pressing 1–9 does nothing | The focus is in a text box or a select, or `storyboard.json` failed to load. | Click the map first; check the caption strip for a `storyboard.json:` message. |
| The caption says "no SCMR variant of this recording" | S and R need pre-recorded variants; only `wet_morning_haze` (and `node_mature` for SCMR) have them. | Press 3 or 4 first, or record a variant (`<scenario>__scmr-stub.yaml`). |
| A caption or bookmark is wrong | `storyboard.json` has an old value. | Edit `dashboard/dist/storyboard.json` (this build) or `dashboard/public/storyboard.json` (kept); reload the page — no rebuild. |
| `scripts/demo.sh: Permission denied` | The execute bit was lost in a copy. | `sh scripts/demo.sh`, or `chmod +x scripts/demo.sh`. |
| `OSError: [Errno 98] Address already in use` | A launcher is already serving port 8765. | Use it, or `PORT=9000 scripts/demo.sh`. |
| PowerShell refuses to run `demo.ps1` | The execution policy blocks scripts. | Double-click `scripts\demo.cmd`, which bypasses the policy for this script only. |

## Before a demo

Follow `DEMO_CHECKLIST.md` in the repository root. In short:

1. `pytest engine/tests -q` and `cd dashboard && npm test` pass.
2. `scripts/demo.sh --build`, then press 1–9 once through.
3. Turn off Wi-Fi and reload: everything should still work.
