#!/usr/bin/env python3
"""Fetch the Aakash project (RIHN) hourly CUPI-G PM2.5/CO archives, Sep–Nov 2022–2024 (addendum C).

Licence: CC BY-NC-ND 4.0 (https://aakash-rihn.org/en/data-set/). Non-commercial research use with attribution; the
data and any modified version are NOT redistributed, so raw files stay under data/real/aakash/raw/ (gitignored).
Writes data/real/aakash/manifest.json (URL, SHA-256, size, retrieval time). Re-running verifies the checksums.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from realdata_fetch_util import download, now_utc, sha256, update_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "data" / "real" / "aakash"
BASE = "https://aakash-rihn.org/en/wp-content/uploads/2025/01/"
FILES = [f"1H_{y}0901_{y}1130.zip" for y in (2022, 2023, 2024)]


def main() -> int:
    man = ROOT / "manifest.json"
    known = {}
    if man.is_file():
        import json
        known = json.loads(man.read_text(encoding="utf-8"))["files"]
    entries = {}
    for name in FILES:
        dest = ROOT / "raw" / name
        if not dest.is_file():
            download(BASE + name, dest)
        digest = sha256(dest)
        rel = f"raw/{name}"
        if rel in known and known[rel]["sha256"] != digest:
            print(f"CHECKSUM MISMATCH {rel}", file=sys.stderr)
            return 1
        entries[rel] = known.get(rel) or {"url": BASE + name, "sha256": digest, "bytes": dest.stat().st_size,
                                          "retrieved_utc": now_utc()}
        print(rel, digest)
    update_manifest(man, entries, {"source": "Aakash project, RIHN (https://aakash-rihn.org/en/data-set/)",
                                   "licence": "CC BY-NC-ND 4.0"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
