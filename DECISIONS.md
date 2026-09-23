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

## Dependencies beyond CLAUDE.md rule 13

- **Dep-1.** `@vitejs/plugin-react` (dev): standard React support for Vite.
- **Dep-2.** `vitest` 5 (dev): dashboard unit tests, named in SPEC §9.1. Version 5 because ≤ 4.1.10 carries advisory GHSA-82fw-gwwq-j7x9 and npm 10.9 fails to resolve 4.1.11's optional peers; `npm audit` reports 0 vulnerabilities.
- **Dep-3.** `@fontsource/barlow-condensed`, `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono`: bundle the §6.3 fonts locally for offline use.
- **Dep-4.** `@types/node`, `typescript` (dev): type checking for `npm run build`. React is pinned to 18.x as SPEC §6.1 requires.
