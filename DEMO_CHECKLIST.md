# Demo checklist

A three-minute run of the PRAHARI-SIM storyboard ([docs/SPEC.md](docs/SPEC.md) §11). Everything runs from the laptop:
no engine, no server beyond a local static one, no internet. All numbers on screen are simulation output (SIM).

## The day before

- [ ] Pull the latest branch. If recordings or results changed, run `cd dashboard && npm run build` (it copies
      `recordings/` and `results/summary.json` in).
- [ ] Start the launcher once and run through all nine steps:
  - macOS or Linux: `scripts/demo.sh`
  - Windows: double-click `scripts\demo.cmd`
- [ ] Rehearse with a timer: the planned speaking time is 170 seconds (the `seconds` fields in
      `dashboard/public/storyboard.json`).
- [ ] Edit captions or bookmarks in `dashboard/dist/storyboard.json` for this talk only, or in
      `dashboard/public/storyboard.json` to keep them. No rebuild is needed; reload the page.
- [ ] Copy the whole `dashboard/dist/` folder to a USB stick as a spare.

## At the venue, 15 minutes before

- [ ] Turn on airplane mode, or disconnect Wi-Fi. The demo must not depend on the venue network.
- [ ] Start the launcher. The browser opens on step 1 with the caption strip under the header.
- [ ] Connect the projector and check the resolution. The layout is designed for 1600 × 1000 or larger; use the
      browser zoom (Ctrl/Cmd −) if the map or the right panel is cut off.
- [ ] Press F for full screen (press F or Esc to leave it).
- [ ] Press 1–9 once through to load every recording into memory; later jumps are then instant.
- [ ] Press 1 to return to the start.

## On stage

| Key | Step | What to do |
| --- | --- | --- |
| 1 | The forest and the satellite pixel | Point at the dashed 375 m pixel over the node grid |
| 2 | Fixed thresholds | It plays at ×600; let the baseline alarms pop for a few seconds |
| 3 | Haze on a wet morning | Plays at ×600; watch the "So far" counter under Mechanisms |
| 4 | SCMR off | Same haze with SCMR off: the counter climbs higher. S toggles SCMR and R toggles RAQ on the haze recording |
| 5 | A fire on a dry, busy afternoon | Plays at ×600: candidates pulse, then the confirmation |
| 6 | Every alarm explains itself | Walk through the "Why this alarm" panel |
| 7 | The satellite race | The strip under the map; read the headline |
| 8 | Results | Scroll the right panel down to the ablation chart if time allows |
| 9 | Everything here is simulated | The model card; close on "all numbers are SIM" |

Other keys: Space plays and pauses, Esc hides the caption strip, and ← → step one frame.

## If something goes wrong

| Problem | Do this |
| --- | --- |
| The browser did not open | Open `http://localhost:8765/?presenter=1` by hand |
| "Address already in use" | Another launcher is running: use that one, or run `PORT=9000 scripts/demo.sh` (Windows: `demo.ps1 -Port 9000`) |
| No Python on the machine | The launcher falls back to `npx vite preview` (needs Node.js and `npm install` done once) |
| A step shows the wrong view | Press its number again: every step resets its recording, time, speed, tab and layers |
| The caption strip covers too much on a small screen | Press Esc; the keys still work |
| The page is blank | Do not open `dist/index.html` directly (`file://` blocks module scripts); use the launcher |
| Everything fails | Use the spare laptop or the USB copy of `dashboard/dist/` (serve it with `python3 -m http.server --directory <folder>`), or talk through the charts in `docs/results/validation.md` |

## After the talk

- [ ] Note any question you could not answer in `docs/guide/06-demo-walkthrough.md` ("Likely questions").
