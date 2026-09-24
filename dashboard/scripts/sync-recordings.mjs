// Copy committed recordings from ../recordings into public/recordings and write an index,
// so both `npm run dev` and the static build can list and open them without any server.
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "..", "recordings");
const dst = join(here, "..", "public", "recordings");
rmSync(dst, { recursive: true, force: true });
mkdirSync(dst, { recursive: true });
const files = existsSync(src)
  ? readdirSync(src).filter((f) => /\.prs\.jsonl(\.gz)?$/.test(f)).sort()
  : [];
for (const f of files) copyFileSync(join(src, f), join(dst, f));
// Phase 9: each recording's scenario, description and Regime Card, read from its header (the regime selector, View 8).
const meta = {};
for (const f of files) {
  try {
    const raw = readFileSync(join(src, f));
    const text = f.endsWith(".gz") ? gunzipSync(raw).toString("utf8") : raw.toString("utf8");
    const h = JSON.parse(text.slice(0, text.indexOf("\n"))).header ?? {};
    meta[f] = { scenario: h.scenario, description: h.description, seed: h.seed, days: h.days, regime: h.regime ?? null };
  } catch {
    meta[f] = {};
  }
}
writeFileSync(join(dst, "index.json"), JSON.stringify({ recordings: files, meta }, null, 2));
console.log(`synced ${files.length} recording(s) to public/recordings`);

// Experiment summary for the Results tab (Phase 4), if one has been produced by `prahari experiment`.
const resSrc = join(here, "..", "..", "results", "summary.json");
const resDst = join(here, "..", "public", "results");
rmSync(resDst, { recursive: true, force: true });
if (existsSync(resSrc)) {
  mkdirSync(resDst, { recursive: true });
  copyFileSync(resSrc, join(resDst, "summary.json"));
  console.log("synced results/summary.json");
}
