#!/usr/bin/env python3
"""Fetch Delhi CPCB PM2.5 data through the OpenAQ v3 API for addendum C (cluster DL15 and the 2019 provenance check).

OpenAQ lists NO licence for CPCB locations (checked 1 Oct 2026). The developer decided on 1 Oct 2026 to use them as
public Government of India monitoring data (DECISIONS P-9). Raw responses are never redistributed: they go to
data/real/openaq_cpcb_delhi/raw/ (gitignored). Credit: CPCB (source) and OpenAQ (platform), as OpenAQ's terms
require.

  shortlist                  CPCB PM2.5 locations within 25 km of 28.6129 N, 77.2295 E, with every PM2.5 sensor's own
                             date range → shortlist.json (metadata only)
  fetch                      /v3/sensors/{id}/measurements for the 17 Sep–30 Nov (IST) windows: per location and
                             season, the PM2.5 sensor whose own date range spans the window (several: the lowest id;
                             none: the location is skipped) → raw/<season>/sensor<id>_p<n>.json.gz
  provenance --sensors a,b   1 Oct–30 Nov 2017 (IST) for the listed sensors → raw/2017/ (Princeton comparison)

The API key is read from OPENAQ_API_KEY and never written or printed. Requests stay under 55 per minute.
"""
import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from realdata_fetch_util import now_utc, sha256, update_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "data" / "real" / "openaq_cpcb_delhi"
API = "https://api.openaq.org/v3"
CENTRE, RADIUS_M, CPCB, PM25 = (28.6129, 77.2295), 25000, 168, 2
# IST midnight boundaries in UTC: 17 Sep 00:00 IST = 16 Sep 18:30 UTC; 1 Dec 00:00 IST = 30 Nov 18:30 UTC
SEASONS = (2023, 2024, 2025)
WINDOWS = {y: (f"{y}-09-16T18:30:00Z", f"{y}-11-30T18:30:00Z") for y in SEASONS}
PROVENANCE = 2017                                   # OpenAQ's older CPCB sensor ids end in Feb 2018
WINDOWS[PROVENANCE] = ("2017-09-30T18:30:00Z", "2017-11-30T18:30:00Z")
_last = [0.0]


def get(path: str, params: dict) -> dict:
    """GET with the key from the environment, ≤ 55 requests a minute, retrying 429/5xx with backoff."""
    key = os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise SystemExit("OPENAQ_API_KEY is not set")
    q = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{API}{path}?{q}"
    for k in range(6):
        wait = 60.0 / 55 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"X-API-Key": key, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and k < 5:
                time.sleep(float(e.headers.get("Retry-After") or 2 ** (k + 2)))
                continue
            raise
        except urllib.error.URLError:
            if k < 5:
                time.sleep(2 ** (k + 2))
                continue
            raise
    raise RuntimeError("unreachable")


def spans(obj: dict, start: str, end: str) -> bool:
    f, t = (obj.get("datetimeFirst") or {}).get("utc"), (obj.get("datetimeLast") or {}).get("utc")
    return bool(f and t and f <= start and t >= end)


def chosen(row: dict, season: int):
    """Addendum C — the location's PM2.5 sensor for a season: own date range spans the window; lowest id; or None."""
    ok = sorted(s["id"] for s in row["pm25_sensors"] if s["spans"][str(season)])
    return ok[0] if ok else None


