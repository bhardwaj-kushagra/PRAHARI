// Public-site build switches. This folder exists only on the site branches (site-dev, site-live), never on main;
// see docs/site/README.md. Site-only behaviour lives here so that merging main into site-dev stays conflict-free.

/** The optional live engine (SPEC §6.1, Phase 6) needs a FastAPI server on the viewer's own machine, which a visitor
 *  to the public site does not have, so its panel is hidden by default. Set VITE_LIVE_ENGINE=1 when building or running
 *  `npm run dev` to show it again, for example against a local `uvicorn server.app:app`. */
export function liveEngineEnabled(env: Record<string, unknown>): boolean {
  return env.VITE_LIVE_ENGINE === "1";
}

export const LIVE_ENGINE = liveEngineEnabled(import.meta.env);
