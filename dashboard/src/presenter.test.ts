import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { keyAction, rehearsalSeconds, type Storyboard, stepMinute, storyboardProblems } from "./presenter";

const here = dirname(fileURLToPath(import.meta.url));
const board = JSON.parse(readFileSync(join(here, "..", "public", "storyboard.json"), "utf8")) as Storyboard;

describe("presenter mode (SPEC §6.4)", () => {
  it("maps keys 1–9, F, S, R and Escape, and leaves modified keys to the browser", () => {
    expect(keyAction({ key: "3" })).toEqual({ kind: "step", key: 3 });
    expect(keyAction({ key: "F" })).toEqual({ kind: "fullscreen" });
    expect(keyAction({ key: "s" })).toEqual({ kind: "switch", module: "scmr" });
    expect(keyAction({ key: "r" })).toEqual({ kind: "switch", module: "raq" });
    expect(keyAction({ key: "Escape" })).toEqual({ kind: "clear" });
    expect(keyAction({ key: "0" })).toBeNull();
    expect(keyAction({ key: "r", ctrlKey: true })).toBeNull();          // Ctrl-R still reloads
  });
  it("turns a day and a time into minutes since the start of the run", () => {
    expect(stepMinute({ key: 1, title: "", day: 31, time: "14:00", seconds: 1, caption: "" })).toBe(30 * 1440 + 840);
    expect(stepMinute({ key: 1, title: "", t: 42, seconds: 1, caption: "" })).toBe(42);
    expect(stepMinute({ key: 1, title: "", seconds: 1, caption: "" })).toBeNull();
  });
  it("reports storyboard problems", () => {
    const bad: Storyboard = { title: "", steps: [
      { key: 1, title: "a", seconds: 0, caption: "", time: "9h" },
      { key: 1, title: "b", seconds: 5, caption: "", panel: "maps" as never },
    ] };
    expect(storyboardProblems(bad)).toEqual([
      "step 1: time must be HH:MM", "step 1: seconds must be positive", "key 1 used twice",
      'step 1: unknown panel "maps"', "no step names a recording"]);
  });
});

describe("the bundled storyboard (Phase 10 acceptance 2)", () => {
  it("is valid, uses keys 1–9 once each and fits in three minutes", () => {
    expect(storyboardProblems(board)).toEqual([]);
    expect(board.steps.map((s) => s.key)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
    expect(rehearsalSeconds(board)).toBeLessThanOrEqual(180);
  });
  it("names only recordings that exist in recordings/", () => {
    for (const s of board.steps) if (s.recording) expect(existsSync(join(here, "..", "..", "recordings", s.recording)), s.recording).toBe(true);
  });
});
