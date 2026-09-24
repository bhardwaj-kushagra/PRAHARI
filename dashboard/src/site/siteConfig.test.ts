import { describe, expect, it } from "vitest";
import { LIVE_ENGINE, liveEngineEnabled } from "./siteConfig";

describe("public-site switches", () => {
  it("hides the live engine unless VITE_LIVE_ENGINE is exactly 1", () => {
    expect(liveEngineEnabled({})).toBe(false);
    expect(liveEngineEnabled({ VITE_LIVE_ENGINE: "0" })).toBe(false);
    expect(liveEngineEnabled({ VITE_LIVE_ENGINE: "true" })).toBe(false);
    expect(liveEngineEnabled({ VITE_LIVE_ENGINE: "1" })).toBe(true);
  });

  it("builds with the live engine hidden by default (the test run does not set VITE_LIVE_ENGINE)", () => {
    expect(LIVE_ENGINE).toBe(false);
  });
});
