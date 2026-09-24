# The public site

The PRAHARI-SIM dashboard is published as a view-only website at **`https://dashboard.firenet.live`**, so people can
explore the recorded scenarios in a browser without installing anything. It is the same replay dashboard as the
laptop demo: static files and the committed recordings, no engine and no server. Every value on it is simulation
output (SIM).

This page covers the branch model, what the site changes compared with `main`, the hosting settings, and how a change
reaches the public address. The dated record of site work is [LOG.md](LOG.md); the rules for working on these
branches are in the site branches' [CLAUDE.md](../../CLAUDE.md).

## Branch model

```text
main ──●── 318fe4d ──●── v1.0.0 ──●──●──►   simulator: engine, science, experiments, results (main's own CLAUDE.md)
              │               │
              │               │ merge main or a tag (science updates, one way only)
              ▼               ▼
site-dev ─────●───────●───────●──●──●──►   draft of the website; all site work lands here
                      │             │      (Cloudflare builds a preview of every push)
                      │ promote     │ promote (pull request)
                      ▼             ▼
site-live ────────────●─────────────●──►   production: Cloudflare publishes it at dashboard.firenet.live
```

- **`main`** is the simulator. Science work continues there under the original rules. It never receives site changes.
- **`site-dev`** started from `318fe4d` (release 1.0 before the second audit) and has since merged the tag `v1.0.0`
  (`578f1c8`, release 1.0 with the second audit). All site work happens here, either
  directly or on a feature branch merged into it. Each push gets a Cloudflare preview address, so a change can be
  checked on real hosting (and on a phone) before anyone else sees it.
- **`site-live`** is what the public sees. It changes only through a promotion pull request `site-dev → site-live`,
  so it is always a copy of a `site-dev` commit that was already checked. Cloudflare rebuilds the public site on each
  promotion, not on each draft push.

Science updates flow one way: merge `main` (or a release tag) into `site-dev`, check, promote. Site branches are never
merged into `main`.

## What the site changes compared with `main`

| Change | Where | Why |
| --- | --- | --- |
| Live-engine panel hidden | `dashboard/src/site/siteConfig.ts`; one guard in `App.tsx`, one tooltip in `MechanismSwitches.tsx` | It needs a FastAPI server on the viewer's own machine, so on the web it could only say "not connected". `VITE_LIVE_ENGINE=1` brings it back for local work. |
| Unlisted, caching | `dashboard/public/_headers` | Asks search engines not to index the site; long caching for hashed assets, one hour for recordings. Only Cloudflare reads this file. |
| Node version | `.node-version` | Makes Cloudflare's build use Node 22, the version the dashboard is tested with. |
| Working rules | `CLAUDE.md` | Site rules instead of the simulator rules; see the file. |
| Documentation | `docs/site/` | This page and the log. |

Everything else (engine, configurations, recordings, results, the rest of the dashboard) is identical to the tag
`v1.0.0`.

## Hosting settings (Cloudflare Pages)

| Setting | Value |
| --- | --- |
| Git repository | `bhardwaj-kushagra/PRAHARI` |
| Production branch | `site-live` |
| Preview branches | custom: `site-dev` only (no previews for `main` or other branches) |
| Framework preset | None |
| Build command | `cd dashboard && npm ci && npm run build` |
| Build output directory | `dashboard/dist` |
| Root directory | (empty: the repository root, because the build copies `recordings/` and `results/` in) |
| Environment variable | `NODE_VERSION` = `22` (the same as `.node-version`; either is enough) |
| Custom domain | `dashboard.firenet.live` |

The build copies the committed recordings into the site (about 51 MB in total at `v1.0.0`; the largest single file is
about 5.7 MB). Cloudflare Pages allows up to 20 000 files of at most 25 MiB each, so there is plenty of room.

## DNS (name.com)

`firenet.live` itself stays where it is (the existing Blogger page). Only one record is added at name.com:

| Type | Host | Answer | TTL |
| --- | --- | --- | --- |
| CNAME | `dashboard` | `<project>.pages.dev` (the address Cloudflare gives the project) | 300 |

Add the custom domain in the Cloudflare project **first**, then the CNAME. Cloudflare checks the record and issues the
HTTPS certificate itself, usually within minutes. If the domain has a CAA record, it must allow `letsencrypt.org` and
`pki.goog`, or the certificate cannot be issued.

## Releasing a change

1. Work on `site-dev`. Run the checks: in `dashboard/`, `npx tsc --noEmit`, `npx vitest run`, `npm run build`.
2. Push. Open the `site-dev` preview address from the Cloudflare project and check it on a desktop browser and a phone.
3. Open a pull request with base `site-live` and compare `site-dev`. Merge it with "Create a merge commit".
4. Cloudflare builds `site-live` (about two minutes) and the public address updates.

**Rolling back:** in the Cloudflare project, open Deployments, pick the previous production deployment and choose
"Rollback to this deployment". It takes effect at once; then fix the problem on `site-dev` and promote again.

## Bringing in science updates from `main`

On `site-dev`: `git merge main` (or a tag). If `main` changed its `CLAUDE.md`, that file conflicts; keep the site
version with `git checkout --ours CLAUDE.md`. The site's edits to shared dashboard files are listed in
[LOG.md](LOG.md), so any other conflict can be resolved by taking `main`'s file and re-applying the small switch. Check
that no new recording exceeds 25 MiB, run the checks, then release as above.
