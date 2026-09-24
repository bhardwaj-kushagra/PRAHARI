# CLAUDE.md — PRAHARI public site (branches `site-dev` and `site-live`)

This branch carries the **public, view-only website** of the PRAHARI-SIM dashboard, served at
`https://dashboard.firenet.live` by Cloudflare Pages. It is **not** where the simulator is developed. The simulator,
its science, experiments and results live on `main`, under `main`'s own `CLAUDE.md`. The branch model, the hosting
settings and the release steps are in `docs/site/README.md`; the site's log of changes and decisions is
`docs/site/LOG.md`.

## Branches

| Branch | Purpose | Who writes to it |
| --- | --- | --- |
| `main` | Simulator: engine, science, experiments, results, laptop demo | Science work only; never site changes |
| `site-dev` | Draft of the website; all site work happens here (or on a feature branch merged into it) | Site work |
| `site-live` | What Cloudflare publishes; always a copy of a tested `site-dev` commit | Only a promotion pull request `site-dev → site-live` |

Never commit directly to `site-live`. Never merge a site branch into `main`.

## Before writing any code in a session

1. Read `docs/site/README.md` and the latest entries of `docs/site/LOG.md`.
2. State in a few bullets what you will change, which files you will touch and how you will check it. Wait for "go"
   unless told to proceed.

## The rules

1. **Dashboard only.** Site work changes `dashboard/`, `docs/site/`, this file and hosting files (`.node-version`,
   `dashboard/public/_headers`). It never edits `engine/`, `configs/`, `server/`, `reference/`, `recordings/` or
   `results/` by hand. New recordings, results or engine behaviour reach the site **only** by merging `main` into
   `site-dev`.
2. **Add, don't rewrite.** Put site-only behaviour in new files (`dashboard/src/site/`, separate style sheets), and
   keep edits to existing dashboard files to small, clearly marked switches. Every edit to a file that also exists on
   `main` is a possible merge conflict later; list such edits in `docs/site/LOG.md`. Unlike `main`'s rule 4, the
   dashboard's accepted phases **may** be changed here when the site needs it, but prefer the smallest change.
3. **No fabricated results.** Every number and chart comes from the recordings and results files produced on `main`.
   Never type a result value into the site, never edit a recording, never tune anything to make a chart look better.
4. **Label simulation.** Every view keeps the SIMULATION badge, and every chart footer keeps its seeds and simulated
   days. On a public site this matters more than on stage.
5. **Static and offline.** The site is static files only: no server, no database, no analytics scripts, no requests to
   third-party hosts (fonts stay bundled). The optional live engine stays hidden (`dashboard/src/site/siteConfig.ts`).
6. **Works on the hosting limits.** Cloudflare Pages: at most 20 000 files, each at most 25 MiB. Check new recordings
   against this before promoting.
7. **Minimal dependencies.** React, TypeScript, Vite, ECharts, zustand, as on `main`. Anything else needs a line in
   `docs/site/LOG.md` first.
8. **Tests with every change.** `npx tsc --noEmit`, `npx vitest run` and `npm run build` (in `dashboard/`) must pass,
   and the built site must open with no console errors, before any promotion.
9. **Escape hatch.** If a site change fights you for about three focused attempts, revert it on `site-dev`, write the
   symptoms in `docs/site/LOG.md` and move on. `site-live` keeps serving the last good version meanwhile.
10. **Document it.** Each session adds a dated entry to `docs/site/LOG.md`: what changed, which shared files were
    touched, check results, and whether it has been promoted. Write in the project's own words.

## Merging `main` into `site-dev` (science updates)

`git merge main` (or a release tag such as `v1.0.0`) on `site-dev`. The most likely conflict is this file, whenever
`main` has changed its own `CLAUDE.md`: keep the site version (`git checkout --ours CLAUDE.md`). Resolve any other
conflict in favour of `main` for engine, configs, recordings and results, and re-apply the site switch for dashboard
files (the list of shared-file edits is in `docs/site/LOG.md`). Then run the checks in rule 8.

## At the end of every session

- Add the entry to `docs/site/LOG.md` (rule 10).
- Tell the developer what to open: the `site-dev` preview address, or `npm run build && npm run preview` locally.
- If the change is ready, say so; the developer promotes it with a pull request `site-dev → site-live`.

## Useful commands

```text
cd dashboard && npm ci                         # install (Node 22, see .node-version)
cd dashboard && npx tsc --noEmit && npx vitest run && npm run build   # checks before promotion
cd dashboard && npm run preview                # serve the built site at http://localhost:4173
cd dashboard && VITE_LIVE_ENGINE=1 npm run dev # show the live-engine panel again (needs a local engine server)
git merge main                                 # on site-dev: bring in science updates
```
