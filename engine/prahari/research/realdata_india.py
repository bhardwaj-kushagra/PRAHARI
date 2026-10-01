"""North-west India, crop-residue season (docs/research/realdata-plan.md addendum C; REAL, exploratory).

Three networks: AK (Aakash/RIHN low-cost CUPI-G, hourly PM2.5 and CO, 2022–2024), DL (CPCB Delhi, Princeton archive,
hourly, 2017–2019) and DL15 (CPCB Delhi through OpenAQ, 15 min, 2025). Per cluster-year: the plan's common-mode event
catalogue (definitions kept in minutes), a front fit, and the held-out comparison with the registered M20b haze model
through an observation operator (the unchanged class `prahari.sensors.haze.M20b` on the network's own coordinates).
DL15 also gets the node-layer replay. Nothing here changes protocol R2. Raw data are read from data/real/*/raw/ and
never written back; the output holds no per-station series (licence terms).
"""
from __future__ import annotations

import copy
import csv
import gzip
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from prahari.core.rng import make_rngs
from prahari.research.realdata import (event_stats, find_events, haversine_km, local_excursions, node_layer, replay,
                                       rolling_baseline, share, to_grid)

IST_S = 19800                                    # UTC+5:30
CENTRE, RADIUS_KM = (28.6129, 77.2295), 25.0     # DL and DL15 selection
MIN_COVERAGE, MIN_STATIONS = 0.75, 5
STUCK_S = 6 * 3600                               # identical consecutive values lasting ≥ 6 h → missing
CARRY_S = 15 * 60                                # gaps ≤ 15 min carried forward
NIGHT = (20, 8)                                  # 20:00–08:00 IST
OPERATOR_SEED, OPERATOR_N = 20261003, 10000
ROOT = Path("data/real")
# Singh et al. (2023), Sci Rep 13:13201, Supplementary Table S1 (CC BY 4.0): the 29 CUPI-G sites of the 2022 campaign
# (latitude, longitude to 0.1°). No mapping to the Aakash file IDs is published (DECISIONS P-10), so this layout feeds
# only the observation operator.
AK_LAYOUT = [(31.7, 74.7), (31.8, 74.9), (31.6, 75.3), (30.9, 75.2), (31.3, 75.5), (30.9, 75.8), (31.0, 76.2),
             (30.5, 75.5), (30.5, 76.0), (30.0, 75.8), (30.3, 76.1), (30.4, 76.3), (30.7, 76.8), (30.6, 76.5),
             (30.4, 77.0), (29.7, 76.7), (29.8, 76.9), (29.2, 76.4), (29.2, 76.8), (29.6, 77.0), (28.7, 76.6),
             (28.9, 77.1), (29.3, 77.6), (28.5, 77.0), (28.5, 77.2), (29.0, 77.7), (28.3, 77.1), (28.4, 77.3),
             (28.5, 77.9)]


def _ist(y: int, m: int, d: int) -> int:
    """Epoch of 00:00 IST on the date."""
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp()) - IST_S


# Cluster-years: (data start, window start, window end), epochs. Baselines start at the data start (addendum C).
SEASONS = {("AK", y): (_ist(y, 9, 1), _ist(y, 10, 1), _ist(y, 12, 1)) for y in (2022, 2023, 2024)}
SEASONS.update({("DL", y): (_ist(y, 9, 1), _ist(y, 10, 1), _ist(y, 12, 1)) for y in (2017, 2018, 2019)})
SEASONS[("DL15", 2025)] = (_ist(2025, 9, 17), _ist(2025, 10, 1), _ist(2025, 12, 1))
PRESEASON = {y: (_ist(y, 9, 1), _ist(y, 10, 1)) for y in (2022, 2023, 2024)}       # AK, descriptive only


