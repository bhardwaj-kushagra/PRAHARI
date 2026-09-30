"""Sensor.Community Stuttgart network (docs/research/realdata-plan.md, addendum B; REAL, exploratory).

Builds the same `data` structure as the N5 loader from the archive files fetched by
`scripts/fetch_sensorcommunity_stuttgart.py`, applies the addendum's selection (outdoor SDS011, verified location within
2.0 km of the centre, readings on ≥ 90% of the 5-minute bins, the 30 nearest), then runs the N5 analysis unchanged.
"""
from __future__ import annotations

import csv
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from prahari.record.writer import write_text_atomic
from prahari.research.realdata import TICK_S, haversine_km

ROOT = Path("data/real/sensorcommunity_stuttgart")
CENTRE = (48.7758, 9.1829)
T0 = int(datetime(2024, 10, 1, tzinfo=timezone.utc).timestamp())
T_BINS = 31 * 86400 // TICK_S
TZ_HOURS = 2                                    # CEST (UTC+2) until 27 Oct; bins use +2 throughout (documented)


def _epoch(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "")).replace(tzinfo=timezone.utc).timestamp())


def read_sensor(files: list[Path]) -> tuple[list, list, list]:
    """(epochs, PM2.5 values, (lat, lon) rows) from one sensor's daily archive files (semicolon CSV)."""
    ep, val, ll = [], [], []
    for f in files:
        opener = gzip.open if f.suffix == ".gz" else open
        with opener(f, "rt", encoding="utf-8", errors="replace") as h:
            for r in csv.DictReader(h, delimiter=";"):
                try:
                    ep.append(_epoch(r["timestamp"]))
                    val.append(float(r["P2"]) if r.get("P2") not in (None, "") else np.nan)
                    ll.append((float(r["lat"]), float(r["lon"])))
                except (ValueError, KeyError):
                    continue
    return ep, val, ll


def select(root: Path = ROOT, radius_km: float = 2.0, min_cov: float = 0.9, max_n: int = 30) -> dict:
    """Addendum B selection. Returns the N5-style data dict plus the selection table."""
    shortlist = json.loads((root / "shortlist.json").read_text())["sensors"]
    table, rows, stations = [], [], {}
    for sid in shortlist:
        files = sorted((root / "raw").glob(f"*_sds011_sensor_{sid}.csv*"))
        if not files:
            continue
        ep, val, ll = read_sensor(files)
        if not ep:
            continue
        lat, lon = np.median(np.array(ll), axis=0)
        km = float(haversine_km(np.array([CENTRE, [lat, lon]]))[0, 1])
        idx = (np.asarray(ep) - T0) // TICK_S
        ok = (idx >= 0) & (idx < T_BINS) & np.isfinite(val)
        cov = float(np.unique(idx[ok]).size) / T_BINS
        table.append({"sensor": sid, "lat": round(float(lat), 5), "lon": round(float(lon), 5), "km": round(km, 3),
                      "coverage": round(cov, 3)})
        if km <= radius_km and cov >= min_cov:
            stations[sid] = {"name": "ST_" + sid, "lat": float(lat), "lon": float(lon), "km": km}
            rows += [{"UnixTime": str(e), "stationID": sid, "PM2P5": str(v)} for e, v in zip(ep, val)]
    keep = sorted(stations, key=lambda s: stations[s]["km"])[:max_n]
    stations = {s: stations[s] for s in keep}
    rows = [r for r in rows if r["stationID"] in stations]
    return {"rows": rows, "stations": stations, "fires": [], "selection_table": table, "selected": keep}


def write_realdata_sc(out: Path) -> list[str]:
    """Run the N5 analysis on the selected Stuttgart network; write results/research/real_sensorcommunity_stuttgart.json."""
    from prahari.research import realdata_report as rr
    from prahari.research.realdata import CLUSTERS
    data = select()
    CLUSTERS["ST"] = TZ_HOURS                   # local-time bins only; no fire records
    try:
        res = rr.analyse_cluster(data, "ST")
    finally:
        CLUSTERS.pop("ST", None)
    doc = {"label": "REAL (exploratory)", "source": "Sensor.Community archive (ODbL 1.0), October 2024",
           "plan": "docs/research/realdata-plan.md, addendum B", "centre": CENTRE,
           "selected": data["selected"], "selection_table": data["selection_table"], "cluster": res}
    p = Path(out) / "real_sensorcommunity_stuttgart.json"
    write_text_atomic(p, json.dumps(doc, indent=1))
    return [str(p)]
