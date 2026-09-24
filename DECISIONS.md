# DECISIONS

Every deviation from `docs/SPEC.md`, new dependency, interpretation or tuning choice. Newest at the bottom of each section.

## Source of truth

- **D-001 (Phase 0).** `docs/SPEC.md` is the single source of truth. The separate "Technical Framework (IEEE IAS AM 2026)" document was not in the repository when Phase 0 started; if it is added, differences are reconciled here before any code changes.

## Spec errata (SPEC 1.0 → 1.0.1)

Found by recomputing every §9.2 reference value and cross-checking M-numbers. All other §9.2 values and the §7 worked examples were verified correct (M6, M8, M13, M23, M26, M32, M34, M38, M39, M43, M44, M45; legacy RAQ 2/3 nodes = Bayes RAQ; 375 m pixel ≈ 29 cells; upwind 0.25 su).

- **E-1.** Files lived at the repo root; moved to `docs/SPEC.md` and `reference/` as `CLAUDE.md`, README and §3.2 require. Contents unchanged.
- **E-2.** §2 P10 example comment cited `M17` for the QCC p-value; QCC is **M26** (M17 is the metal-oxide response).
- **E-3.** §4.2 cusum stub cited "ARL formula (M21)"; M21 is Faults. The ARL formula is **M23**.
- **E-4.** §4.2 learn stub cited "SBB bound (M31)"; M31 is SCMR. The Sellke–Bayarri–Berger bound is in **M34**.
- **E-5.** §4.7 trace example was internally inconsistent (3-node cluster with the 2-node χ² value, BF bound 5200 where M34 gives ≈4200, posterior 0.0099 < 0.01 yet `decision: true`, "dry, busy day" with a wet-day-sized prior). Replaced with consistent values: three p = 6.9e-4 → X = 43.7, dof 6, p_C = 8.6e-8, BF bound 2.6e5, prior odds 1.9e-6, posterior 0.50 ≥ 0.01 → true.
- **E-6 (Phase 2).** M7 used 147.2 as the moisture-conversion constant (Van Wagner & Pickett's 1985 FORTRAN). Over
  the cffdrs reference chain (48 days) that misses by up to 0.12 FFMC, beyond the SPEC's 0.1 tolerance; cffdrs uses
  250·59.5/101 = 147.27723 and then matches to 0.005. SPEC M7 now shows 147.27723 (SPEC 1.0.2).
- **E-7 (Phase 5).** M28's common-mode exclusion said "|z| ≥ 3"; the report simulation counts nodes with a
  slow-baseline z ≥ 3 (one-sided: smoke only raises readings), and the engine follows it. SPEC M28 now says so
  (SPEC 1.0.3, which also adds the per-phase documentation deliverable to §7).

## Notes carried to later phases

- **N-a (Phase 4).** `reference/prahari_simulation.py` writes to hard-coded `/home/claude/…` paths in `__main__`. The golden harness imports its functions; the oracle file itself stays read-only.
- **N-b (Phase 6).** In the oracle, SCMR's f_loc is measured around the *triggering node's* neighbourhood, and the quorum is counted per candidate, not per M30 cluster. Legacy mode follows the oracle; the M30/M31 cluster form is the advanced mode.
- **N-c (Phase 4+).** Per-module RNG streams (§4.4) cannot reproduce the oracle's single stream bit for bit. Golden tests compare within the report's 95% intervals, as §9.3 allows.
- **N-d (Phase 2).** M7 verification needs `cffdrs` reference outputs (≥10 weather days, ±0.1 FFMC). Fetch the published test dataset in Phase 2; if unavailable, park M7 (`ffmc: stub`).
- **N-e (Phase 8).** "0.5 Wh/day with no sun lasts 9 ± 0.5 days" is tested as a constant drain from full to the 5% cut-off: 0.95 × 4.56 / 0.5 = 8.66 days.

## Phase 0 design choices

- **P0-1.** Runner fallback chain is real → stub → off → hold last valid output → the contract's neutral output. Modules whose `off` is not allowed (weather, growth, sensor) skip `off`. Any fallback marks the module `degraded`, logs the error once and emits a `degraded` event in the frame.
- **P0-2.** Step timings are kept out of the recording (written to `*.health.json`) so the same seed gives a byte-identical recording. Recordings use gzip with `mtime=0` and an empty filename.
- **P0-3.** Config validation is plain Python (no Pydantic) to keep dependencies minimal.
- **P0-4.** Selecting `real` for a module that has no real implementation yet runs its stub and shows `stub` in health.
- **P0-5.** "No server" (S2, P8) means no engine or API server. The static build is served by `npm run preview` or any static file host; opening `index.html` from `file://` is deferred to Phase 10 because Chromium blocks module scripts on `file://`.
- **P0-6.** Contract data classes are split across `core/contracts.py` (world and node layer), `core/contracts_edge.py` (edge layer) and `core/contract_checks.py` (validators) to keep files under ~300 lines. `contracts.py` re-exports the edge classes, so every consumer still imports from `prahari.core.contracts`.
- **P0-7.** The cusum stub is the v1 CUSUM of M23 (z = Φ⁻¹(1 − p), k = 0.5, h from Siegmund) because an ARL-derived h is only valid on that scale; a first try applying h = 8.8 to −ln p scores with k = 1.5 gave ~100 false candidates per day. The real M28 (−ln p, k = 1.5, replay-tuned h) arrives in Phase 5.
- **P0-8.** Stub warm-up: the TTC stub uses a running mean until n reaches the 720-min time constant, and the cusum stub holds G at 0 for the first 60 min (`params.cusum.warmup_min`). Without this, the first hour produced ~11 spurious candidates from baseline initialisation.
- **P0-9.** The decision trace records which rule decided (`bayes.method`, `fisher.method`). While RAQ or Fisher are stubs, the explanation says "fixed quorum … (stub RAQ; posterior shown for reference only)" and "Bonferroni p", so no alert claims a Bayes decision that was not made.
- **P0-10.** Recordings are copied into `dashboard/public/recordings/` (gitignored) by `npm run sync-recordings`, which runs automatically before `dev` and `build`; the dashboard lists them from a generated `index.json` and also opens any file via the picker or drag-and-drop.

## Phase 1 design choices

- **P1-1. Larger landscape, centred grid.** On the Phase 0 map (700 m), 100 nodes at 70 m with r_d = 50 m cover 100% of
  the map (the farthest point from a node is 49.5 m) and M38 gives SF7 to every node (SF7 closes to 746 m), so the siting
  comparison and SF colouring would be meaningless. The default landscape is now 1400 × 1400 m with the grid centred
  (`world.offset_m: null`). The report's golden configuration (100 nodes at 70 m) is unchanged; only the surroundings grew.
- **P1-2. Illustrative landscape (ASM).** One village polygon, two footpaths, a road and a power line, placed by hand to
  look like a Terai forest edge. It is not a real place; the model card tags it ASM.
- **P1-3. Village is not forest.** Closed features listed in `landscape.non_forest` get λ = 0 and cannot host greedy
  sites; the village still raises λ around it through its distance field (D = 0 inside).
- **P1-4. Static λ for siting.** M3 is evaluated with a(t) = 1 and no lightning term. Covered fractions are ratios, so
  they do not depend on λ₀ or a(t); λ₀ (1e-9 per m² per minute) is a placeholder rescaled per scenario from Phase 3a.
- **P1-5. Corridor spacing (DER).** M1 places nodes every s metres along the chosen lines; when the lines are shorter
  than N·s, the spacing becomes L/N so that exactly N nodes fit (35 m on the default footpaths plus village edge).
  Offsets alternate ±15 m; a node whose offset lands inside a closed feature takes the other side.
- **P1-6. Greedy on the raster.** Candidate sites are 10 m forest cell centres; coverage uses the same cell-centre rule
  (distance ≤ r_d) as the M4 objective, so greedy's gains and the reported fractions agree exactly. Ties go to the
  lowest row-major cell, so siting is deterministic and needs no RNG stream.
- **P1-7. Setup modules.** `landscape`, `siting` and `links` run once before the first tick through the same `Slot`
  isolation as tick stages; setup failures appear as `degraded` events in the first frame. `siting` may not be off.
- **P1-8. `links` separate from `comms`.** Static link budgets (M38 without shadowing) live in their own module so that
  the `comms` stub keeps its Phase 0 behaviour. Shadowing, TS011 relays and collisions arrive with Phase 8; nodes with no
  closing SF are flagged "needs a relay" rather than hidden.
- **P1-9. Map colours.** Spreading factor is ordinal, so links use one blue hue from dim (SF7) to bright (SF12),
  validated with the dataviz ordinal check on the dark map surface (monotone lightness, ΔL ≥ 0.06, 2.19:1 at the dim
  end). Ignition likelihood is a one-hue warm-white alpha ramp, keeping ember, amber and pine for node states.
- **P1-10. Phase 0 files touched (approved with the Phase 1 plan).** `core/pipeline.py` (setup call, header fields),
  `core/contracts.py` (re-export), `stages.py` (imports), `world/geometry.py` (additive `grid_origin`,
  `corridor_layout`), `configs/default.yaml` (world block, new parameter blocks), `configs/scenarios/smoke.yaml` and
  `tests/smoke/test_smoke.py` (the scripted fire moved from (300, 330) to (650, 680), the same place relative to the
  re-centred grid). Dashboard: `CommandMap.tsx` (layers, glyph scaling), `HeaderStrip.tsx`, `NodePanel.tsx`, `App.tsx`,
  `types.ts` (additive), `theme.css`.

## Phase 2 design choices

- **P2-1. M7 verification fixture.** `engine/tests/unit/data/cffdrs_fwi_01.csv` is the cffdrs package's published
  `fwi_01` test output (48 days, 4 significant figures), copied unchanged with provenance in the folder's README.
  cffdrs is GPL-2; the file holds numeric outputs only.
- **P2-2. Weather details (ASM).** ε_T's σ = 0.3 °C is read as the *stationary* sd (innovation 0.3·√(1−0.98²)).
  Daily means and dew point follow a mean-reverting walk (lag-1 0.8 per day, sd 1 °C) rather than a pure random walk,
  which would drift without bound over 58-day experiments. Wind persistence 0.995 and direction persistence 0.999 per
  minute. Rain: one event on a day with probability `rain_prob_day`, lognormal total (median 5 mm), spread over
  60–240 min. The FFMC stage sums rain over the previous 24 h and converts wind to km/h.
- **P2-3. Sensor, nuisance and haze follow the oracle.** Parameters match `reference/prahari_simulation.py::background`
  (cycle amplitude, ±30% day amplitude, drift and ageing, AR(1) 0.95 with daytime factor, 0.05·t₃ tail, roadside split,
  event shape, haze rate and trapezoid, node gains) so that legacy-mode golden runs stay comparable.
- **P2-4. Framework scenarios keep stub signals.** `smoke`, `siting_corridor` and `siting_greedy` set `sensor`,
  `nuisance` and `haze` to `stub` in their scenario files (module states come from config, rule 2). With realistic
  signals, the Phase 0 detection stubs flood (see PROGRESS) and would bury these scenarios' scripted fires. A trial fix
  to the TTC stub's warm-up (first-day running statistics) did not reduce the flood materially and was reverted to keep
  the accepted Phase 0 file unchanged.
- **P2-5. `signals_3day` instead of a week.** A week-long recording with the stub detectors' candidate flood was 11 MB
  compressed (65 MB raw, 3 s to parse) because SPEC §4.6 records every event tick. Three days gives 5.6 MB and still
  shows daily cycles, nuisance spikes and a scripted haze episode.
- **P2-6. Charts.** ECharts (allowed by rule 13) with tree-shaken imports, loaded only when the Signals tab opens (main
  bundle stays 173 kB). Single-series charts, titles naming the series, one neutral series hue, text tokens for text,
  haze as neutral shaded bands; ember/amber/pine stay reserved for node states.
- **P2-7. Files from accepted phases touched (approved with the Phase 2 plan).** `core/contracts.py` (additive
  `Weather.dew_c`, `Additive.level`), `record/frames.py` (`dew_c` in the weather dict), `core/pipeline.py` (frame
  `haze` level, `haze_start` events), stage files `env/weather.py`, `env/ffmc.py`, `sensors/*.py` (real classes added;
  stubs unchanged), `configs/default.yaml`, the three framework scenario files, `docs/SPEC.md` (E-6), dashboard
  `types.ts` (additive), `store.ts` (panel name), `App.tsx` (tab), `theme.css`.

## Phase 3a design choices

- **P3a-1. Legacy models stay stubs.** SPEC §5 makes the legacy form of a model its stub and default: `growth` (M9) and
  `plume` (M12, M13, M16) keep running as `stub`. The Phase 3a acceptance values are tested through those stages.
- **P3a-2. Activity profile (ASM).** a(t) = 0.2 at night, 1.0 from 09:00 to 18:00, smoothstep ramps over 06–09 and
  18–21, ×1.5 on `market_days`.
- **P3a-3. λ₀ scaling (DER, approximate).** λ₀ = expected_fires / (Σ_t a(t) Δt · ΣS·A_cell · p_s(ps_reference_ffmc)),
  with the reference FFMC 90. Actual FFMC varies through a run, so the realised expectation differs when fuel is much
  wetter or drier than the reference; the test checks the count at the reference FFMC.
- **P3a-4. Thinning envelope.** Candidates are drawn uniformly over the map at λ₀·a_max·S_max (S scaled to max 1) and
  accepted with a(t)/a_max · S(x), as SPEC §5.3 describes; accepted attempts are counted in `Fires.attempts`.
- **P3a-5. Plume grid.** Every 5 ticks while fires burn, the running plume model's mean field (no intermittency) is
  evaluated on a 10 m grid over the fires' bounding box ± 300 m, stored as base64 little-endian float16 in frame key
  `plume` (row 0 = south). It is display-only: a failure drops the grid, never the run.
- **P3a-6. Smoke colour.** One cool slate hue (159, 179, 200) with alpha on a log scale from 0.05 to 2.5 su, keeping
  warm white (likelihood), blue (links) and ember/amber/pine (node states) distinct. Nodes glow in text white with
  opacity ∝ min(conc / 2.5, 1).
- **P3a-7. Files from accepted phases touched (approved with the Phase 3a plan).** `core/context.py` (+`landscape`),
  `core/contracts.py` (+`Fires.new_causes`, `Fires.attempts`), `core/pipeline.py` (context landscape, ignition cause,
  `nodes.conc`, plume grid), `fire/ignition.py` and `fire/plume.py` (real class and `field` added; stubs unchanged),
  `record/frames.py` (grid encode/decode), `configs/default.yaml`; dashboard `CommandMap.tsx`, `MapLayers.tsx`,
  `MapTools.tsx`, `mapView.ts`, `layers.ts`, `types.ts` (additive), `theme.css`.

## Phase 3b design choices

- **P3b-1. Legacy stays default.** SPEC §5: defaults reproduce the report unless marked advanced, and M11 is advanced;
  golden runs need M12. So `plume: stub` (legacy) stays the default and scenarios opt in to `plume: real`. The Gaussian
  model also narrows plumes (σ_y ≈ 5.5 m at 50 m in class C), which changes which nodes see smoke.
- **P3b-2. Upwind floor (ASM, from LIT [3]).** C = max(M11(x, y), 0.1 · M11 centreline at the same distance d), so
  upwind and far-crosswind nodes see about 10%; this reproduces the legacy 0.25 su at 50 m upwind.
- **P3b-3. Source scaling (DER).** The Gaussian source follows the legacy M9 ramp and lognormal Q_max, rescaled so that
  a legacy-strength source gives the calibrated Q: Q(τ) = Q_cal · q(τ) · e^{−50/L} / 2.5. Calibration is at the
  reference wind (10 m median 1.5 m/s → u_c 0.6 m/s) in class C; at other winds concentration scales with 1/u_c, as
  M11 prescribes, whereas the legacy model ignores wind speed except for delay.
- **P3b-4. Stability by time of day (ASM).** Class C from 06:00 to 18:00, E otherwise (SPEC default "C by day, E at
  night"); intermittency uses the same mean-one lognormal as M12.
- **P3b-5. Model-card notes.** Header model-card rows gain `notes` (the stage's snapshot at run start), which records
  `q_cal` as SPEC §5.5 asks. Additive; the dashboard's model card shows them.
- **P3b-6. Files from accepted phases touched.** `core/pipeline.py` (model-card `notes`), `stages.py` (import),
  `fire/plume.py` (docstring only), `configs/default.yaml` (plume parameters; state unchanged); dashboard
  `ModuleHealth.tsx`, `MapTools.tsx`, `types.ts` (additive).

## Phase 4 design choices

- **P4-1. Baselines follow the oracle line by line.** P0 (M22, `detect/baselines/fixed.py`): threshold μ + 3σ from the
  first simulated day (population σ), alarms on rising edges with a 30-minute per-node refractory. P1 (M23,
  `detect/baselines/v1.py`): the report's "v1 as written" — EWMA with the |z| ≥ 3 freeze and no cap, CUSUM with
  k = 0.5 and h = 8.8 (Siegmund, M23), a hit only when the node's refractory counter is 0 (then set to 30 and
  decremented the same tick), confirmation by ≥ 2 candidates within R and 30 minutes. Unit tests feed identical arrays
  to these stages and to the oracle's own functions (loaded from `reference/`) and require exact agreement.
- **P4-2. v1 hindsight initialisation (LIT, oracle behaviour).** The oracle initialises the EWMA from the mean and
  variance of the whole first day and then runs the filter over that same day. In a tick loop this needs the future,
  so the stage buffers day 1, initialises at its end and replays the buffer through the filter. No alarm is possible
  before `start_min` (end of day 1 in recordings, TEST0 in experiments, as the oracle starts G = 0 at TEST0).
- **P4-3. Protocol stream.** `"protocol"` is appended at the end of `STREAMS` (rule 7) and is used only by the harness
  for day types and protocol fires, so every module stream is unchanged.
- **P4-4. Pipeline split (approved with the plan).** `Simulation.tick()` now calls `step_signals(t)` (weather →
  sensor, same order) and `step_baselines(x)`; `prepare()` runs the setup modules. The headless harness calls exactly
  the same code without building frames. Recordings of every earlier scenario are unchanged except for the new
  `p0_alarm` / `p1_alarm` events.
- **P4-5. Reference values.** The report's numbers live only in `engine/tests/golden/report_reference.json`
  (rule 10). The harness copies them into `summary.reference` with the label "FIRENET–PRAHARI report (SIM)" so the
  Results tab can draw them as hollow markers beside ours; they are never computed or edited by the engine.
- **P4-6. Golden outcome (SPEC §9.3), recorded as it came out — nothing was tuned.** Five seeds (11, 22, 33, 44, 55),
  legacy mode, 30 test days each:

  | Pipeline | This simulator | Report | Oracle, same 5 seeds |
  | --- | --- | --- | --- |
  | P1 false incidents / month | **136.2** (126.2–146.8) | 132 (123–143) | 132.4 |
  | P0 false incidents / month | **340.6** (324.6–357.2) | 291 (277–307) | 291.4 |
  | Confirmed within 3 h | P0 314/324, P1 322/324 | — | — |

  P1 passes. P0 misses the report's interval. The engine's baselines match the oracle exactly on identical inputs
  (P4-1), so the gap is statistical, not a code difference. False alarms are strongly clustered (haze episodes and
  heavy-tailed bursts), so the report's interval — an exact Poisson interval of the pooled count — is much narrower
  than the true seed-to-seed spread. Running the oracle itself over seeds 11–30 gives P0 = 321.9 per month (sd 49.6,
  standard error of a 20-seed mean 11.1) and P1 = 139.1 (sd 11.0, SE 2.5); the report's 5-seed P0 of 291 is a low
  draw of the oracle's own distribution. Our engine necessarily uses its own per-module streams (N-c), so it cannot
  reproduce the oracle's exact draws, only its distribution.
- **P4-7. Equivalence check (engine vs oracle, seeds 11–30, quiet pass, no fires).** Both implementations were run
  over the same 20 seeds (per-seed values in `engine/tests/golden/equivalence_seeds11_30.json`):

  | Pipeline | Oracle mean (sd, SE) | Engine mean (sd, SE) | Difference | Welch t, p | Mann–Whitney p |
  | --- | --- | --- | --- | --- | --- |
  | P0 | 321.9 (49.6, 11.1) | 310.9 (71.2, 15.9) | −11.0 | −0.57, 0.58 | 0.71 |
  | P1 | 139.1 (11.0, 2.5) | 141.8 (9.2, 2.1) | +2.7 | 0.84, 0.40 | 0.44 |

  No detectable difference in either pipeline; medians are 321 vs 326 (P0) and 142 vs 138 (P1). Individual seeds
  differ, as expected with separate streams (golden seed 55: engine 387, oracle 131; seed 11: 299 vs 322).
  Conclusion: the P0 miss is a 5-seed sampling effect of clustered false alarms, and the engine reproduces the
  report's model. The golden test keeps the report's intervals as written (SPEC §9.3); P0 is expected to fail it
  with these seeds and that failure is documented here rather than hidden by tuning or seed picking. A fairer
  acceptance for a stochastic, overdispersed rate would compare distributions over ≥ 20 seeds, as above — proposed
  for the developer's decision, not adopted.
- **P4-8. Map glyphs.** The "Baselines" layer marks P0 alarms with a grey triangle and P1 alarms with a grey ring for
  30 simulated minutes; grey is reserved for the old approaches and ember for PRAHARI (SPEC §6.3).
- **P4-9. Files from accepted phases touched (approved with the Phase 4 plan).** `core/pipeline.py` (split, baseline
  stages, alarm events), `core/rng.py` (+`protocol`), `core/contracts.py` (re-export of `BaselineAlarms`), `cli.py`
  (`experiment`), `stages.py` (imports), `configs/default.yaml` (baseline states and `evaluation` parameters);
  dashboard `App.tsx`, `CommandMap.tsx`, `MapTools.tsx`, `mapView.ts`, `types.ts` (additive), `layers.ts`,
  `store.ts`, `scripts/sync-recordings.mjs`.

## Phase 5 design choices

- **P5-1. Real node stages beside the stubs.** `ttc_real.py` (M24 with the 180-minute freeze cap and winsorised
  resumption, M25 fast residual from a ring of cumulative sums), `qcc_real.py` (M26), `cusum_real.py` (M28) and the
  pure `tuning.py` register as `real` under the existing names; the stub files are unchanged. `score` stays the stub:
  with one channel and c = 1 it is exactly M27 (S = −ln p); M29 health weights are advanced (Phase 9).
- **P5-2. Oracle semantics, verified on identical inputs.** Unit tests require exact agreement with the report
  simulation's `ewma_z(lockup_fix=True)` (from the end of day 1), `fast_resid`, `conformal_p`, `cusum`, `cm_mask`
  and `tune_h`, and with its P1t path (h, candidates, confirmations). Inherited details: day-1 hindsight
  initialisation of the slow baseline (as P4-2); a candidate only when the refractory counter is 0 (set to 30 and
  decremented the same tick); bisection over [0.5, 400] for 18 steps returning the upper bound.
- **P5-3. QCC calibration (LIT).** Default `window: frozen`: each node's set per 4-hour bin grows over the first 14
  days, then is frozen, sorted once and searched with one row-offset `searchsorted` per tick (0.14 ms). While a set
  grows, p is computed against the set so far and the score is then appended (online conformal; the report
  simulation uses the full 14 days with hindsight, which only changes p during the calibration days — never used
  for tuning or testing). `window: sliding` (the SPEC's 28-day maturity window) is available as an advanced option
  (ASM). Scores are the raw fast residual, as in the report. A tick with any missing reading is not learned.
- **P5-4. Causal common-mode mask.** The report pads its mask ±60 minutes with hindsight; a tick loop tunes at the
  end of the tuning window, so the 60 minutes after it are not available. Only candidates in the last hour of tuning
  that precede a common-mode episode starting in the first hour of testing are affected. Evaluation statistics use
  the full hindsight mask, as the report does.
- **P5-5. Erratum E-7 (applied in SPEC 1.0.3 after the developer's go-ahead).** SPEC M28 said "|z| ≥ 3"; the report simulation uses the one-sided
  z ≥ 3 (smoke only raises readings). The engine follows the simulation (`cm_z`); SPEC text aligned.
- **P5-6. `h_default` (DER, SPEC §10 fallback).** Until the tuning window has been seen (every demo recording), the
  node CUSUM uses 218.7 — the mean tuned h of the report simulation on seeds 11–55 (238.1, 230.3, 204.8, 232.1,
  188.0). P1t uses 400: the simulation's bisection ends at its cap on all five seeds.
- **P5-7. Common-mode input via the context.** `RunContext.z_slow` (additive) carries the latest TTC slow z; the
  pipeline sets it in `step_node` and the real CUSUM reads it for the M28 exclusion, so no stage signature changed.
  P1t computes the mask from its own capped z, as the report does.
- **P5-8. Framework scenarios pin the stub node layer.** `smoke`, `siting_*` and `fires_day*` exist to show the
  framework with clean stub signals and stub detectors (Phase 0 acceptance: the stub pipeline confirms the scripted
  fire); they now pin `ttc`, `qcc`, `cusum: stub`, as they already pinned the signal stubs. `signals_3day` runs the
  real node layer (its comment updated), and the new `node_3day` adds a day-3 fire. The Phase 0 runner test that
  used `qcc` as its "no real implementation yet" example now uses `energy`.
- **P5-9. Acceptance outcome (golden seeds 11, 22, 33, 44, 55; quiet pass, 30 held-out test days each).**

  | | This simulator | Target | Report simulation, same seeds |
  | --- | --- | --- | --- |
  | QCC exceedance at p ≤ 0.01 | **1.10%** (0.61–1.58% per seed) | 0.8–2.0% | 1.54% (1.16–1.69%) |
  | Node-local false candidates / node / 30 d | **0.65** (median 0.70; 0.03–1.02) | 0.5–1.5 | 1.70 (median 1.24; 0.81–4.25) |
  | Tuned h (mean) | 251.8 (seed 22 at the 400 cap) | — | 218.7 |
  | P1t false incidents / month | **14.4** (11.3–18.1) | report 18.6 (15.0–22.8) | 18.6 |
  | P1t confirmed within 3 h | 197/324 = 61% | report 59% (53–64) | — |

  Both Phase 5 criteria pass on the means. The report simulation itself misses criterion 2 on these seeds (its seed
  55 gives 4.25).
- **P5-10. Finding: the M28 exclusion can miss a common-mode rise right after a long one.** Seed 22's tuning window
  holds a second network-wide rise straight after a long haze episode. During the first episode the capped slow
  baseline inflates s² (winsorised updates), so in the second only about 10% of nodes reach slow z ≥ 3 — below the
  25% threshold — while every node's −ln p is near its floor (mean S ≈ 5). The 67 near-simultaneous candidates are
  counted as node-local, so the bisection ends at its cap (h = 400) and that seed's test-period local rate drops to
  0.03. The engine's slow z equals the report's exactly (P5-2), so this is the method's behaviour, not a code
  difference; the report simulation's seed-55 outlier looks like the same effect. Not tuned away (rule 10).
  Proposal for the developer: define the common-mode signal on the detection evidence itself (share of nodes with
  p ≤ 0.01, or with G above a fraction of h) — an advanced option, left for approval.
- **P5-11. P1t equivalence (report simulation vs engine, seeds 11–30, quiet pass).** Our 5-seed P1t (14.4 per
  month) sits just below the report's interval (15.0–22.8), as P0 did in Phase 4. Over 20 seeds (per-seed values in
  `engine/tests/golden/equivalence_p1t_seeds11_30.json`): report simulation 18.3 (sd 7.0, SE 1.6), engine 17.1
  (sd 6.8, SE 1.5); difference −1.2, Welch t −0.55, p 0.58; Mann–Whitney p 0.66. No detectable difference; both
  bisections end at or near the 400 cap on almost every seed. The golden test keeps the report's interval as written
  and is expected to miss with these five seeds; nothing was tuned.
- **P5-14. Warm-start recordings (follow-up, developer's call delegated).** Every demo recording was a young
  network (≤ 3 days of calibration, `h_default`), so in `node_3day` only one node raised a candidate at the fire and
  the stub quorum of two never confirmed it. The report's operating point assumes 14 calibration and 14 tuning days.
  `record.from_day` (ASM, default 0) simulates from day 0 but writes frames and traces only from that day; the
  header gains `record_from_min` and its model card is taken after the first recorded tick, so it shows the tuned h.
  New scenario `node_mature` (31 days, recorded from day 29): QCC sets of 3,360 per bin, tuned h 226.6, P1t at its
  cap; the day-31 fire gives candidates at nodes 41 (+67 min) and 31 (+108 min) and is confirmed at +134 min by the
  stub quorum. No model parameter changed (rule 10). Cold recordings (`from_day: 0`) are byte-identical to before.
  Pros: the demo shows the system at its designed operating point. Cons: about 65 s to generate instead of 7 s.
  `node_3day` stays as the young-network view (the floor falling day by day).
- **P5-12. Dashboard.** Node tab: the existing readout gains "Calibration n / floor p_min"; below it the lazy-loaded
  Node Inspector (SPEC View 2) stacks reading with the slow baseline, fast residual, p-value on a log axis with the
  falling floor 1/(n+1), CUSUM G with h and the node's candidates (ember = the map's candidate state), and the health
  weight. Frames gain `nodes.baseline` and `nodes.n_cal` (additive). The Results tab gains a node-layer table with
  per-seed values, the means and the targets.
- **P5-13. Files from accepted phases touched (as in the Phase 4 pattern).** `core/pipeline.py` (`step_node`,
  `baseline_p1t`, `p1t_alarm` events, two frame keys), `core/context.py` (+`z_slow`), `stages.py` (imports),
  `eval/experiments.py` and `cli.py` (P1t, `node_metrics`), `configs/default.yaml` (module states, parameters),
  `configs/experiments/golden.yaml`, the five framework scenarios (pins) and `signals_3day.yaml` (comment),
  `tests/unit/test_runner.py` (example module), `tests/golden/test_golden_baselines.py` (P1t, node acceptance);
  dashboard `App.tsx`, `NodePanel.tsx`, `ResultsPanel.tsx`, `results.ts`, `series.ts`, `types.ts` (additive).

## Phase 6 design choices

- **P6-1. Real edge stages beside the stubs.** `detect/prahari/edge_real.py` (cluster M30, SCMR M31, Fisher M32),
  `decide_real.py` (SRP M33 legacy, RAQ M34) and `escalate_real.py` (M35) register as `real` under the existing
  names; the stub files are unchanged. `learn` stays the stub, which *is* the M34 Sellke–Bayarri–Berger bound (the real
  M36 fit is Phase 9).
- **P6-2. Legacy clustering form by default (N-b).** `cluster.form: legacy` reproduces the report simulation's
  `confirm`: every new candidate forms a cluster of the window's candidate nodes within R of it (candidates within a
  tick processed in node order), SCMR compares that node's neighbourhood with the network, and the quorum is counted
  per candidate. A unit test feeds identical candidate streams to our chain and to `confirm` and requires identical
  alarms. `form: components` (M30 as written: connected components, SCMR over every node within R of any member) is
  the advanced option.
- **P6-3. Candidate p-values for Fisher (DER).** M32 states p_i ≈ r·ΔT; with r = 1 per node per 30 d (the M28 target)
  and ΔT = W = 30 min, p_i = 6.9e-4 for every member. p_C therefore depends on the cluster size only, which is why
  the legacy quorum and the Bayes rule agree (acceptance 2: 2 nodes on dry days — BF 4.2e3 × 1e-4 = 0.42 ≥ 0.01 —
  and 3 on wet days). The members' own QCC p-values stay in the trace for the reader.
- **P6-4. RAQ forms.** `raq.form: legacy` (default, the report) decides by the day-type quorum; `bayes` by
  BF(p_C)·odds ≥ C_FA/C_miss. Either way the frame's `prior.quorum` is the reverse view the SPEC asks for, and the
  trace records the rule used (`bayes.method`: "legacy quorum", "bayes" or "fixed quorum (stub)").
- **P6-5. Legacy prior and day types (M33).** Day types are drawn per day with P(dry) = 0.5 from a new `srp` random
  stream (appended at the end, rule 7) and can be overridden per day (`srp.day_type_overrides`). The experiment
  harness overrides them with its protocol's day types so fires, prior and quorum share one calendar. The full M33
  integral (λ × p_s over the cluster area) needs a per-cluster prior and is left for the regime work (Phase 9).
- **P6-6. Escalation (M35, ASM details).** Clusters join the incident holding any node within R of them; levels only
  rise until the incident clears after 120 minutes without candidates; a new alert is raised when an incident first
  reaches CONFIRMED or ESCALATED. Growth is measured from the incident's size at the start of the 30-minute window
  (or its first cluster, if younger). On the 1.4 km demo map the "another confirmed incident within 1 km" rule
  escalates almost any second incident; that is the SPEC's rule, kept as written. The SPEC's prior-only WATCH has no
  cluster to attach to; the header strip shows the day type and quorum instead.
- **P6-7. Contracts (additive).** `Clusters.anchor`, `Clusters.n_recent`, `Raq.method`, `Decision.incident`;
  `Decision.OPTIONAL` lets the runner's per-cluster length check accept an empty `incident` from the stub
  (`runner.expect_len` now iterates `dataclasses.fields`). Traces gain `incident` and `anchor`; alerts gain
  `incident`; the explanation template gains the legacy-RAQ wording.
- **P6-8. Live mode.** `server/app.py` (FastAPI) and `server/live.py`: the engine runs in a thread through a
  `LiveWriter` that implements the recording writer's interface, so the WebSocket carries exactly a recording's lines
  (header, frames, traces, footer). Frames are paced to a chosen speed (×60 = one simulated minute per second; 0 = as
  fast as possible). `POST /modules` queues a switch that is applied between recorded frames via
  `Simulation.switch_module`, which rebuilds the module's Slot (stateful modules restart from `reset`, e.g. QCC loses
  its calibration) and marks the frame with a `module_switch` event. The dashboard's `LiveSource` wraps each snapshot
  of the stream in a `RecordingSource`, so every view works unchanged; `updateSource` keeps the clock and follows the
  live edge. Replay stays the default and needs no server (rule 11).
- **P6-9. Mechanism switches in replay.** SPEC View 5 asks for pre-recorded variants; they are named
  `<scenario>__<module>-<state>.prs.jsonl.gz`. One variant ships: `node_mature__scmr-stub` (the SPEC's demo moment —
  switch SCMR off during haze). Switches without a variant are disabled in replay and work in live mode.
- **P6-10. `node_mature` day 31 is a dry, busy day.** With random day types, day 31 drew "wet, quiet", so the rule
  needed three nodes and the two-node fire was not confirmed. The scenario now sets day 31 dry (the SPEC §11
  storyboard's condition, stated in the scenario file); no model changed. Day 30's haze gives 3 alerts with SCMR and
  15 without (SIM).
- **P6-11. Golden P2 (seeds 11, 22, 33, 44, 55) and the equivalence check — recorded as it came out, nothing tuned.**

  | P2 PRAHARI | This simulator | Report (SPEC §9.3) | Result |
  | --- | --- | --- | --- |
  | False incidents / month | 3.4 (2.0–5.4); per seed 5, 5, 2, 0, 5 | 6.4 (4.4–9.0) | below the interval |
  | Confirmed within 3 h | 246/324 = 75.9% (M44 CI 71–80%) | 83% (79–87%) | below the interval |

  **Code equivalence.** Fed the report simulation's own seed-11 fire-pass signals, our node and edge stages give its
  exact result: tuned h 238.13 and 54 of 63 fires confirmed, as the report simulation. The legacy edge also matches
  its `confirm` alarm for alarm on synthetic candidate streams (unit test).

  **20 seeds (11–30), engine vs report simulation** (`engine/tests/golden/equivalence_p2_seeds11_30.json`):
  false incidents 6.25 vs 7.20 per month (Welch p 0.48, Mann–Whitney p 0.84) — no detectable difference;
  detection 74.0% vs 82.2% (Welch p 0.03, Mann–Whitney p 0.005) — the engine detects less. Diagnosis:
  - *Haze in the calibration and tuning windows.* Detection falls with the number of haze episodes in days 0–27
    (correlation −0.57 engine, −0.36 report simulation; about −3.8 points per episode pooled). The engine's seeds
    happened to hold 3.3 episodes on average against 2.25 for the report simulation's seeds (the expected value is
    2.8; each is within ordinary sampling range). That accounts for about 4 of the 8 points. The mechanism is the
    P5-10 one: haze inflates the calibration tails and can push the tuned h to its cap (engine seed 24: 37%).
  - *How smoke reaches the nodes.* The report simulation gives every injected fire its own constant random wind
    direction and speed; the engine carries smoke on its continuous weather wind (mostly from the WSW, drifting during
    a fire). Swapping in the engine's quiet background under the report simulation's injected fires (seeds 12–19)
    gives 82.7% (410/496) against 79.2% for the engine's own fires on the same seeds (351/443): about 3.5 points.

  Proposed, pending the developer's approval because it touches the accepted plume stub (rule 4): a legacy
  `plume.wind: per_fire` option (random constant direction θ ~ U(0, 2π) and speed U(30, 120) m/min per fire, as the
  report simulation injects fires) for the golden preset only, keeping the weather-driven wind for demos; then rerun
  the 20-seed comparison. Logged in `KNOWN_ISSUES.md` (improvement backlog).
  *Follow-up (Phase 7):* approved and built as P7-1; it did not raise detection, and a direct footprint check showed
  the fires were not the cause — the transport attribution above is withdrawn (P7-9).
- **P6-12. Files from accepted phases touched.** `core/pipeline.py` (`step_edge`, `last_env`, `switch_module`,
  trace extras, alert incident), `core/runner.py` (optional fields in `expect_len`), `core/contracts_edge.py`
  (additive fields), `core/trace.py` (legacy-RAQ template, `extra`), `core/rng.py` (+`srp`), `stages.py`,
  `eval/experiments.py` (P2, shared day types), `configs/default.yaml`, `configs/experiments/golden.yaml` (+P2),
  `configs/scenarios/node_mature.yaml` (day 31), `engine/pyproject.toml` (extras); dashboard `App.tsx`,
  `AlertsPanel.tsx`, `store.ts` (additive), `theme.css`.

## Phase 7 design choices

- **P7-1. Per-fire wind for the golden presets (approved after Phase 6).** The plume stub gains
  `plume.wind: per_fire` (default `weather`, so every demo scenario and recording is unchanged): each fire, when it
  is first seen, draws a constant downwind direction θ ~ U(0, 2π) and speed u ~ U(30, 120) m/min from the plume's own
  stream, exactly as the report simulation's `inject_fires`. Fires already end after 180 minutes
  (`ignition.fire_lifetime_min`), so no duration parameter was added. All experiment presets set it. With it, the
  engine's protocol fire is the report simulation's fire term for term: the same Q_ref (2.5 su at 50 m, L = 40 m),
  lognormal Q_max (σ 0.5), growth τ_g = 10 min, directional factor, transport delay, mean-one intermittency
  (σ 0.5), linear sensor response and uniform placement over the grid. A unit test checks that a fire's wind stays
  constant and that the option is opt-in.
- **P7-2. Offline edge replay (DER, exact).** A pass now records the node evidence S = −ln p (float32, T × N), the
  share of nodes with slow z ≥ 3 and the node candidates (`eval/offline.py`, `ScoreRecorder`). The edge variants
  are replayed from the recorded candidates through the same registered stages (`registry.build`), so P2, P2-SCMR
  (SCMR stub) and P2-RAQ (RAQ stub) share one pair of passes instead of three. Unit tests show that the offline
  replay equals the live edge alarm for alarm, and that the offline tuned h and replayed candidates equal the live
  CUSUM's. The live P2 edge path in the harness was removed; recordings still run the live edge (`step_edge`).
- **P7-3. Pipeline groups.** An ablation that changes the node layer (P2-QCC: `qcc: stub`; P2-TTC: `ttc: stub`) needs
  passes of its own; an edge ablation does not. `_groups` sorts the requested pipelines by their node-layer
  overrides. The baselines (P0, P1, P1t) ride in the unmodified group's passes.
- **P7-4. Operating dial.** For each target r (false node candidates per node per 30 days) the harness re-tunes h
  from the recorded quiet-pass evidence with the live tuner's own bisection and common-mode mask (`tuning.tune_h`,
  `cm_mask`), replays the CUSUM from the test start (`cusum_replay`) and the edge, and pools each point like a
  pipeline. The golden preset uses the report simulation's four targets: 1 per 60, 30, 14 and 7 days per node. The
  point at 1 per 30 days is the design point; a unit test checks it equals P2 exactly.
