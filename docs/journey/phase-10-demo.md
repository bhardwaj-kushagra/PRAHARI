# Phase 10 — Demo hardening

## Goal

A demo that cannot fail on stage: the three-minute storyboard of SPEC §11, driven by single keys, from a laptop with no engine and no internet.

## What was built

- **Storyboard recordings.** One new scenario, `wet_morning_haze`, with two variants for the S and R keys: `__scmr-stub` and `__raq-stub`. The other steps reuse recordings that already show them (table below).
- **Presenter mode (SPEC §6.4):**
  - **Keys.** 1–9 jump to the storyboard steps. Each step sets its recording, time, speed, map layers and tab, then plays or holds. Space plays and pauses, S and R switch SCMR and RAQ through the pre-recorded variants, F toggles full screen, and Esc hides the caption.
  - **Caption strip.** It sits under the header and shows the step and the line to say.
  - **Code.** `dashboard/src/presenter.ts` holds the pure step and key logic; `components/PresenterOverlay.tsx` applies a step to the stores.
- **Storyboard as data.** `dashboard/public/storyboard.json` holds the nine steps: keys, bookmarks (day and time), speed, layers, tab, planned seconds and captions. It is edited without rebuilding. A Vitest test checks that it is valid, that every recording it names exists, and that the plan fits in three minutes.
- **Launchers.**
  - `scripts/demo.sh` (macOS and Linux) and `scripts/demo.ps1` with `scripts/demo.cmd` (Windows).
  - Each builds the dashboard if needed, serves `dashboard/dist` on `http://localhost:8765` with Python's standard-library server, and opens the browser at `?presenter=1`, which starts on step 1.
  - `npx vite preview` is the fallback when there is no Python.
- **`DEMO_CHECKLIST.md`.** The day before, at the venue, the keys on stage, and what to do when something fails.

**Storyboard map (SPEC §11 name → recording):**

| Step | §11 recording | Recording used | Bookmark |
| --- | --- | --- | --- |
| 1 | `dry_afternoon_ignition`, start | `satellite_race` (satellite pixels on) | day 31, 13:50 |
| 2 | `quiet_week` ×600 with P0 | `node_mature` (baselines layer on), a day with no fire | day 29, 06:00, ×600 |
| 3 | `wet_morning_haze` | `wet_morning_haze` (new) | day 30, 10:00, ×600 |
| 4 | same, SCMR off | `wet_morning_haze__scmr-stub` (new) | day 30, 10:00, ×600 |
| 5–7 | `dry_afternoon_ignition` | `satellite_race`: ignition, why panel, race timeline | day 31 14:00 ×600; 15:15; 23:25 |
| 8, 9 | Results; model card | the open recording | — |

## How it works

A step is a small record in `storyboard.json`. Pressing its key:

1. Loads the recording once per session; later jumps use a cache and take a few hundredths of a second.
2. Seeks to the bookmark and sets the speed.
3. Merges the step's map layers and opens its tab.
4. Clears the selected node and alert, so the Alerts tab shows the latest alert.
5. Plays or holds, and scrolls a named element (the race timeline) into view.

S and R reuse the Phase 6 replay variants. They open the same recording with the mechanism flipped, keep the clock, and say so in the strip.

The launchers only serve files. The dashboard already carries its fonts, charts and recordings, and a scan of the build finds no address it would fetch from outside.

## Challenges and issues

1. **`file://` cannot work.** Opening `dist/index.html` directly fails: browsers refuse module scripts and `fetch()` from `file://`. Making it work would need a different bundling set-up for a single file.
2. **The fixed caption overlay covered things.** The first version floated over the page. It hid the play and speed buttons, and a long caption hid the race timeline's footer, which must show seeds and days (rule 15).
3. **No wet day in the existing recordings.** `node_mature`'s haze day is a dry, busy day, where the RAQ stub (quorum 2) and the real RAQ agree. The R key would have shown no difference.
4. **The picker and presenter mode raced.** On `?presenter=1` both the recording picker (default: smoke) and step 1 opened a recording, and the one that loaded last won.
5. **Captions must not carry results.** A caption such as "45× fewer false alarms" would be a result value hard-coded outside the simulator's files (rule 10).

## Decisions and trade-offs

| Decision | Pros | Cons | Ids |
| --- | --- | --- | --- |
| Reuse existing recordings for steps 1, 2 and 5–7 instead of copies named as in §11 | no duplicated 3–4 MB files; the story matches what earlier phases validated | the names differ from §11 (mapped above and in `storyboard.json`) | P10-1 |
| New `wet_morning_haze` with SCMR and RAQ variants | both switches show a real difference on stage | three more recordings (about 1.2 MB each) | P10-2 |
| Serve `dist/` with Python's standard-library server | no new dependency; Python is already required for the engine | needs Python (or Node for the fallback) on the demo laptop | P10-3 |
| Caption strip in the layout flow, under the header | never covers controls or footers | the map area is a strip shorter while captions show | P10-4 |
| Qualitative captions; the numbers stay in the charts | no result hard-coded in text | captions say "far fewer" rather than a figure | P10-5 |

## Resolution

- **1:** The launchers serve `dist/`. The troubleshooting page and the checklist say never to open `index.html` directly.
- **2:** The strip moved into the layout flow. Screenshots of all nine steps show the controls and footers.
- **3:** `wet_morning_haze` sets day 30 to wet and quiet (quorum 3); otherwise it is `node_mature`'s world and haze. Results (SIM):
  - With SCMR, 158 of 174 decisions are held and 2 haze clusters still become alerts.
  - With SCMR off there are 6 alerts.
  - With RAQ off (quorum 2) there are 3, the extra one a 2-node cluster at 10:54.

  The caption says SCMR "holds what is common", not that it removes all of it.
- **4:** With `?presenter`, the picker leaves the first recording to presenter mode.
- **5:** Captions state what to look at; every number on screen comes from a recording or `results/summary.json`. The one number in a caption, 29 node cells per VIIRS pixel, is derived from configuration: (375 m / 70 m)².

## Acceptance results

| # | Test | Result |
| --- | --- | --- |
| 1 | Airplane mode: the static build opens and plays all storyboard steps | **pass**:<br>• Played through the launcher's server with every non-local request blocked: 0 external requests.<br>• All nine steps reached their recording, time and tab, each ready within 0.4 s.<br>• S and R opened the right variants. |
| 2 | A full rehearsal of §11 takes 3 minutes or less | **pass** — 170.1 s with each step held for its planned time (170 s planned; 180 s allowed) |
| 3 | No console errors | **pass** — none during the rehearsal |

Also: 204 engine tests (21 golden skipped unless enabled) and 53 dashboard tests pass; `wet_morning_haze` is byte-identical on rerun.

## What to show

Run `scripts/demo.sh` (Windows: `scripts\demo.cmd`), press F, then 1 through 9. The keys and fallbacks are on one page in [../../DEMO_CHECKLIST.md](../../DEMO_CHECKLIST.md).