# -- preprocessing ------------------------------------------------------------------------------------------------
def stuck_to_nan(g, tick_s: int, stuck_s: int = STUCK_S):
    """Addendum C QC — runs of identical consecutive finite values lasting ≥ `stuck_s` become missing."""
    g = np.array(g, dtype=float)
    n = max(1, stuck_s // tick_s)
    t, T = 0, g.size
    while t < T:
        if not np.isfinite(g[t]):
            t += 1
            continue
        e = t + 1
        while e < T and g[e] == g[t]:
            e += 1
        if e - t >= n:
            g[t:e] = np.nan
        t = e
    return g


def carry_forward(g, bins: int):
    """Gaps of ≤ `bins` bins carried forward (the plan's rule); longer gaps stay missing."""
    g = np.array(g, dtype=float)
    last, run = np.nan, 0
    for t in range(g.size):
        if np.isfinite(g[t]):
            last, run = g[t], 0
        elif np.isfinite(last) and run < bins:
            g[t] = last
            run += 1
    return g


def series(epochs, values, t_start: int, T: int, tick_s: int):
    """Addendum C preprocessing of one station: grid mean per bin, negatives → 0, stuck runs → missing, carry ≤ 15 min."""
    g = to_grid(np.asarray(epochs, dtype=np.int64), np.asarray(values, dtype=float), t_start, T, carry=0, tick_s=tick_s)
    g = np.where(g < 0, 0.0, g)
    g = stuck_to_nan(g, tick_s)
    return carry_forward(g, CARRY_S // tick_s)


# -- loaders --------------------------------------------------------------------------------------------------------
def _num(v: str) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return np.nan
    return np.nan if x <= -9999 else x


def load_ak(year: int, root: Path = ROOT / "aakash" / "raw") -> dict:
    """Aakash hourly zip: per station (file CUPIG_<id>.csv), epochs from `dateUTC`, PM2.5 and CO means."""
    z = zipfile.ZipFile(root / f"1H_{year}0901_{year}1130.zip")
    out = {}
    for name in sorted(n for n in z.namelist() if n.endswith(".csv") and not n.startswith("__MACOSX")):
        sid = Path(name).stem.replace("CUPIG_", "")
        rows = list(csv.reader(io.StringIO(z.read(name).decode("utf-8-sig", errors="replace"))))
        head = rows[0]
        i_t, i_pm, i_co = head.index("dateUTC"), head.index("pm2.5"), head.index("CO")
        ep, pm, co = [], [], []
        for r in rows[2:]:
            if len(r) <= i_co or not r[i_t]:
                continue
            ep.append(int(datetime.strptime(r[i_t], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()))
            pm.append(_num(r[i_pm]))
            co.append(_num(r[i_co]))
        out[sid] = {"epochs": ep, "pm": pm, "co": co}
    return out


def _princeton_epoch(s: str):
    s = s.strip()
    for fmt in ("%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%d/%m/%y %H:%M"):
        try:
            return int(datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp()) - IST_S
        except ValueError:
            continue
    return None


def parse_princeton(path: Path) -> dict:
    """One Princeton station file: columns by header name, day-first dates (IST), hourly-step check (DECISIONS P-10)."""
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    head = rows[0]
    info = {"file": path.name}
    if head.count("PM2.5") != 1:
        return {**info, "excluded": "PM2.5 column ambiguous or missing"}
    i_pm, i_st, i_la, i_lo = head.index("PM2.5"), head.index("Station"), head.index("lat"), head.index("lon")
    ep, pm, names, ll = [], [], set(), set()
    for r in rows[1:]:
        if len(r) < len(head) or not r[0].strip() or not r[i_st].strip():
            continue                                            # blank trailing rows (no date or no station)
        e = _princeton_epoch(r[0])
        if e is None:
            continue
        ep.append(e)
        pm.append(_num(r[i_pm]) if r[i_pm] not in ("None", "") else np.nan)
        names.add(r[i_st])
        ll.add((r[i_la], r[i_lo]))
    steps = np.diff(np.asarray(ep))
    hourly = float((steps == 3600).mean()) if steps.size else 0.0
    if hourly < 0.99:
        return {**info, "excluded": f"only {hourly:.3f} of steps are 1 h"}
    if len(names) != 1 or len(ll) != 1:
        return {**info, "excluded": f"{len(names)} station names, {len(ll)} coordinate pairs"}
    (la, lo), = ll
    return {**info, "station": names.pop(), "lat": float(la), "lon": float(lo), "epochs": ep, "pm": pm,
            "hourly_steps": round(hourly, 4)}


def load_dl(root: Path = ROOT / "cpcb_princeton" / "raw") -> tuple[dict, list]:
    """Princeton stations within 25 km of the centre: {station: record}, plus the per-file table."""
    out, table = {}, []
    for f in sorted(root.glob("*.csv")):
        rec = parse_princeton(f)
        row = {k: rec.get(k) for k in ("file", "station", "lat", "lon", "excluded", "hourly_steps")}
        if "excluded" not in rec:
            km = float(haversine_km(np.array([CENTRE, [rec["lat"], rec["lon"]]]))[0, 1])
            row["km"] = round(km, 2)
            if km <= RADIUS_KM:
                out[rec["station"]] = rec
            else:
                row["excluded"] = "outside 25 km"
        table.append(row)
    return out, table


def load_dl15(season: int, root: Path = ROOT / "openaq_cpcb_delhi") -> dict:
    """OpenAQ pages of each location's chosen PM2.5 sensor: epochs at `period.datetimeFrom.utc`, values, coordinates."""
    sl = json.loads((root / "shortlist.json").read_text(encoding="utf-8"))
    out = {}
    for loc in sl["locations"]:
        sid = loc["chosen_sensor"].get(str(season))
        if sid is None:
            continue
        ep, val, interval = [], [], set()
        for f in sorted((root / "raw" / str(season)).glob(f"sensor{sid}_p*.json.gz"),
                        key=lambda p: int(re.search(r"_p(\d+)", p.name).group(1))):
            for r in json.loads(gzip.decompress(f.read_bytes()))["results"]:
                ep.append(int(datetime.fromisoformat(r["period"]["datetimeFrom"]["utc"].replace("Z", "+00:00")).timestamp()))
                val.append(float(r["value"]) if r.get("value") is not None else np.nan)
                interval.add(r["period"].get("interval"))
        if ep:
            out[str(loc["location_id"])] = {"name": loc["name"], "lat": loc["lat"], "lon": loc["lon"], "sensor": sid,
                                            "epochs": ep, "pm": val, "intervals": sorted(i for i in interval if i)}
    return out


# -- analysis -------------------------------------------------------------------------------------------------------
def local_xy_km(latlon) -> np.ndarray:
    """Local tangent plane (km, x east, y north) about the centroid."""
    ll = np.asarray(latlon, dtype=float)
    la0, lo0 = ll.mean(axis=0)
    return np.column_stack([(ll[:, 1] - lo0) * 111.32 * np.cos(np.radians(la0)), (ll[:, 0] - la0) * 110.57])


def front_fit(first_ticks, xy_km, tick_s: int) -> dict | None:
    """Addendum C — least-squares plane t_i = t0 + s·x_i of first-elevated times (min) on positions (km): apparent
    speed (m/s), direction of travel (degrees clockwise from north), residual SD (min) and R²."""
    t = np.asarray(first_ticks, dtype=float) * tick_s / 60.0
    X = np.column_stack([np.ones(len(t)), np.asarray(xy_km, dtype=float)])
    if len(t) < 5 or np.linalg.matrix_rank(X) < 3:
        return None
    coef, *_ = np.linalg.lstsq(X, t, rcond=None)
    res = t - X @ coef
    sst = float(((t - t.mean()) ** 2).sum())
    s = coef[1:]                                                        # min per km
    norm = float(np.hypot(*s))
    return {"speed_ms": round(1000.0 / (60.0 * norm), 3) if norm > 0 else None,
            "direction_deg": round(float(np.degrees(np.arctan2(s[0], s[1])) % 360), 1) if norm > 0 else None,
            "residual_sd_min": round(float(res.std(ddof=3)) if len(t) > 3 else 0.0, 2),
            "r2": round(1.0 - float((res ** 2).sum()) / sst, 3) if sst > 0 else None, "n": int(len(t))}


def _night(hour: int) -> bool:
    return hour >= NIGHT[0] or hour < NIGHT[1]


def catalogue(pm, tick_s: int, t_start: int, w0: int, w1: int, latlon=None) -> dict:
    """The plan's common-mode events (definitions in minutes) for one cluster-year, counted when they start inside
    [w0, w1); per event the plan's statistics, IST start hour, night flag and (with coordinates) the front fit."""
    day = 86400 // tick_s
    y = np.log1p(pm)
    T, N = y.shape
    active = np.isfinite(y)
    med, sc = rolling_baseline(y, win=day, min_valid=day // 2)
    with np.errstate(invalid="ignore"):
        elevated = np.nan_to_num((y - med) / sc, nan=-np.inf) >= 3.0
    f = share(elevated, active, MIN_STATIONS)
    evs = find_events(f, 0.5, 0.25, min_core=max(1, 900 // tick_s), merge=max(1, 3600 // tick_s))
    a0, a1 = (w0 - t_start) // tick_s, (w1 - t_start) // tick_s
    evs = [e for e in evs if a0 <= e[0] < a1]
    xy = local_xy_km(latlon) if latlon is not None else None
    stats = []
    for e in evs:
        st = event_stats(e, elevated, active, pm, med, tick_s=tick_s)
        start = t_start + e[0] * tick_s
        st["start_ist"] = datetime.fromtimestamp(start + IST_S, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        st["start_hour_ist"] = int(((start + IST_S) % 86400) // 3600)
        st["night"] = _night(st["start_hour_ist"])
        if xy is not None:
            E = elevated[e[0]:e[1]]
            inv = np.flatnonzero(E.any(axis=0))
            st["front"] = front_fit([int(np.argmax(E[:, i])) for i in inv], xy[inv], tick_s) if inv.size >= 5 else None
        stats.append(st)
    win = slice(a0, a1)
    days = float(np.isfinite(f[win]).sum()) / day
    excursions = local_excursions(elevated[win], f[win], min_len=max(1, 900 // tick_s))
    zw = ((y - med) / sc)[win]
    zw = zw[np.isfinite(zw)]
    fw = f[win]
    diagnostics = {"note": "exploratory; added after the first run to explain the event rate",
                   "elevated_share_station_ticks": round(float(elevated[win].sum() / max(active[win].sum(), 1)), 4),
                   "z_scale_median_log": round(float(np.nanmedian(sc[win])), 3),
                   "z_q99": round(float(np.percentile(zw, 99)), 2) if zw.size else None,
                   "share_f_q99": round(float(np.nanpercentile(fw, 99)), 3) if np.isfinite(fw).any() else None,
                   "share_f_max": round(float(np.nanmax(fw)), 3) if np.isfinite(fw).any() else None,
                   "ticks_f_ge_0_25": int(np.nansum(fw >= 0.25)), "ticks_f_ge_0_5": int(np.nansum(fw >= 0.5))}
    return {"events": stats, "n_events": len(stats), "days_with_share": round(days, 2), "diagnostics": diagnostics,
            "events_per_day": round(len(stats) / days, 3) if days else None,
            "local_excursions_per_station_day": round(excursions / max(float(active[win].sum()) / day, 1e-9), 4),
            "_masks": (evs, elevated, active, f, med)}


def wilson(k: int, n: int, z: float = 1.96) -> list | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def _q(a, qs=(5, 50, 95)):
    a = np.asarray([v for v in a if v is not None and np.isfinite(v)], float)
    return [round(float(v), 3) for v in np.percentile(a, qs)] if a.size else None


def operator(latlon, haze_params: dict, rng, tick_s: int, n: int = OPERATOR_N) -> dict:
    """Addendum C observation operator — M20b episodes (the unchanged registered class) on the network's coordinates:
    across-station CV of g·u·c over stations with c ≥ 0.5, their onset spread floored to the tick, and the share of
    stations with c ≥ 0.5."""
    from prahari.sensors.haze import M20b
    xy = local_xy_km(latlon) * 1000.0
    p = copy.deepcopy(haze_params)
    p["network_width_m"] = None                    # the swath width uses the network's own span
    p["scripted"] = []
    cv, spread, inv_share = np.empty(n), np.empty(n), np.empty(n)
    for k in range(n):
        m = M20b(p, rng, xy)
        u, c, delay, _ = m._draw_geometry()
        inv = c >= 0.5
        a = (m.gain * u * c)[inv]
        cv[k] = float(a.std() / a.mean()) if a.size >= 2 else np.nan
        d = np.floor(delay[inv] * 60.0 / tick_s) * tick_s / 60.0
        spread[k] = float(d.max() - d.min()) if d.size else np.nan
        inv_share[k] = float(inv.mean())
    return {"cv_q05_50_95": _q(cv), "onset_spread_min_q05_50_95": _q(spread),
            "share_involved_q05_50_95": _q(inv_share), "p_full_coverage": round(float((inv_share >= 0.9).mean()), 3),
            "n": n, "_cv": cv, "_spread": spread}


def node_replay(pm, tick_s: int, t_start: int, evs) -> dict:
    """Addendum C — the plan's node-layer replay at the native tick (7 calibration days, 7 tuning days, test after)."""
    y = np.log1p(pm)
    T, N = y.shape
    active = np.isfinite(y)
    day = 86400 // tick_s
    nl = node_layer(y, IST_S / 3600.0, t_start, tick_s=tick_s)
    rp = replay(nl["p"], nl["z_slow"], active, tick_s=tick_s)
    t1, pad = rp["test0"], 3600 // tick_s
    ev_mask = np.zeros(T, dtype=bool)
    for a, b in evs:
        ev_mask[max(0, a - pad):min(T, b + pad)] = True
    ct = rp["cand_t"]
    test_days = rp["test_ticks"] / day
    n_nodes = int(active[t1:].any(axis=0).sum())
    ok = active[t1:] & ~rp["cm_mask"][t1:, None]
    exceed = float((nl["p"][t1:][ok] <= 0.01).mean()) if ok.any() else None
    return {"h": rp["h"], "h_at_cap": rp["h_at_cap"], "test_days": round(test_days, 2), "nodes": n_nodes,
            "candidates": int(ct.size),
            "candidates_per_node_30d": round(ct.size / max(n_nodes, 1) / test_days * 30, 3) if test_days > 0 else None,
            "share_in_cm_mask": round(float(rp["cm_mask"][ct].mean()), 3) if ct.size else None,
            "share_in_event_spans": round(float(ev_mask[ct].mean()), 3) if ct.size else None,
            "cm_mask_time_share_test": round(float(rp["cm_mask"][t1:].mean()), 3),
            "event_time_share_test": round(float(ev_mask[t1:].mean()), 3),
            "exceedance_outside_cm_at_1pct": round(exceed, 4) if exceed is not None else None}


# -- driver ---------------------------------------------------------------------------------------------------------
def _grid(stations: dict, key: str, t_start: int, T: int, tick_s: int, w0: int, w1: int):
    """Stations passing the coverage rule on the window: (ids, (T, N) array, (lat, lon) rows or None)."""
    a0, a1 = (w0 - t_start) // tick_s, (w1 - t_start) // tick_s
    ids, cols, ll = [], [], []
    for sid in sorted(stations):
        rec = stations[sid]
        g = series(rec["epochs"], rec[key], t_start, T, tick_s)
        if np.isfinite(g[a0:a1]).mean() >= MIN_COVERAGE:
            ids.append(sid)
            cols.append(g)
            ll.append((rec["lat"], rec["lon"]) if "lat" in rec else None)
    arr = np.column_stack(cols) if cols else np.zeros((T, 0))
    return ids, arr, (np.array(ll, dtype=float) if ll and ll[0] is not None else None)


def _spacing(latlon) -> dict | None:
    if latlon is None or len(latlon) < 2:
        return None
    d = haversine_km(np.asarray(latlon, dtype=float))
    iu = np.triu_indices(len(latlon), 1)
    return {"min": round(float(d[iu].min()), 2), "median": round(float(np.median(d[iu])), 2),
            "max": round(float(d[iu].max()), 2)}


def _inside(v, q) -> bool | None:
    if v is None or q is None:
        return None
    return bool(q[0] <= v <= q[2])


def _held_out(events: list, op: dict, rate: float | None) -> dict:
    """Addendum C comparison table for one cluster-year (or pooled events with their own operator intervals)."""
    n = len(events)
    k_night = sum(e["night"] for e in events)
    cvs = [e["peak_excess_cv"] for e in events if e["peak_excess_cv"] is not None]
    spr = [e["onset_spread_min"] for e in events if e["onset_spread_min"] is not None]
    fits = [e["front"] for e in events if e.get("front") and e["front"]["r2"] is not None and e["front"]["r2"] >= 0.5]
    dur = [e["duration_min"] for e in events]
    return {"n_events": n, "events_per_day": rate, "rate_multiplier_vs_h_mix": round(rate / 0.1, 2) if rate else None,
            "night_share": round(k_night / n, 3) if n else None, "night_share_ci95_wilson": wilson(k_night, n),
            "night_share_reference": 0.7,
            "cv_median": _q(cvs, (50,))[0] if cvs else None, "cv_operator_q05_50_95": op["cv_q05_50_95"],
            "cv_share_inside_operator_90": round(np.mean([_inside(v, op["cv_q05_50_95"]) for v in cvs]), 3) if cvs else None,
            "onset_spread_median_min": _q(spr, (50,))[0] if spr else None,
            "onset_spread_operator_q05_50_95": op["onset_spread_min_q05_50_95"],
            "onset_spread_share_inside_operator_90": round(np.mean([_inside(v, op["onset_spread_min_q05_50_95"]) for v in spr]), 3) if spr else None,
            "share_events_involving_ge_90pct": round(np.mean([e["share_involved"] >= 0.9 for e in events
                                                              if e["share_involved"] is not None]), 3) if n else None,
            "operator_p_full_coverage": op["p_full_coverage"],
            "front_fits_r2_ge_0_5": len(fits),
            "front_speed_share_in_1_6_ms": round(np.mean([1.0 <= f["speed_ms"] <= 6.0 for f in fits]), 3) if fits else None,
            "front_speed_median_ms": _q([f["speed_ms"] for f in fits], (50,))[0] if fits else None,
            "duration_share_in_300_840_min": round(np.mean([300 <= d <= 840 for d in dur]), 3) if n else None,
            "duration_median_min": _q(dur, (50,))[0] if dur else None}


def _overlap(a: list, b: list) -> float | None:
    """Share of spans in `a` that overlap any span in `b` (tick pairs [start, end))."""
    if not a:
        return None
    return round(float(np.mean([any(x0 < y1 and y0 < x1 for y0, y1 in b) for x0, x1 in a])), 3)


def provenance(dl: dict, root: Path = ROOT / "openaq_cpcb_delhi") -> dict:
    """Addendum C provenance check: OpenAQ's 2017 CPCB values (hourly means of 15-min periods) against Princeton's
    hourly values at the same stations (within 1 km), 1 Oct–30 Nov 2017 IST."""
    w0, w1 = _ist(2017, 10, 1), _ist(2017, 12, 1)
    oa = load_dl15(2017, root)
    if not oa:
        return {"status": "no 2017 OpenAQ data fetched"}
    rows, rel = [], []
    for lid, r in sorted(oa.items()):
        near = [(float(haversine_km(np.array([[r["lat"], r["lon"]], [p["lat"], p["lon"]]]))[0, 1]), name)
                for name, p in dl.items()]
        km, name = min(near) if near else (None, None)
        if km is None or km > 1.0:
            rows.append({"openaq": r["name"], "match": None})
            continue
        T = (w1 - w0) // 3600
        a = to_grid(np.asarray(r["epochs"]), np.asarray(r["pm"]), w0, T, carry=0, tick_s=3600)
        b = to_grid(np.asarray(dl[name]["epochs"]), np.asarray(dl[name]["pm"]), w0, T, carry=0, tick_s=3600)
        ok = np.isfinite(a) & np.isfinite(b) & (b > 0)
        d = np.abs(a[ok] - b[ok]) / b[ok]
        rel.extend(d.tolist())
        rows.append({"openaq": r["name"], "princeton": name, "km": round(km, 3), "hours_compared": int(ok.sum()),
                     "median_abs_rel_diff": round(float(np.median(d)), 4) if d.size else None})
    return {"window_ist": "2017-10-01 to 2017-11-30", "stations": rows, "matched": sum(1 for r in rows if r.get("princeton")),
            "median_abs_rel_diff_all": round(float(np.median(rel)), 4) if rel else None, "hours": len(rel)}


def analyse(r2: dict | None = None) -> dict:
    from prahari.research.runner_r2 import load_r2, scenario_config
    r2 = r2 or load_r2()
    haze = scenario_config(r2, "H-mix")["params"]["haze"]
    rng = make_rngs(OPERATOR_SEED)["research"]
    dl_all, dl_table = load_dl()
    out, pooled = {}, {}
    for (cl, year), (t0, w0, w1) in SEASONS.items():
        key = f"{cl}-{year}"
        if cl == "AK":
            st, tick = load_ak(year), 3600
        elif cl == "DL":
            st, tick = dl_all, 3600
        else:
            st = load_dl15(year)
            ints = sorted({i for r in st.values() for i in r["intervals"]})
            tick = {("00:15:00",): 900, ("01:00:00",): 3600}.get(tuple(ints))
            if tick is None:
                out[key] = {"analysed": False, "reason": f"mixed or unknown native intervals {ints}"}
                continue
        T = (w1 - t0) // tick
        ids, pm, ll = _grid(st, "pm", t0, T, tick, w0, w1)
        if len(ids) < MIN_STATIONS:
            out[key] = {"analysed": False, "reason": f"{len(ids)} stations pass the coverage rule"}
            continue
        cat = catalogue(pm, tick, t0, w0, w1, ll)
        layout = np.array(AK_LAYOUT) if cl == "AK" else ll
        op = operator(layout, haze, rng, tick)
        evs, *_ = cat["_masks"]
        res = {"analysed": True, "tick_s": tick, "stations": len(ids), "station_ids": ids,
               "spacing_km": _spacing(layout), "spacing_source": "Singh et al. 2023 Table S1 layout" if cl == "AK" else "files",
               **{k: v for k, v in cat.items() if k != "_masks"},
               "operator": {k: v for k, v in op.items() if not k.startswith("_")},
               "held_out": _held_out(cat["events"], op, cat["events_per_day"])}
        for e in cat["events"]:                                                # pooled comparison per cluster
            e["_cv_in"] = _inside(e["peak_excess_cv"], op["cv_q05_50_95"])
            e["_spread_in"] = _inside(e["onset_spread_min"], op["onset_spread_min_q05_50_95"])
        pooled.setdefault(cl, {"events": [], "days": 0.0, "p_full": []})
        pooled[cl]["events"] += cat["events"]
        pooled[cl]["days"] += cat["days_with_share"]
        pooled[cl]["p_full"].append(op["p_full_coverage"])
        if cl == "AK":                                                         # CO channel and pre-season
            cids, co, _ = _grid(st, "co", t0, T, tick, w0, w1)
            if len(cids) >= MIN_STATIONS:
                cc = catalogue(co, tick, t0, w0, w1)
                res["co"] = {"stations": len(cids), "n_events": cc["n_events"], "events_per_day": cc["events_per_day"],
                             "night_share": round(np.mean([e["night"] for e in cc["events"]]), 3) if cc["events"] else None,
                             "share_pm_events_overlapping_co": _overlap(evs, cc["_masks"][0]),
                             "share_co_events_overlapping_pm": _overlap(cc["_masks"][0], evs)}
            else:
                res["co"] = {"analysed": False, "reason": f"{len(cids)} CO stations pass the coverage rule"}
            p0, p1 = PRESEASON[year]
            pids, ppm, _ = _grid(st, "pm", t0, T, tick, p0, p1)
            if len(pids) >= MIN_STATIONS and (p0 - t0) // tick >= 0:
                pc = catalogue(ppm, tick, t0, p0, p1)
                res["preseason_september"] = {"stations": len(pids), "n_events": pc["n_events"],
                                              "events_per_day": pc["events_per_day"],
                                              "night_share": round(np.mean([e["night"] for e in pc["events"]]), 3) if pc["events"] else None}
            else:
                res["preseason_september"] = {"analysed": False, "reason": f"{len(pids)} stations with September data"}
        if cl == "DL15":
            res["node_replay"] = node_replay(pm, tick, t0, evs) if tick == 900 else {
                "analysed": False, "reason": "native interval is 1 h (addendum C)"}
        out[key] = res
    pooled_out = {}
    for cl, p in pooled.items():
        ev = p["events"]
        n, k = len(ev), sum(e["night"] for e in ev)
        cvs = [e["_cv_in"] for e in ev if e["_cv_in"] is not None]
        sps = [e["_spread_in"] for e in ev if e["_spread_in"] is not None]
        fits = [e["front"] for e in ev if e.get("front") and e["front"]["r2"] is not None and e["front"]["r2"] >= 0.5]
        pooled_out[cl] = {"n_events": n, "days_with_share": round(p["days"], 2),
                          "events_per_day": round(n / p["days"], 3) if p["days"] else None,
                          "rate_multiplier_vs_h_mix": round(n / p["days"] / 0.1, 2) if p["days"] else None,
                          "night_share": round(k / n, 3) if n else None, "night_share_ci95_wilson": wilson(k, n),
                          "cv_share_inside_operator_90": round(float(np.mean(cvs)), 3) if cvs else None,
                          "onset_spread_share_inside_operator_90": round(float(np.mean(sps)), 3) if sps else None,
                          "share_events_involving_ge_90pct": round(float(np.mean([e["share_involved"] >= 0.9 for e in ev])), 3) if n else None,
                          "operator_p_full_coverage_mean": round(float(np.mean(p["p_full"])), 3),
                          "front_fits_r2_ge_0_5": len(fits),
                          "front_speed_share_in_1_6_ms": round(float(np.mean([1 <= f["speed_ms"] <= 6 for f in fits])), 3) if fits else None,
                          "duration_share_in_300_840_min": round(float(np.mean([300 <= e["duration_min"] <= 840 for e in ev])), 3) if n else None}
    for cl in pooled:
        for e in pooled[cl]["events"]:
            e.pop("_cv_in", None)
            e.pop("_spread_in", None)
    return {"label": "REAL (exploratory)", "plan": "docs/research/realdata-plan.md, addendum C",
            "sources": {"AK": "Aakash project, RIHN; CC BY-NC-ND 4.0 (no redistribution)",
                        "DL": "Sharma & Mauzerall (2021), Princeton, doi:10.34770/60j3-yp02; CC BY 4.0",
                        "DL15": "CPCB through OpenAQ v3; no licence listed by OpenAQ; developer's decision (DECISIONS P-9)"},
            "operator": {"seed": OPERATOR_SEED, "draws": OPERATOR_N, "model": "prahari.sensors.haze.M20b, r2.yaml H-mix"},
            "clusters": out, "pooled": pooled_out, "princeton_files": dl_table, "provenance_2017": provenance(dl_all)}


def write_realdata_india(out: Path) -> list[str]:
    from prahari.record.writer import write_text_atomic
    res = analyse()
    p = Path(out) / "real_india.json"
    write_text_atomic(p, json.dumps(res, indent=1, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)))
    return [str(p)]
