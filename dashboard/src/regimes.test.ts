import { describe, expect, it } from "vitest";
import { cardLine, filterByRegime, regimeOptions, type RecordingMeta } from "./regimes";

const card = (name: string, lightning = false) =>
  ({ name, label: `${name} card`, radio_plan: "US915", alert_format: "x", lightning });
const meta: Record<string, RecordingMeta> = {
  "a.gz": { regime: card("usa") },
  "b.gz": { regime: card("canada", true) },
  "c.gz": { regime: card("canada", true) },
  "d.gz": { regime: null },
  "e.gz": {},
};
const files = Object.keys(meta);

describe("regime selector (View 8)", () => {
  it("lists the regimes present, cards first and recordings without a card last", () => {
    expect(regimeOptions(files, meta).map((o) => [o.name, o.n])).toEqual([["canada", 2], ["usa", 1], ["none", 2]]);
  });
  it("filters recordings by regime; an empty choice keeps them all", () => {
    expect(filterByRegime(files, meta, "canada")).toEqual(["b.gz", "c.gz"]);
    expect(filterByRegime(files, meta, "none")).toEqual(["d.gz", "e.gz"]);
    expect(filterByRegime(files, meta, "")).toEqual(files);
  });
  it("summarises a card in one line", () => {
    expect(cardLine(card("canada", true))).toBe("US915 · alerts: x · lightning on");
  });
});
