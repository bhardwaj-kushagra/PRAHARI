import { describe, expect, it } from "vitest";
import { daysLabel, sci, simClock } from "./format";

describe("format", () => {
  it("formats the simulated clock", () => {
    const h = { start: "2026-04-15T00:00" } as Parameters<typeof simClock>[0];
    expect(simClock(h, 0)).toBe("Day 1 · 00:00");
    expect(simClock(h, 847)).toBe("Day 1 · 14:07");
    expect(simClock(h, 1440 + 61)).toBe("Day 2 · 01:01");
  });
  it("formats numbers compactly without dropping integer zeros", () => {
    expect(sci(100)).toBe("100");
    expect(sci(30)).toBe("30");
    expect(sci(0.5)).toBe("0.5");
    expect(sci(1e-4)).toBe("1e-4");
    expect(sci(0)).toBe("0");
  });
  it("labels warm-start recordings with the first recorded day", () => {
    expect(daysLabel(1)).toBe("1 simulated day");
    expect(daysLabel(31, 28 * 1440)).toBe("31 simulated days, recorded from day 29");
  });
});