- **P7-5. Results layout.** Each preset writes `results/<preset>.json` (committed) and per-seed files (ignored), then
  `eval/report.py` rebuilds `results/summary.json`: the golden preset is the primary table; the node ablations join
  its pipelines; the spacing sweep and the 20-seed sweep are attached (`spacing`, `seed_sweep`); `sources` says which
  file supplied what; `table` lists every pipeline in the report's order beside the report's row. The report values
  still live only in `engine/tests/golden/report_reference.json` (rule 10). `.gitignore` admits the four preset files.
- **P7-6. Golden tests extended.** Besides P0–P2 false incidents and the node targets, the golden suite now checks
  the four ablations' false incidents against the report's intervals, P0–P2 detection against the report's
  intervals (§9.3 gives both), and — where the report gives a point value without an interval (ablation detection,
  spacing) — that the report's value falls inside our own M44 interval. `PRAHARI_JOBS` runs seeds in parallel.
  Run in this session (16.5 minutes, `PRAHARI_JOBS=3`): 6 pass, 15 miss — the misses are the P7-9 findings. After the
  legacy ablations (P7-12): 5 pass, 16 miss — P2-QCC detection now misses (67.3% vs 78%).
- **P7-7. `--jobs N`.** Seeds run in N forked processes (`multiprocessing`, standard library). Each seed's streams
  come from its own master seed, so the output does not depend on N (checked: the seed-11 golden P2 row is the same
  with 1 and 4 jobs).
