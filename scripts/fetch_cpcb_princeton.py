#!/usr/bin/env python3
"""Fetch the Delhi-NCR PM2.5 station files of the Princeton CPCB archive (Sharma & Mauzerall 2021,
doi:10.34770/60j3-yp02; CC BY 4.0) for addendum C: every `pm25_ccr_copy/Delhi*` file plus the Haryana and Uttar
Pradesh files of the NCR districts around Delhi. The 25 km rule is applied later, on the coordinates in the files.

Raw files go to data/real/cpcb_princeton/raw/ (gitignored); data/real/cpcb_princeton/manifest.json records URL,
SHA-256, size and retrieval time. Re-running verifies the checksums.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from realdata_fetch_util import download, now_utc, sha256, update_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "data" / "real" / "cpcb_princeton"
CATALOG = "https://datacommons.princeton.edu/discovery/catalog/doi-10-34770-60j3-yp02.json"
NCR = re.compile(r"^(Haryana|UP)_(Gurugram|Gurgaon|Faridabad|Bahadurgarh|Ballabgarh|Sonipat|Noida|GreaterNoida|Ghaziabad)")


def select(files: list[dict]) -> list[dict]:
    """Addendum C — Delhi files and the NCR-district files of the PM2.5 folder."""
    out = []
    for f in files:
        p = f["full_path"]
        if not (p.startswith("pm25_ccr_copy/") and p.endswith(".csv")):
            continue
        base = p.split("/", 1)[1]
        if base.startswith("Delhi") or NCR.match(base):
            out.append(f)
    return out


def main() -> int:
    with urllib.request.urlopen(CATALOG, timeout=120) as r:
        cat = json.load(r)
    man = ROOT / "manifest.json"
    known = json.loads(man.read_text(encoding="utf-8"))["files"] if man.is_file() else {}
    entries = {}
    for f in select(cat["files"]):
        base = f["full_path"].split("/", 1)[1]
        dest = ROOT / "raw" / base
        if not dest.is_file():
            download(f["download_url"], dest)
        digest = sha256(dest)
        rel = f"raw/{base}"
        if rel in known and known[rel]["sha256"] != digest:
            print(f"CHECKSUM MISMATCH {rel}", file=sys.stderr)
            return 1
        entries[rel] = known.get(rel) or {"url": f["download_url"], "sha256": digest, "bytes": dest.stat().st_size,
                                          "retrieved_utc": now_utc()}
        print(rel, dest.stat().st_size)
    update_manifest(man, entries, {"source": "Sharma & Mauzerall (2021), Princeton University, doi:10.34770/60j3-yp02",
                                   "licence": "CC BY 4.0", "catalog": CATALOG})
    return 0


if __name__ == "__main__":
    sys.exit(main())
