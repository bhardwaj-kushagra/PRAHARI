import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import type { Storyboard } from "../presenter";
import { neighbourStep, orderedSteps } from "./PresenterTouch";

const here = dirname(fileURLToPath(import.meta.url));
const board = JSON.parse(readFileSync(join(here, "..", "..", "public", "storyboard.json"), "utf8")) as Storyboard;

describe("guided-tour buttons (public site)", () => {
  it("walks the storyboard in key order, stopping at both ends", () => {
    const steps = orderedSteps(board);
    expect(steps.map((s) => s.key)).toEqual([...steps.map((s) => s.key)].sort((a, b) => a - b));
    expect(neighbourStep(board, steps[0], -1)).toBeNull();
    expect(neighbourStep(board, steps[steps.length - 1], 1)).toBeNull();
    for (let i = 0; i + 1 < steps.length; i++) {
      expect(neighbourStep(board, steps[i], 1)?.key).toBe(steps[i + 1].key);
      expect(neighbourStep(board, steps[i + 1], -1)?.key).toBe(steps[i].key);
    }
  });
});