- **P7-8. Results view.** Main charts show P0–P2; a separate ablation chart shows P2 and each variant with its
  confirmation rate; `ExperimentCharts.tsx` adds the operating dial (false incidents per month on a log axis
  against median minutes to confirm, one point per target, the design point enlarged) and the spacing chart
  (confirmed and single-node shares within 3 h with M44 intervals, report values as hollow diamonds). Every value is
  read from `summary.json`; every chart footer names its seeds and simulated days. Value labels now sit past the
  interval and per-seed ticks, and legends sit below titles, so nothing overlaps.
- **P7-9. Results, recorded as they came out — nothing tuned.** Golden seeds 11, 22, 33, 44, 55 (`results/summary.json`):

  | Pipeline | False incidents / month | Report (SPEC §9.3) | Confirmed within 3 h | Report |
  | --- | --- | --- | --- | --- |
  | P0 | 340.6 (324.6–357.2) | 291 (277–307) | 317/324 = 97.8% | 95% (93–97) |
  | P1 | 136.2 (126.2–146.8) | 132 (123–143) — inside | 318/324 = 98.1% | 99% (98–100) — inside |
  | P1t | 14.4 (11.3–18.1) | 18.6 (15.0–22.8) | 198/324 = 61.1% | 59% (53–64) — inside |
  | P2 | 3.4 (2.0–5.4) | 6.4 (4.4–9.0) | 231/324 = 71.3% | 83% (79–87) |
  | P2-QCC | 30.8 (26.1–36.1) | 17.4 (13.9–21.5) | 242/324 = 74.7% | 78% — inside our interval |
  | P2-TTC | 8.2 (5.9–11.1) | 11.8 (9.0–15.2) | 234/324 = 72.2% | 66% |
  | P2-SCMR | 5.0 (3.2–7.4) | 12.0 (9.2–15.4) | 232/324 = 71.6% | 84% |
  | P2-RAQ | 5.4 (3.6–7.9) | 10.0 (7.4–13.2) | 250/324 = 77.2% | 88% |

  Every ablation raises false alarms above P2, as in the report. Spacing (seeds 11, 22, 33): confirmed within 3 h
  63% / 33% / 5% at 70 / 100 / 150 m (report 85 / 56 / 13%); single-node alerts 96% / 85% / 59%; false alarms are
  the same at every spacing because R = 1.6 s scales with the grid. Operating dial (1 per 60, 30, 14, 7 days per
  node): 4.0 / 3.4 / 7.6 / 14.2 false incidents per month, 222 / 231 / 267 / 280 of 324 confirmed, median 67 / 62 /
  55 / 46 minutes. The first two false-alarm points invert (20 against 17 incidents in total; seed 44 gives 1 against
  0) because a higher h shifts when node candidates coincide; detection and latency are monotone.

  **Per-fire wind (P7-1) did not raise detection.** Golden P2 went from 246/324 to 231/324 (same fire times and
  places, new winds and intermittency draws). The fire model now equals the report simulation's term for term, and a
  direct check on seed 11 confirms it: the mean number of nodes a fire lifts by ≥ 0.5 / 1 / 2 su in the fast residual
  is 8.24 / 5.19 / 2.92 in the engine and 8.17 / 5.10 / 3.02 in the report simulation. The Phase 6 attribution of half
  the gap to transport (P6-11) is therefore withdrawn; that background-swap difference (+3.5 points) was within
  sampling error (z ≈ 1.3).

  **20 seeds (11–30), engine against the report simulation** (`engine/tests/golden/equivalence_p7_seeds11_30.json`):
  false incidents agree for P0, P1, P1t, P2, P2-SCMR and P2-RAQ (every Welch p > 0.4); detection agrees for P0, P1
  and P1t, and is lower for the pipelines with the conformal node layer — P2 72.8% vs 82.2% (Welch p 0.015,
  Mann–Whitney p 0.002), P2-SCMR 73.3% vs 82.4%, P2-RAQ 79.6% vs 86.1%.

  **Where the difference sits.** On seed 11 the quiet fast residual in the calibration days has a much heavier upper
  tail in the engine (2.2% of minutes above 1 su; report simulation 0.29%); with haze switched off it falls to
  0.18%. A haze-heavy calibration window widens the conformal reference set, so a fire's lift earns a less extreme
  p-value and fewer neighbours cross h within the 30-minute window (seed 11's missed dry-day fires show one node
  re-triggering while its neighbours stay below h). The haze model is the same in both simulators; the engine's
  seeds 11–30 drew 66 episodes in days 0–27 (56 expected, Poisson p ≈ 0.10) against the report simulation's 45.
  **Independent check on fresh seeds 31–50** (same file, `seeds31_50`): false incidents are identical for P2 (7.05 vs
  7.05 per month) and agree for every pipeline; P2 detection is 79.4% (902/1136) against 84.4% (1019/1208), a
  smaller difference that is not significant on its own (Welch p 0.16, Mann–Whitney p 0.29). Over all 40 seeds the
  PRAHARI pipelines still detect about 7 points less (P2 76.1% vs 83.3%, Welch p 0.007) while P0 and P1t agree
  (p 0.97 and 0.65). Conclusion: part of the Phase 6 gap was sampling of haze-heavy seeds; a smaller residual
  difference in the node layer's calibration remains, open in `KNOWN_ISSUES.md` with the next diagnostic.