def shortlist() -> int:
    d = get("/locations", {"providers_id": CPCB, "parameters_id": PM25, "coordinates": f"{CENTRE[0]},{CENTRE[1]}",
                           "radius": RADIUS_M, "limit": 1000})
    rows = []
    for loc in sorted(d["results"], key=lambda x: x["id"]):
        sens = get(f"/locations/{loc['id']}/sensors", {"limit": 100})["results"]
        pm = [{"id": x["id"], "datetime_first": (x.get("datetimeFirst") or {}).get("utc"),
               "datetime_last": (x.get("datetimeLast") or {}).get("utc"),
               "spans": {str(y): spans(x, *w) for y, w in sorted(WINDOWS.items())}}
              for x in sorted(sens, key=lambda x: x["id"]) if x["parameter"]["name"] == "pm25"]
        row = {"location_id": loc["id"], "name": loc["name"], "lat": loc["coordinates"]["latitude"],
               "lon": loc["coordinates"]["longitude"], "pm25_sensors": pm,
               "provider": loc["provider"]["name"], "licenses": loc.get("licenses") or [],
               "datetime_first": (loc.get("datetimeFirst") or {}).get("utc"),
               "datetime_last": (loc.get("datetimeLast") or {}).get("utc")}
        row["chosen_sensor"] = {str(y): chosen(row, y) for y in sorted(WINDOWS)}
        rows.append(row)
    out = {"retrieved_utc": now_utc(), "query": {"providers_id": CPCB, "parameters_id": PM25, "centre": CENTRE,
                                                 "radius_m": RADIUS_M},
           "licence_listed": sorted({lic["name"] for r in rows for lic in r["licenses"]}), "locations": rows}
    (ROOT / "shortlist.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for y in sorted(WINDOWS):
        print(y, sum(r["chosen_sensor"][str(y)] is not None for r in rows), "of", len(rows),
              "locations have a PM2.5 sensor spanning the window")
    return 0


def fetch_sensor(season: int, sid: int) -> dict:
    """Every page of one sensor's measurements in the season window; returns manifest entries."""
    start, end = WINDOWS[season]
    out, page = {}, 1
    done = ROOT / "raw" / str(season) / f"sensor{sid}.done"
    if done.is_file():
        return {}
    while True:
        dest = ROOT / "raw" / str(season) / f"sensor{sid}_p{page}.json.gz"
        if dest.is_file():
            body = json.loads(gzip.decompress(dest.read_bytes()))
        else:
            body = get(f"/sensors/{sid}/measurements", {"datetime_from": start, "datetime_to": end, "limit": 1000,
                                                         "page": page})
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(gzip.compress(json.dumps(body, separators=(",", ":")).encode("utf-8"), mtime=0))
            tmp.replace(dest)
        out[f"raw/{season}/{dest.name}"] = {"sensor": sid, "season": season, "page": page, "sha256": sha256(dest),
                                            "bytes": dest.stat().st_size, "n": len(body.get("results", [])),
                                            "retrieved_utc": now_utc()}
        if len(body.get("results", [])) < 1000:
            break
        page += 1
    done.write_text("ok\n")
    return out


def fetch(seasons, sensors=None) -> int:
    sl = json.loads((ROOT / "shortlist.json").read_text(encoding="utf-8"))
    man = ROOT / "manifest.json"
    for y in seasons:
        sids = sensors or [r["chosen_sensor"][str(y)] for r in sl["locations"] if r["chosen_sensor"][str(y)]]
        for sid in sids:
            entries = fetch_sensor(y, int(sid))
            if entries:
                update_manifest(man, entries, {"source": "OpenAQ v3 API (CPCB provider)",
                                               "licence": "none listed by OpenAQ (checked 1 Oct 2026); used at the "
                                                          "developer's decision, DECISIONS P-9"})
            print(y, sid, "pages", len(entries))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["shortlist", "fetch", "provenance"])
    ap.add_argument("--sensors", default=None, help="comma list of sensor ids (provenance)")
    a = ap.parse_args(argv)
    ROOT.mkdir(parents=True, exist_ok=True)
    if a.command == "shortlist":
        return shortlist()
    if a.command == "fetch":
        return fetch(SEASONS)
    if not a.sensors:
        ap.error("provenance needs --sensors")
    return fetch((PROVENANCE,), [int(s) for s in a.sensors.split(",")])


if __name__ == "__main__":
    sys.exit(main())
