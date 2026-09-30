"""Fetch the Sensor.Community archive (ODbL 1.0) for outdoor SDS011 sensors near Stuttgart, 1–31 October 2024
(docs/research/realdata-plan.md, addendum B).

1. Shortlist: outdoor SDS011 sensors within 3.0 km of the centre on today's map
   (`data.sensor.community/static/v2/data.24h.json`), saved to `shortlist.json` (committed). This is a shortlist only;
   the October 2024 locations are verified from the archive files by the analysis.
2. Archive files `archive.sensor.community/2024/<day>/<day>_sds011_sensor_<id>.csv.gz` (past years sit in year folders)
   for each shortlisted sensor and day go to `raw/` unmodified (not committed). A SHA-256 manifest (`manifest.json`, committed) records exactly what was used.

Run: python scripts/fetch_sensorcommunity_stuttgart.py
"""
import hashlib
import json
import math
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "real" / "sensorcommunity_stuttgart"
RAW = ROOT / "raw"
CENTRE = (48.7758, 9.1829)
UA = {"User-Agent": "Mozilla/5.0 (PRAHARI research; open-data use under ODbL)"}


def get(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def shortlist() -> dict:
    path = ROOT / "shortlist.json"
    if path.exists():
        return json.loads(path.read_text())["sensors"]
    snap = json.loads(get("https://data.sensor.community/static/v2/data.24h.json"))
    out = {}
    for x in snap:
        if x["sensor"]["sensor_type"]["name"] != "SDS011" or str(x["location"].get("indoor", 0)) not in ("0", "False"):
            continue
        la, lo = float(x["location"]["latitude"] or 0), float(x["location"]["longitude"] or 0)
        km = math.hypot((la - CENTRE[0]) * 111.2, (lo - CENTRE[1]) * 111.2 * math.cos(math.radians(CENTRE[0])))
        if km <= 3.0:
            out[str(x["sensor"]["id"])] = {"lat": la, "lon": lo, "km_from_centre": round(km, 3)}
    out = dict(sorted(out.items(), key=lambda kv: kv[1]["km_from_centre"]))
    path.write_text(json.dumps({"source": "https://data.sensor.community/static/v2/data.24h.json",
                                "retrieved": date.today().isoformat(), "centre": CENTRE,
                                "rule": "outdoor SDS011 within 3.0 km of the centre on the retrieval date "
                                        "(shortlist only; October 2024 locations are verified from the archive files)",
                                "sensors": out}, indent=1))
    return out


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    ids = shortlist()
    manifest = {}
    for i in range(31):
        day = (date(2024, 10, 1) + timedelta(days=i)).isoformat()
        for sid in ids:
            name = f"{day}_sds011_sensor_{sid}.csv.gz"
            path = RAW / name
            if not path.exists():
                try:
                    path.write_bytes(get(f"https://archive.sensor.community/{day[:4]}/{day}/{name}", timeout=60))
                    time.sleep(0.05)
                except Exception:                     # no file for that sensor and day (404) or a transient error
                    manifest[name] = None
                    continue
            manifest[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT / "manifest.json").write_text(json.dumps(dict(sorted(manifest.items())), indent=0))
    print(len(ids), "sensors shortlisted;", sum(v is not None for v in manifest.values()), "files;",
          sum(v is None for v in manifest.values()), "absent")


if __name__ == "__main__":
    main()