- **P7-10. Ablation definitions.** Our ablations replace a mechanism by its registered stub, the SPEC's meaning and
  the same switch the dashboard's View 5 uses: P2-QCC = `qcc: stub` (Gaussian p-value of the slow z, k 1.5 on −ln p);
  P2-TTC = `ttc: stub` (v1 slow residual without the freeze cap, conformal); P2-SCMR = `scmr: stub`; P2-RAQ =
  `raq: stub` (fixed quorum). The report simulation defines the two node ablations differently: "minus conformal"
  runs the CUSUM on the MAD-scaled fast residual with k 0.5, and "minus two-timescale" uses a conformal p-value of
  the capped slow z. The edge ablations are defined identically, and their 20-seed false alarms agree with it
  (P2-SCMR 9.4 vs 10.05, P2-RAQ 9.8 vs 10.15). Legacy forms of the node ablations would need additions to accepted
  Phase 5 modules (rule 4) and are proposed in `KNOWN_ISSUES.md` for approval.
- **P7-11. Files from accepted phases touched.** `fire/plume.py` (per-fire wind, approved), `eval/experiments.py`
  (groups, recorders, offline edge, dial, jobs, spacing), `cli.py` (`--jobs`, dial and spacing lines),
  `configs/default.yaml` (plume keys, experiment `dial`/`spacings`), `configs/experiments/golden.yaml`,
  `tests/smoke/test_experiment.py` (new results layout), `tests/golden/test_golden_baselines.py` and
  `report_reference.json` (ablations, spacing — the report's values only), `.gitignore`, `CLAUDE.md` (commands);
  dashboard `ResultsPanel.tsx`, `results.ts`, `results.test.ts` (additive).

- **P7-12. Legacy node ablations (approved after Phase 7; small additive changes to accepted Phase 5 modules).**
  `experiment.ablation_form: legacy` (set by the `ablation` preset; default `stub`) builds P2-QCC and P2-TTC as the
  report simulation does, through three parameters whose defaults leave every existing run unchanged:
  `ttc.detect_on: slow` (the detection residual is the capped slow z), `qcc.form: robust_z` (z = (r − median) /
  (1.4826·MAD) per node over the calibration days, p = Φ(−z)) and `cusum.statistic: z` with `cusum.k_z: 0.5` (the
  CUSUM adds the signed z). The signed z travels in two optional contract fields, `PValues.z` and `Scores.z`
  (rule 3, additive); the score stub passes it on. `_groups` keys each ablation on its module or parameter
  overrides. Unit tests (`test_ablation_legacy.py`) check each form against the report simulation's `ewma_z`,
  `gauss_z`, `cusum` and `tune_h` on identical inputs. Default recordings: every frame identical; only the model
  card's source text changed, and the recordings were regenerated for it.
- **P7-13. Legacy ablation results.** On the report simulation's own seed-11 signals the engine's legacy chains give
  its results: P2-QCC exactly (h 210.229, identical candidate lists, 14 false incidents per month, 48 of 63 fires);
  P2-TTC 7 vs 8 false incidents and 46 vs 48 fires with the same h (400, the cap). The P2-TTC difference is fully
  explained by day 1: the report simulation computes the first day's slow z against a baseline taken from the whole
  first day (look-ahead), which a causal engine cannot; replacing those day-1 values with the engine's warm-up z makes
  the candidate lists identical (897 = 897). Kept as is (ASM, one of 14 calibration days).
  Golden seeds (`results/ablation.json`): P2-QCC 8.8 (6.4–11.8) false incidents per month, 218/324 = 67.3% confirmed
  (report 17.4, 13.9–21.5; 78%); P2-TTC 8.4 (6.1–11.4), 194/324 = 59.9% (report 11.8, 9.0–15.2; 66%). The stub
  forms had given 30.8 and 8.2 (P7-9). Over seeds 11–30 against the report simulation
  (evidence file, `legacy_ablations`): false incidents agree — P2-QCC 10.25 vs 12.40 per month (Welch p 0.48), P2-TTC
  12.75 vs 11.20 (p 0.44); detection shows the same seed-driven gap as P2 — 69.2% vs 74.4% (p 0.08) and 60.6% vs
  69.8% (p 0.05).
- **P7-14. Reverse swap and model checks — where the P2 detection gap comes from.** A 2 × 2 design over seeds 11–30
  ran every combination of background (engine; report simulation) and fire set (engine protocol fires; the report
  simulation's injected fires) through the same engine chain (evidence file, `reverse_swap`). The two anchor cells
  reproduce the known results exactly (862/1185 and 1000/1228). Confirmed within 3 h:

  | | Engine fires | Report-simulation fires |
  | --- | --- | --- |
  | Engine background | 862/1185 = 72.7% | 950/1228 = 77.4% |
  | Report-simulation background | 961/1185 = 81.1% | 1000/1228 = 81.4% |

  Both factors contribute: the engine backgrounds cost 4.6–7.4 points (Mann–Whitney p 0.02–0.10) and the engine fire
  sets 2.0–4.8 points (paired p 0.11 and 0.001). Neither is a model difference:
  - *Fires.* The fire sets agree on distance to the nearest node (27.0 vs 26.4 m, KS p 0.62), nodes within 100 m
    (6.1 vs 6.2) and time of day (KS p 0.99); they differ in the share of fires on wet days, which need three nodes
    (21.9% vs 16.7%, KS p 0.08; the protocol expects 20%) — a day-type sampling difference.
  - *Haze.* 200 independent 58-day haze histories from each model agree in episodes (5.76 vs 5.68, KS p 1.0),
    durations (449 vs 453 min, p 0.86) and amplitudes (1.64 vs 1.64 su, p 0.69).
  - *Background as a whole.* On 60 fresh seeds (101–160) the calibration-period tail of the quiet fast residual —
    the quantity the conformal p-values rank against — does not differ significantly: share of node-minutes above
    1 su 0.80% vs 0.65% (KS p 0.51), mean per-node 99.9% quantile 1.83 vs 1.74 su (p 0.27), 99.97% quantile 2.35 vs
    2.29 su (p 0.18). The engine is slightly higher on all three, so a small background difference cannot be ruled
    out at this sample size.
  Conclusion: the code is the same (C1 and Phase 6), the fire model and the haze model are the same, and the
  detection gap on seeds 11–30 comes from which worlds those seeds happened to draw — haze-heavy calibration windows
  in the engine's, and fewer wet-day fires in the report simulation's.

## Phase 8 design choices

- **P8-1. Real radio and energy only where they are asked for.** `comms` and `energy` stay `stub` in
  `configs/default.yaml`, the golden presets and every earlier scenario; the new `gateway_outage` and `cloudy_days`
  scenarios (and live mode, through the module switches) run them `real`. Every earlier recording keeps identical
  frames (checked by comparing all nine), and every result is unchanged. This is the SPEC's own escape-hatch
  arrangement for an optional phase and keeps legacy mode intact.
- **P8-2. M38 shadowing and TS011 relays in the links setup module.** `links.shadowing_sd_db` (default 0, keeping
  Phase 1's links; 6 dB in the Phase 8 scenarios, SPEC ASM) draws a fixed X_σ per node–gateway and node–node pair from
  a new `links` stream. `Links` gains optional `prx_all`, `sf_all` (every gateway, for re-routing), `relay`,
  `relay_sf`, `relay_prx`. A node with no direct link uses the strongest neighbour whose node-to-node link closes
  and which has its own direct link (node-to-node paths use the same forest law, ASM). The header's `links.relay`
  appears only when some node needs a relay.
- **P8-3. Comms model (M39, M40, ASM details).** Candidate frames (confirmed) and hourly heartbeats (unconfirmed, a
  fixed random minute per node) start at a uniform moment in the minute on one of three channels (IN865 default
  plan); collisions follow pure ALOHA on the same channel and SF with a 6 dB capture rule; lost candidate frames retry
  up to 3 times after U(1, 10) s. Frames that spill past the minute, later retries and relay second hops are resolved
  with the next minute's frames; all frames share one collision domain. Heartbeats are not queued during an outage.
  Loops run over frames (a few per minute), not over nodes (rule 8).
- **P8-4. Store-and-forward and outages.** `comms.outages` lists gateway outages. A node whose gateway is out
  re-routes to another gateway if one closes, otherwise keeps candidate frames (up to `queue_max`) and sends them
  when a route returns — as a burst that can itself collide and retry. Delivered candidates reach the edge in the
  minute they arrive.
- **P8-5. Energy model (M41–M43).** Draw per power mode (BME688 scan current, ESP32 1 s per minute at 80 mA and
  10 µA asleep) plus, per frame sent, 44 mA for its time on air and 11 mA for two 0.1 s Class A receive windows (ASM
  window length). Harvest on a half-sine from 06:00 to 18:00 that integrates to A η G k (1.5 Wh on a clear day);
  scripted or random cloudy days scale the day by U(0.1, 0.4); optional per-node canopy spread (ASM). Store 4.556 Wh
  (two 3,000 F cells, 2.7 → 1.35 V). Modes: ULP below 20%, off below 5%, back on at 10% (ASM hysteresis). A node that
  is off neither senses (no sensor current) nor transmits; its node-layer arrays keep running (ASM, display only).
- **P8-6. Pipeline additions (accepted Phase 0/6 file, additive).** The energy stage receives `(t, weather,
  delivered)` instead of `t` (the stub ignores it); `ctx.links` and `ctx.energy_mode` (new optional `RunContext`
  fields) connect setup, comms and energy; frames gain `nodes.queue`, `nodes.mode` and `gateways_down` only when the
  real modules run; packets of skipped minutes are carried into the next written frame with their own minute `t`.
  Contracts gain optional fields only: `Delivered.queue`, `Delivered.down`, `EnergyState.mode` and the `Links` fields
  above (rule 3). New streams `links` and `energy` are appended (rule 7).
- **P8-7. A runner test changed its example.** `test_real_falls_back_to_stub_while_no_real_exists` used `energy`
  as the module without a real implementation; it now uses `satellite` (no real model until Phase 9).
- **P8-8. Scenario settings.** `cloudy_days` starts nodes at 30% with canopy spread 0.6 so that three cloudy days
  visibly take weaker nodes into ULP; these are scenario settings stated in the file, not model parameters.
  `gateway_outage` reuses `node_mature` (seed, haze, day-31 fire) and places the outage across the fire.
- **P8-9. Energy chart.** `prahari energy` writes `results/energy.json` from the configuration (no random draws);
  `report.combine` attaches it to `summary.json`. The chart draws lollipops (a stem from the axis minimum to a dot)
  because a log axis has no zero for bars to start from. It uses one series hue: a grey second colour for MQ-2 failed
  the palette validator (ΔE 14.4 against the blue, below the normal-vision floor of 15), and each row is already
  named on the axis. The footer states that the chart involves no random draws instead of listing seeds.
- **P8-10. Results.** Acceptance 1: 61.7 ms at SF7 and 1,482.75 ms at SF12 (SPEC 1,482.8). Acceptance 2: pure-ALOHA
  success 82.4 / 61.5 / 37.8% at G = 0.1 / 0.25 / 0.5 against 81.9 / 60.7 / 36.8%. Acceptance 3: the 0.5 Wh-per-day
  node stops after 8.66 days and empties after 9.11. Energy: BME688 0.114 / 0.178 / 0.415 Wh per day (ULP / low
  power / standard), MQ-2 22.9. `gateway_outage`: node 41's candidate waits 23 minutes and the fire is confirmed at
  14:48; `cloudy_days`: the lowest store falls to 19% and 15 nodes scan in ULP at 02:00 on day 5 (all SIM).
- **P8-11. Found: the edge clusters by arrival minute.** In `gateway_outage` the delayed frame lands in the same
  30-minute window as a later one, so the fire is confirmed earlier (14:48) than with a perfect link (15:14, `node_mature`).
  A deployed edge would use the detection time each frame carries. Changing the accepted Phase 6 cluster stage is
  proposed, not done (`KNOWN_ISSUES.md`).
- **P8-12. Files from accepted phases touched.** `comms/pathloss.py` (shadowing, relays, all-gateway SFs),
  `comms/lorawan.py` and `energy/budget.py` (docstrings; the stub's input name), `core/{pipeline,context,contracts,
  contracts_world,rng}.py`, `record/world.py` (header relay), `stages.py`, `eval/report.py`, `cli.py`,
  `configs/default.yaml`, `tests/unit/test_runner.py` (P8-7), `.gitignore`; dashboard `types.ts`, `series.ts`,
  `results.ts`, `mapView.ts`, `CommandMap.tsx`, `MapTools.tsx`, `NodePanel.tsx`, `NodeInspector.tsx`,
  `ExperimentCharts.tsx`, `theme.css` (all additive).

## Phase 9 design choices

- **P9-1. Real Phase 9 modules only where they are asked for.** `faults`, `score` (M29), `satellite` (M37) and
  `learn` (M36) stay `stub` in `configs/default.yaml`, the golden presets and every earlier scenario. The ignition
  lightning term has no storms by default, `srp.form` stays `legacy` and `regime` stays null. The new scenarios switch
  on what they show. Every earlier recording was regenerated for the new header block (`regime`) and compared line by
  line: identical frames, except the two noted in P9-2.
- **P9-2. Arrival-time fix (approved by the developer; closes the Phase 8 item).** `Delivered` gains `t_detect`, the
  minute each candidate was raised; the real comms stage fills it from the frame it delivers. The cluster stage keeps
  2W of history and gathers, for each arrival, the candidates whose *detection* minutes lie within W of it. With the
  perfect-link stub arrival and detection coincide, so legacy results are unchanged. `gateway_outage` now confirms at
  15:14, the same minute as `node_mature` with a perfect link (SIM). In `cloudy_days` two decision traces change their
  SCMR network share (0.42 against 0.40 and 0.34 against 0.33); no decision changes.
- **P9-3. M37 satellite race.** Overpasses at the SPEC's fixed local times; the first pass at which the M37 fallback
  area A_15 (τ/15)² has reached 500 m² sees the fire with probability 0.8; the alert follows after U(40, 60) min
  (MODIS) or U(60, 90) min (VIIRS). The whole plan is drawn at ignition from the `satellite` stream and published as a
  `satellite_plan` event, so the race timeline needs no look-ahead. The area model assumes an unattended fire keeps
  growing after the sensing model's 180-minute smoke window (ASM, labelled illustrative on the chart).
- **P9-4. M21 faults.** Poisson faults at the SPEC rates plus scripted ones. A dropout holds the last reading and sets
  `Readings.missing` (new optional field) so no NaN reaches the pipeline. Stuck-at duration 6 h to 3 days (ASM).
- **P9-5. M29 health weights in a real `score` stage.** Fresh data (5 min), not stuck (rolling 60-minute variance
  above 1% of the node's median hourly variance), neighbour consensus q (robust z of the node's slow baseline against
  its neighbours', over a day). Two corrections found while testing acceptance 3: hours in which a node was already
  stuck are stored as missing (NaN) so they do not pull its own reference variance towards zero, and a flat window
  below 1e-9 su² counts as stuck whatever the history (ASM). Without them the stuck node's weight recovered after
  about 13 hours. For speed, neighbour lists are padded arrays, the hourly reference is cached and q is refreshed every
  10 minutes (0.77 → 0.14 ms per tick).
- **P9-6. The dashboard's fault glyph is the system's view.** A node is drawn as "fault" when its health weight is
  below 0.1 (`display.abstain_c`), not when a fault was injected; injected faults are shown as `fault_start` events.
  This is what an operator would see: "this sensor abstains".
- **P9-7. Lightning (M3 λ_light) and the SCMR relaxation.** Storms are scripted discs with a strike rate; each strike
  ignites with probability strike_ignition_prob × p_s(FFMC) inside the forest. `ctx.storm` stays set for 180 minutes
  after the storm ends (`storm_hold_min`, ASM) because the fires it started are still being detected then; without the
  hold SCMR still held clusters after the storm. While the flag is set the prior carries `lightning` and SCMR uses
  ρ ≥ 1.5 instead of 3 (SPEC M31, an untested hypothesis, labelled ASM).
- **P9-8. M33 integral prior as an option.** `srp.form: integral` computes each cluster's prior from the M3 map, the
  M8 sustained-fire probability and the activity curve, scaled so the map expects `fires_per_30d` sustained fires (ASM,
  1 per 30 days). Two-node odds come out at 3.9e-5 to 1.1e-4 (SIM), close to the legacy 1e-4; no scenario uses it yet.
- **P9-9. Regime Cards.** `configs/regimes/{india,canada,usa,australia}.yaml` set weather, interface weights, haze and
  radio plan, plus a `regime_card` identity block that the recording header carries. The card values are illustrative
  (ASM) apart from the SPEC §8.1 facts they encode (lightning on for Canada and Australia; IN865, US915, AU915).
- **P9-10. M36 learning loop.** `learn: real` loads a fitted model file and replaces the SBB bound with LR̂ once the
  model has seen K ≥ 10 burns. The fit is logistic regression with an L2 penalty (λ = 1 on standardised features, ASM)
  by IRLS in NumPy — no new dependency. Training uses only windows that pass SCMR, the population M34 is applied to: a
  first fit on all windows learned that network-wide haze windows (large X, large |C|, low ρ) are not fires and so
  weighted X almost to zero; restricted to SCMR-passed windows, X and |C| carry the weight. Quiet windows come from
  every training seed's quiet pass (quiet data is cheap in the field; burns are the scarce resource K counts).
- **P9-11. Rules are compared at a fixed false-alarm budget.** For the bound and for each K the threshold on the M34
  posterior odds is the most permissive one whose false incidents on the held-out quiet passes stay within 3 per month
  (TGT, near P2's golden rate). The confirmation rate and median latency at that threshold are the learning curve. The
  threshold is set on the evaluation seeds' quiet passes (as a fixed-FPR comparison is), never on their fire passes.
- **P9-12. Runner fallback test retargeted.** `test_runner.py`'s "real module falls back to its stub" case used
  modules that now have real implementations (energy in Phase 8, satellite in Phase 9); it now uses `growth`.
- **P9-13. Learning-curve bug found and fixed before the curve was accepted.** The first full run gave 49, 54, 37, 37
  and 71% for K = 5–100 (SIM). The training loop stopped reading seeds once it had K burns, so the quiet windows
  changed with K (91 up to K = 50, 209 at K = 100) and each fit had a different prior. Every K now uses all training
  seeds' quiet windows; the result is 49 → 68, 68, 68, 71% (acceptance 2). This is a correction, not tuning: nothing
  else changed (same seeds, budget, penalty and features), and the buggy numbers are kept in the journey page.
- **P9-14. The learning preset.** Training seeds 41–42 (119 protocol fires), held-out seeds 51–53, K = 5, 10, 20, 50,
  100, budget 3 false incidents a month; calibration maturity on seeds 11 and 22 with 1, 2, 4, 7 and 14 days of quiet
  data, 14 tuning and 10 test days. The seeds were chosen before any run, apart from 11 and 22, which are the first two
  golden seeds. The deployed legacy quorum is reported on the same held-out runs as a reference (80% at 7.7 false
  incidents a month, outside the budget), not as a point on the curve. `results/learning.json` and the K = 100 model
  are committed; the other model files are regenerated by the preset.
- **P9-15. `sensor_fault` uses the M37 satellite.** With the stub's fixed 90-minute delay its satellite alert (14:30)
  came before the confirmation (14:49) and the race timeline would have shown a satellite win that no overpass
  schedule allows. Switching it to `real` changes only the satellite events (checked frame by frame).
- **P9-16. Files from accepted phases touched.** `core/{pipeline,contracts,contracts_edge,context}.py`,
  `comms/lorawan_real.py` (`t_detect`), `detect/prahari/{edge_real,decide_real,score,learn}.py` (the detection-minute
  window; lightning SCMR threshold and the integral prior; stubs accepting the new inputs), `fire/ignition.py`
  (storms), `satellite/overpass.py` (docstring), `eval/{offline,report}.py`, `stages.py`, `cli.py`,
  `configs/default.yaml`, `.gitignore`, `tests/unit/test_runner.py` (P9-12); dashboard `App.tsx`, `CommandMap.tsx`,
  `NodeInspector.tsx`, `NodePanel.tsx`, `RecordingPicker.tsx`, `ExperimentCharts.tsx`, `types.ts`, `results.ts`,
  `theme.css`, `scripts/sync-recordings.mjs` (all additive). Every earlier recording was regenerated for the header's
  `regime` block.

## Phase 10 design choices

- **P10-1. Storyboard steps reuse validated recordings.** SPEC §11 names `dry_afternoon_ignition`, `quiet_week` and
  `wet_morning_haze`. Steps 1 and 5–7 use `satellite_race` (the mature network, a dry, busy day 31, a 14:00 fire, the
  M37 satellite); step 2 uses `node_mature`'s day 29 (no fire; 220 P0 and 1,083 P1 alarms that day, SIM) instead of a
  week-long recording. The mapping lives in `dashboard/public/storyboard.json` and the Phase 10 journey page. Copies
  under the §11 names would duplicate 3–4 MB files without showing anything new.
- **P10-2. `wet_morning_haze` is the one new storyboard scenario.** `node_mature`'s world, calibration and haze, with day
  30 set to wet and quiet (quorum 3) and only that day recorded. On `node_mature`'s dry haze day the RAQ stub (fixed
  quorum 2) and the real RAQ decide alike, so the R key would show nothing. Results (SIM): 2 haze alerts with SCMR
  (158 of 174 decisions held), 6 with SCMR off, 3 with RAQ off. `__scmr-stub` and `__raq-stub` variants back S and R.
- **P10-3. Launchers serve `dist/` with Python's standard-library server.** Browsers refuse module scripts and `fetch()`
  from `file://`, so a double-clickable `index.html` would need a different, single-file bundling set-up. Python is
  already needed for the engine; `npx vite preview` is the fallback. No new dependency. The server sends recordings as
  `application/gzip` without `Content-Encoding`; the dashboard detects gzip by its magic number either way.
- **P10-4. Presenter mode reads its storyboard at run time.** `storyboard.json` in `public/` (copied to `dist/`) can be
  edited on the demo laptop without a rebuild; it is validated on load (problems shown in the caption strip) and by a
  Vitest test (valid keys, existing recordings, ≤ 180 planned seconds). `?presenter` makes the page open step 1 and
  stops the recording picker's default load from racing it.
- **P10-5. The caption strip sits in the layout flow.** A floating overlay covered the time controls and the race
  timeline's footer (rule 15); under the header it covers nothing.
- **P10-6. Captions carry no result values.** They say what to look at; the numbers come from recordings and
  `results/summary.json` (rule 10). The only figure, 29 node cells per VIIRS pixel, is (375 m / 70 m)² from
  configuration (DER). Files from accepted phases touched: `dashboard/src/App.tsx` (the top strip and overlay),
  `RecordingPicker.tsx` (`?presenter`), `theme.css`.

## Release 1.0 (final audit and hardening)

- **R1-1. Outputs are the asset; the audit changes none of them.** Before any change the SHA-256 of every recording
  and results file and the golden-suite outcome (5 of 21, the documented pattern) were recorded. After the changes
  every recording regenerates byte for byte (after the header refresh of R1-11), `prahari energy` and the learning
  preset reproduce their JSON exactly,
  and the golden suite gives the same outcome. No model, parameter or default changed.
- **R1-2. Two dashboard defects fixed.**
  - (a) At 1280 × 720 the map collapsed to zero height when a recording shows the extra Phase 8 layer rows. The map
    now keeps 360 px and the left column scrolls.
  - (b) The race timeline claimed a race ("The satellite alert came 44 min before PRAHARI confirmed") in recordings
    whose satellite module is the stub, a fixed 90-minute delay that is not the M37 model. It now labels the stub
    and claims nothing. The recordings are unchanged; `satellite_race` and the other Phase 9 scenarios, which run
    M37, are unaffected.
- **R1-3. Error boundaries.** Each view is wrapped so one failing view cannot blank the page on stage. The notice
  shows the error (nothing is hidden) and resets on a new recording or tab.
- **R1-4. Incomplete recordings open.** A last line cut off mid-write is skipped and the recording is marked
  incomplete; any other malformed line is still an error. The engine never writes such a file (atomic writes, R1-5);
  this covers interrupted copies.
- **R1-5. Atomic writes.** `write_atomic` (temporary file, then `os.replace`) for recordings, health files and results
  JSON. The bytes are identical; a failed write keeps the previous file.
- **R1-6. Configuration value checks and CLI errors.**
  - `check_values` rejects impossible run and world values with the key named. Every shipped configuration passes.
    A grid with a non-square node count, which used to degrade the siting module at run time, is now a
    configuration error.
  - The CLI turns configuration, file and interrupt errors into one line with exit codes 2, 1 and 130.
  - Presets resolve from any folder; `--seeds` and `--jobs` are validated.
  - The live server rejects a negative speed and non-positive days (422).
- **R1-7. Dependency lock.**
  - `engine/requirements-lock.txt` records the exact Python packages the release was tested with.
  - `pyproject.toml` keeps its lower bounds and adds upper bounds below the next major version of each package.
    These are not tested, so they are excluded rather than trusted.
  - `package.json` gains `engines: node >= 20`, and `npm ci` installs the existing lock.
  - Version 1.0.0 in both manifests.
- **R1-8. `scripts/check_all.sh`** wraps the existing checks (tests with warnings as errors, type check, build, doc
  links, byte-for-byte regeneration of every recording) so the release can be re-verified at any time. It adds no
  tool.
- **R1-9. Documentation.**
  - Docstrings for the framework, contracts, evaluation code, CLI and server (about 100).
  - The stage-class convention (the `equation`, `tag` and `description` attributes on the model card) documented
    instead of adding a hundred redundant class docstrings.
  - The root README rewritten for the finished project.
  - `core/pipeline.py` is 314 lines after docstrings, slightly over rule 14's guide of about 300. It is accepted
    code, so it is not split (rule 4).
- **R1-11. Stale recording headers refreshed.**
  - The first full release check found 16 committed recordings whose header differed from what the code produces:
    the model-card `source` text of `learn`, and in the two lightning recordings also `srp`. Both texts were extended
    by Phase 9 configuration edits after those recordings were last regenerated.
  - Proof it was not the audit: regenerating `smoke` from the pre-audit commit (`1e87162`) gives the same bytes as the
    audited code.
  - The 16 recordings were regenerated. Each was compared with its predecessor: only that header text differs, and every
    frame and trace line is identical.
- **R1-12. Second audit: latest load wins.** A reproduced race let a slow recording load overwrite a newer choice,
  across presenter keys, the picker, the mechanism switches and the live stream. One token in the store (`beginLoad`
  and `isLatestLoad`) now guards every load. A live stream stops once something else is opened. No output
  change; `loadToken.test.ts` and a browser reproduction cover it.
- **R1-13. Second audit: damaged `.gz` files.** The readable part of a truncated `.gz` opens as an incomplete recording,
  consistent with R1-4. Nothing readable gives "the .gz file is damaged or incomplete", and files that are not
  recordings say "not a PRAHARI recording". Files touched: `store.ts`, `PresenterOverlay.tsx`, `RecordingPicker.tsx`,
  `MechanismSwitches.tsx`, `LivePanel.tsx`, `sources/parseRecording.ts`; no engine file.
- **R1-10. Files from accepted phases touched** (all narrow, listed for review):
  - engine: `core/{config,contracts,contracts_edge,contracts_world,contracts_baselines,clock,context,health,runner,
    registry,rng,trace,pipeline}.py`, `record/{writer,frames,reader,world}.py`, `cli.py`, `eval/{experiments,report,
    learning,node_metrics,energy_table}.py`, several stage modules (docstrings only), `server/{app,live}.py`,
    `pyproject.toml`;
  - dashboard: `App.tsx`, `Footer.tsx`, `RaceTimeline.tsx`, `race.ts`, `sources/parseRecording.ts`, `theme.css`,
    `package.json`, `package-lock.json`;
  - `README.md`.

## Documentation

- **Doc-1. A documentation set in `docs/` (developer request after Phase 5).** `docs/README.md` indexes four
  groups: `guide/` (overview, background, glossary, setup, troubleshooting, demo walkthrough), `architecture/`
  (system, engine, models, data contracts, dashboard, testing), `journey/` (one page per phase with its challenges,
  decisions, trade-offs and resolutions, plus cross-cutting lessons and a decision register) and `results/`
  (validation). Written in the project's own words from the code, tests, outputs and these logs; numbers are quoted
  from simulator outputs and labelled SIM. CLAUDE.md rule 16 and SPEC 1.0.3 §7 make it a deliverable of every phase.
  `DECISIONS.md`, `PROGRESS.md` and `KNOWN_ISSUES.md` stay the terse logs of record; the docs explain them.

## Dependencies beyond CLAUDE.md rule 13

- **Dep-1.** `@vitejs/plugin-react` (dev): standard React support for Vite.
- **Dep-2.** `vitest` 5 (dev): dashboard unit tests, named in SPEC §9.1. Version 5 because ≤ 4.1.10 carries advisory GHSA-82fw-gwwq-j7x9 and npm 10.9 fails to resolve 4.1.11's optional peers; `npm audit` reports 0 vulnerabilities.
- **Dep-3.** `@fontsource/barlow-condensed`, `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono`: bundle the §6.3 fonts locally for offline use.
- **Dep-4.** `@types/node`, `typescript` (dev): type checking for `npm run build`. React is pinned to 18.x as SPEC §6.1 requires.
- **Dep-6 (Phase 6).** `fastapi`, `uvicorn` (named in rule 13) plus `websockets` (uvicorn's WebSocket backend) as the
  optional `server` extra; `httpx` in the `dev` extra, needed by FastAPI's test client. The engine and the replay
  dashboard do not depend on any of them.
- **Dep-5 (Phase 2).** `echarts` 6.1 (named in rule 13). Version 6.1 because 5.x carries advisory GHSA-fgmj-fm8m-jvvx (XSS); `npm audit` reports 0 vulnerabilities.
