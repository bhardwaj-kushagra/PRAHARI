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

## Dependencies beyond CLAUDE.md rule 13

- **Dep-1.** `@vitejs/plugin-react` (dev): standard React support for Vite.
- **Dep-2.** `vitest` 5 (dev): dashboard unit tests, named in SPEC §9.1. Version 5 because ≤ 4.1.10 carries advisory GHSA-82fw-gwwq-j7x9 and npm 10.9 fails to resolve 4.1.11's optional peers; `npm audit` reports 0 vulnerabilities.
- **Dep-3.** `@fontsource/barlow-condensed`, `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono`: bundle the §6.3 fonts locally for offline use.
- **Dep-4.** `@types/node`, `typescript` (dev): type checking for `npm run build`. React is pinned to 18.x as SPEC §6.1 requires.
