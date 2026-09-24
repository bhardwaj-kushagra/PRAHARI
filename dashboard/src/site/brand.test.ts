import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { FIRENET_EXPANSION, FIRENET_WORDS, TEAM } from "./brand";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "..", "..", "index.html"), "utf8");

describe("public-site branding", () => {
  it("highlights letters that spell FIRENET, each at the start of its word", () => {
    expect(FIRENET_WORDS.map((w) => w.key).join("").toUpperCase()).toBe("FIRENET");
    for (const { word, key } of FIRENET_WORDS) expect(word.startsWith(key)).toBe(true);
    expect(FIRENET_EXPANSION).toBe("Fire Identification and Response Network for Early Tracking");
  });

  it("names the team without linking to or mentioning its website (left out for now, S4)", () => {
    expect(TEAM).toEqual({ name: "AgniWare" });
    for (const f of ["SiteBar.tsx", "brand.ts", "site.css"]) {
      expect(readFileSync(join(here, f), "utf8")).not.toMatch(/agniware\.tech|href=/i);
    }
    expect(html).not.toMatch(/agniware\.tech/i);
  });

  it("gives the page a title, a description and a link preview that say SIMULATION or simulation", () => {
    expect(html).toMatch(/<title>[^<]*FIRENET[^<]*SIMULATION[^<]*<\/title>/);
    expect(html).toMatch(/name="description" content="[^"]*simulation output/);
    expect(html).toMatch(/property="og:image" content="https:\/\/dashboard\.firenet\.live\/brand\/og-image\.png"/);
    expect(html).toContain(FIRENET_EXPANSION.replace("Early Tracking", ""));
  });
});
