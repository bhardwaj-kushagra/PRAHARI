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
| `dashboard/src/App.tsx` | Imports `SiteBar`; renders it first inside `.top` | S3 |
| `dashboard/src/components/HeaderStrip.tsx` | Imports `SiteBrand`; it replaces the `PRAHARI-SIM` name span | S3 |
| `dashboard/index.html` | Title, description, link-preview (Open Graph) tags, icons | S3 |
| `dashboard/src/components/PresenterOverlay.tsx` | `goTo` exported; renders `<PresenterTouch />` inside the caption strip while a step is shown | S4 |

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

**Promoted:** yes, by the developer (the site runs the second-audit build).

## 2026-09-24 — S3: FIRENET and AgniWare branding, page title, first mobile layout

**Done:**
- **Branding.**
  - A thin bar above the header (`dashboard/src/site/SiteBar.tsx`, `site.css`) spells out FIRENET: **F**ire
    **I**dentification and **Re**sponse **N**etwork for **E**arly **T**racking.
  - The same bar credits the team: "a project by" the AgniWare logo, AgniWare, and a link to `https://www.agniware.tech`
    that opens in a new tab.
  - The header's name is now FIRENET, with PRAHARI-SIM beneath it. The SIMULATION badge and every footer are unchanged.
  - The names and the link live in `dashboard/src/site/brand.ts`.
- **Logo.**
  - The developer supplied the AgniWare logo as a JPEG on white. Its white background was removed so it sits on the
    dark theme, and it was cropped and saved as PNGs in `dashboard/public/brand/` (32, 96, 180, 192 and 512 px).
  - The site serves these copies itself; no request goes to another host.
  - The conversion used Pillow in a throw-away environment outside the repository, so Pillow is not a dependency of
    the site.
- **Page title and link previews** (`dashboard/index.html`):
  - title `FIRENET · PRAHARI-SIM · SIMULATION`, plus a description;
  - Open Graph and Twitter tags;
  - a 1200 × 630 preview image, `brand/og-image.png`: the FIRENET name, its expansion, the logo, the team and a
    SIMULATION badge, with no result numbers. It was drawn in the dashboard's own fonts and colours and captured with
    headless Chromium;
  - a favicon and an Apple touch icon.
- **Mobile layout** (`dashboard/src/site/mobile.css`, style overrides only; nothing changes above 1000 px wide):
  - At 1000 px and below the page scrolls instead of fitting one window. Header, map and side panel are stacked, and
    the time controls stay pinned to the bottom of the screen.
  - A wide table can no longer stretch the page sideways: the single column is `minmax(0, 1fr)`, and the side panel
    scrolls sideways on its own.
  - At 640 px and below: tighter spacing, larger buttons, one chart per row in Signals, and the presenter's keyboard
    hints are hidden.

**Challenges and how they were resolved:**
- **The first overrides did nothing.** `theme.css` is loaded after the site's style sheets, so on equal selectors it
  won. Every mobile selector now starts with `:root`, which outranks theme.css without `!important`.
- **The panels overlapped at tablet width.** The page grid still divided the window height into fixed rows, so the
  side panel's tabs were squeezed to one pixel and covered. On narrow screens the page now stacks in plain block
  layout.
- **Giant legend icons on phones.** A height rule meant for the map also matched the small icons in its legend. It
  now applies only to the map itself (`.map > svg`).

**Checks:**
- `tsc` clean; Vitest 63 passed (60 plus 3 in `brand.test.ts`: the highlighted letters spell FIRENET, the team link is
  https, and the page title, description and preview image are present); build clean.
- Headless Chromium at five sizes: 1280 × 720, presenter 1600 × 1000, tablet 820 × 1180, phone 390 × 844, and phone
  presenter. At every size: 0 console errors, 0 requests to other hosts, no sideways scroll, the logo loads, and the
  title is correct.
- Also tested: Play, and switching to Signals and back.
- At 1280 × 720 the map keeps the same height as before (301 px); the new bar is absorbed by the scrolling left
  column.

**Open items (mobile, next round):**
1. The Health & model card table is very long on a phone; a compact card per module would read better.
2. The race timeline's labels are tiny at phone width.
3. Presenter mode's keys 1–9 have no touch equivalent (for example, next and previous buttons).

**Promoted:** yes, by the developer.

## 2026-09-24 — S4: team website removed for now; second mobile round

**Done:**
- **AgniWare website left out (developer request).** The team name and logo stay; the link and every mention of
  `www.agniware.tech` are gone:
  - the bar's credit is plain text, not a link;
  - `TEAM` in `brand.ts` holds only the name;
  - the link-preview image was redrawn without the address.

  A test now fails if `agniware.tech` or a link comes back into the bar, the brand file, its styles or `index.html`.
  **To restore it later:** add the address to `TEAM`, turn the credit in `SiteBar.tsx` back into a link, redraw the
  preview card, and change that test.
- **Guided tour for visitors without a keyboard.**
  - A "▶ Guided tour · 9 steps" button in the bar starts the storyboard at step 1.
  - While a step is shown, the caption strip has Previous, Next and ✕ (end) buttons (`dashboard/src/site/PresenterTouch.tsx`).
    The steps and keys 1–9 are unchanged.
  - Wiring needed two small edits to `PresenterOverlay.tsx`, listed in the table above.
- **Mobile round 2** (`mobile.css`, style overrides only):
  - Tablets and phones:
    - the tour caption and its buttons stay pinned to the top of the screen while the page scrolls (the `.top` wrapper
      uses `display: contents` so the caption can stick to the page);
    - the race timeline keeps readable labels and scrolls sideways on its own instead of shrinking.
  - Phones:
    - the Health & model card becomes one card per module. The column names come from the column position, so
      `ModuleHealth.tsx` is unchanged;
    - the map's layer switches sit in one row that scrolls sideways (the map now starts about 150 px higher);
    - the timeline legend in the pinned controls is a single line.

**Checks:**
- `tsc` clean; Vitest 64 passed:
  - `brand.test.ts`: the website test replaces the https test;
  - new `presenterTouch.test.ts`: Previous and Next walk the storyboard in key order and stop at both ends.
- Build clean.
- Headless Chromium at 1280 × 720, 820 × 1180 and 390 × 844:
  - no link and no `agniware.tech` in the page;
  - Guided tour → Next → Next reaches step 3/9, and ✕ ends the tour;
  - after scrolling, the caption is at the top of the screen on tablet and phone;
  - the health rows are cards on the phone only;
  - no sideways scroll, 0 console errors, 0 requests to other hosts.
- Presenter at 1600 × 1000 and phone presenter still pass the S3 checks.

**Known limits:**
- On desktop the tour buttons take their own row under the caption, about 45 px, and only while a tour runs. The left
  column scrolls, so the map stays usable.
- Keys 1–9 remain the fast path for a live talk.

**Promoted:** not yet.
