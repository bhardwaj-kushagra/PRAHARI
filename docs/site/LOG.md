# Site log

Dated record of work on the public-site branches (`site-dev`, `site-live`): what changed, which files shared with
`main` were touched, check results, decisions, and whether the change has been promoted. Newest entry last. The branch
model and hosting settings are in [README.md](README.md).

## Edits to files shared with `main`

Kept here so a merge from `main` can be resolved quickly (take `main`'s file, re-apply the edit).

| File | Edit | Since |
| --- | --- | --- |
| `CLAUDE.md` | Replaced by the site rules | S1 |
| `dashboard/src/App.tsx` | Imports `LIVE_ENGINE`; renders `<LivePanel />` only when it is true | S1 |
| `dashboard/src/components/MechanismSwitches.tsx` | Imports `LIVE_ENGINE`; the disabled-switch tooltip mentions live mode only when it is true | S1 |

## 2026-09-24 — S1: branches and first site build

**Done:**

- `main` at `318fe4d` is the locked release 1.0. `site-dev` and `site-live` were created from it.
- The tag `v1.0.0` could not be pushed from the working environment (its git proxy accepts branch pushes only), so
  the developer created it on GitHub as a release. See S2 for where it landed.
- Live-engine panel hidden behind `dashboard/src/site/siteConfig.ts` (`VITE_LIVE_ENGINE=1` shows it again), with unit
  tests in `siteConfig.test.ts`.
- `dashboard/public/_headers`: `X-Robots-Tag: noindex, nofollow`, `nosniff`, a referrer policy, a one-year cache for
  `assets/` and a one-hour cache for `recordings/`.
- `.node-version` = 22 for the Cloudflare build.
- Site `CLAUDE.md`, this log and [README.md](README.md).

**Checks:**

- `tsc` clean; Vitest 58 passed (56 from release 1.0 plus 2 new); `npm run build` clean (the existing warning about
  the ECharts chunk being over 500 kB is unchanged).
- Built site: 51 MB in total, no file over 20 MB.
- Headless Chromium against the built site served locally: at 1280 × 720 the smoke recording plays, no live-engine
  panel, SIMULATION badge present, 0 console errors, 0 requests to other hosts. Presenter mode (`?presenter=1`) at
  1600 × 1000 opens on the storyboard with the same results.
- At a phone size (390 × 844) the page loads without errors, but the layout is the desktop one squeezed: the map is
  cut to a thin strip and the right panel runs off the screen. Recorded as the first open item.

**Decisions:**

- **S-1 Three branches** (`main`, `site-dev`, `site-live`). Pros: science and site work never block each other; the
  public site changes only on a deliberate promotion; drafts get a real preview. Cons: site edits to shared dashboard
  files can conflict when `main` is merged in. Mitigation: site behaviour in new files, and the table above.
- **S-2 Subdomain by CNAME** (`dashboard.firenet.live`) instead of moving the nameservers to Cloudflare. Pros: one
  record at name.com; the Blogger page at `firenet.live` is untouched. Cons: Cloudflare Access (log-in-only
  viewing) and a path such as `firenet.live/dashboard` would need the nameservers moved; neither is needed now.
- **S-3 Build-time switch for the live engine**, off by default on these branches. Pros: one small guard, no
  component deleted, easy to re-enable locally. Cons: a mention of live mode remains in code the site never shows.
- **S-4 Unlisted with a header, not `robots.txt`.** A crawler blocked by `robots.txt` never sees a `noindex`, and
  can still list the bare address; the header lets it read the page and drop it. Anyone with the link can still view
  the site.

**Open items:**

1. Mobile layout (see the phone check above).
2. Page title and description for link previews when the address is shared.

**Promoted:** yes, in pull request #4 (`site-live` at `b491c03`). The site is live at `https://dashboard.firenet.live`
(Cloudflare Pages project `firenet-dashboard`, custom domain active with SSL).

## 2026-09-24 — S2: verification and the second audit

**Checked on GitHub:**
- `site-live` (`b491c03`) has exactly the same content as `site-dev` at `1973f84`.
- The ruleset on `site-live` is active: pull request required, deletions restricted, force pushes blocked.
- The site-branch note (Site-1) is merged into `main` (pull request #5).

**Found:** `main` had moved on before the release was created.
- The second audit (pull request #3) was merged into `main` in the meantime, so the tag `v1.0.0` points to `578f1c8`,
  not `318fe4d`.
- The second audit fixes two dashboard problems:
  - a slower recording load no longer overwrites a newer one ("latest load wins");
  - a damaged `.gz` recording opens its readable part.
- The site, built from `318fe4d`, lacked both fixes.

**Done:**
- Merged the tag `v1.0.0` into `site-dev`, following the documented science-update path. One conflict, in the import
  lines of `MechanismSwitches.tsx`; both sides were kept.
- The two shared-file edits in the table above are unchanged.

**Checks:**
- `tsc` clean; Vitest 60 passed (the 58 of `v1.0.0` plus the 2 site tests); build clean.
- Headless Chromium at desktop, presenter and phone sizes: no live-engine panel, 0 console errors, 0 requests to other
  hosts.
- The public address could not be fetched from the working environment (its network policy blocks the host), so the
  developer checks it in a browser.

**Promoted:** not yet. The next pull request `site-dev → site-live` carries this merge.
