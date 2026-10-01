"""Real-data analysis of the Thompson et al. (2026) N5 networks (exploratory, REAL; plan: docs/research/realdata-plan.md).

Two questions: (1) how often and how evenly do many stations of a real low-cost network rise together (common-mode
events), and (2) when PRAHARI's node layer runs on real PM2.5, what share of its quiet-data candidates fall inside
those network-wide events. Pure functions over (T, N) arrays on a 5-minute grid; NaN marks an inactive station.
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import numpy as np

from prahari.detect.prahari.qcc import P_FLOOR
from prahari.detect.prahari.ttc_real import ttc_slow_step
from prahari.detect.prahari.tuning import cusum_replay, cm_mask, tune_h

TICK_S = 300                                     # 5-minute grid (N5 cadence)
DAY = 86400 // TICK_S                            # 288 ticks
PREFIX = "nrcan-cfs-fire-Ground-smoke-sensors-6e6b887/"
CLUSTERS = {"WR": -6, "BC": -4, "VC": -4, "RC": -7}    # clusters with ≥ 5 stations; UTC offset in April 2024
FIRE_TZ = -7                                     # WainwrightApr2024.csv times (Etc/GMT+7, as the paper's Rmd)


# -- loading ---------------------------------------------------------------------------------------------------
def _csv(z: zipfile.ZipFile, name: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(z.read(PREFIX + name).decode("utf-8-sig"))))


def _f(v: str) -> float:
    return float(v) if v not in ("", "NA") else np.nan


def load(zip_path: str | Path) -> dict:
    """Readings, station table and Wainwright fire list from the archive (read only)."""
    z = zipfile.ZipFile(zip_path)
    rows = _csv(z, "WR.csv")
    stations = {r["Sensor ID"]: {"name": r["Sensor Name"], "lat": float(r["Lat"]), "lon": float(r["Long"])}
                for r in _csv(z, "Sensor_Locs.csv")}
    fires = [{"name": r["FireName"], "lat": float(r["LAT"]), "lon": float(r["LONG"]), "type": r["FireType"],
              "area_ha": _f(r["ReportedFinalArea"]),
              "ign_epoch": _local_to_epoch(r["ReportedIgnTime"], FIRE_TZ)} for r in _csv(z, "WainwrightApr2024.csv")]
    return {"rows": rows, "stations": stations, "fires": fires}


def _local_to_epoch(s: str, tz_hours: int) -> int:
    from datetime import datetime, timezone
    d = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return int(d.timestamp()) - tz_hours * 3600


def to_grid(epochs, values, t_start: int, T: int, carry: int = 3, tick_s: int = TICK_S):
    """Readings onto the grid (5-minute by default): mean per bin; gaps of ≤ `carry` bins carried forward, longer gaps
    NaN."""
    g = np.full(T, np.nan)
    idx = (np.asarray(epochs) - t_start) // tick_s
    ok = (idx >= 0) & (idx < T) & np.isfinite(values)
    s = np.bincount(idx[ok], weights=np.asarray(values)[ok], minlength=T)
    c = np.bincount(idx[ok], minlength=T)
    has = c > 0
    g[has] = s[has] / c[has]
    last, run = np.nan, 0
    for t in range(T):
        if np.isfinite(g[t]):
            last, run = g[t], 0
        elif np.isfinite(last) and run < carry:
            g[t] = last
            run += 1
    return g


def cluster_arrays(data: dict, cluster: str) -> dict:
    """PM2.5 of one site cluster on a common 5-minute grid: y = ln(1 + PM2.5), PM, station ids and coordinates."""
    ids = sorted(s for s, v in data["stations"].items() if v["name"].startswith(cluster + "_"))
    by = {s: [] for s in ids}
    for r in data["rows"]:
        if r["stationID"] in by:
            by[r["stationID"]].append((int(r["UnixTime"]), _f(r["PM2P5"])))
    ids = [s for s in ids if by[s]]
    t_start = min(min(e for e, _ in by[s]) for s in ids) // TICK_S * TICK_S
    t_end = max(max(e for e, _ in by[s]) for s in ids)
    T = (t_end - t_start) // TICK_S + 1
    pm = np.stack([to_grid([e for e, _ in by[s]], np.array([v for _, v in by[s]]), t_start, T) for s in ids], axis=1)
    pm = np.where(pm < 0, 0.0, pm)
    ll = np.array([[data["stations"][s]["lat"], data["stations"][s]["lon"]] for s in ids])
    return {"ids": ids, "t_start": t_start, "pm": pm, "y": np.log1p(pm), "latlon": ll}


def haversine_km(ll):
    """Pairwise great-circle distances (km) between (lat, lon) rows."""
    la, lo = np.radians(ll[:, 0]), np.radians(ll[:, 1])
    d = np.sin((la[:, None] - la[None]) / 2) ** 2 + np.cos(la[:, None]) * np.cos(la[None]) * np.sin((lo[:, None] - lo[None]) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(d))


# -- common-mode events ----------------------------------------------------------------------------------------
def rolling_baseline(y, win: int = DAY, min_valid: int = DAY // 2, floor: float = 0.05):
    """Causal robust baseline per station: median and 1.4826·MAD over the previous `win` ticks (NaN until
    `min_valid` valid values exist)."""
    T, N = y.shape
    med = np.full((T, N), np.nan)
    sc = np.full((T, N), np.nan)
    for i in range(N):
        col = y[:, i]
        for t in range(1, T):
            w = col[max(0, t - win):t]
            w = w[np.isfinite(w)]
            if w.size >= min_valid:
                m = np.median(w)
                med[t, i] = m
                sc[t, i] = max(1.4826 * np.median(np.abs(w - m)), floor)
    return med, sc


def share(elevated, active, min_active: int = 5):
    """Network share of active stations that are elevated; NaN where fewer than `min_active` are active."""
    n = active.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        f = elevated.sum(axis=1) / n
    return np.where(n >= min_active, f, np.nan)


def find_events(f, core: float = 0.5, span: float = 0.25, min_core: int = 3, merge: int = 12) -> list:
    """Events: a core run of f ≥ `core` lasting ≥ `min_core` ticks, extended while f ≥ `span`; spans closer than
    `merge` ticks are joined. Returns [start, end) tick pairs."""
    f = np.nan_to_num(np.asarray(f, float), nan=0.0)
    hi, lo = f >= core, f >= span
    out = []
    t, T = 0, f.size
    while t < T:
        if hi[t]:
            e = t
            while e < T and hi[e]:
                e += 1
            if e - t >= min_core:
                a, b = t, e
                while a > 0 and lo[a - 1]:
                    a -= 1
                while b < T and lo[b]:
                    b += 1
                if out and a - out[-1][1] < merge:
                    out[-1][1] = max(out[-1][1], b)
                elif not out or a >= out[-1][1]:
                    out.append([a, b])
                t = max(b, e)
                continue
            t = e
            continue
        t += 1
    return [tuple(x) for x in out]


def event_stats(ev, elevated, active, pm, med_y, tick_s: int = TICK_S) -> dict:
    """Per event: duration, station share involved, onset spread (min), peak excess PM2.5 per involved station."""
    a, b = ev
    E, A = elevated[a:b], active[a:b]
    inv = np.flatnonzero(E.any(axis=0))
    first = [int(np.argmax(E[:, i])) for i in inv]
    base = np.expm1(np.nanmedian(med_y[a:b][:, inv], axis=0)) if inv.size else np.array([])
    peak = np.nanmax(pm[a:b][:, inv], axis=0) - base if inv.size else np.array([])
    n_act = int(A.any(axis=0).sum())
    return {"start_tick": int(a), "end_tick": int(b), "duration_min": int((b - a) * tick_s // 60),
            "stations_involved": int(inv.size), "stations_active": n_act,
            "share_involved": round(inv.size / n_act, 3) if n_act else None,
            "onset_spread_min": int((max(first) - min(first)) * tick_s // 60) if first else None,
            "peak_excess_median": round(float(np.median(peak)), 1) if peak.size else None,
            "peak_excess_cv": round(float(np.std(peak) / np.mean(peak)), 3) if peak.size and np.mean(peak) > 0 else None}


def local_excursions(elevated, f, min_len: int = 3) -> int:
    """Runs of ≥ `min_len` ticks in which exactly one station is elevated while the network share is < 0.25."""
    one = (elevated.sum(axis=1) == 1) & (np.nan_to_num(f, nan=1.0) < 0.25)
    n, run = 0, 0
    for v in one:
        run = run + 1 if v else 0
        if run == min_len:
            n += 1
    return n


# -- PRAHARI node layer on real data ----------------------------------------------------------------------------
def node_layer(y, tz_hours: float, t_start: int, cal_days: int = 7, bins: int = 6, alpha_min: float = 720.0,
               freeze: float = 3.0, cap_min: int = 180, lag0_min: int = 60, lag1_min: int = 180, var_floor: float = 1e-4,
               tick_s: int = TICK_S):
    """M24–M26 on the grid (5-minute by default): capped slow z (for the M28 common-mode share), lagged fast residual,
    and the conformal p-value per station and 4-hour local time-of-day bin, frozen after `cal_days`. Missing → p = 1."""
    T, N = y.shape
    tick_min = tick_s // 60
    day = 86400 // tick_s
    alpha, fmax = tick_min / alpha_min, cap_min // tick_min
    lag0, lag1 = lag0_min // tick_min, lag1_min // tick_min
    # M24 — slow baseline, initialised from the first day's valid values, updates skipped at missing ticks
    d1 = y[:day]
    n1 = np.isfinite(d1).sum(axis=0)
    b = np.where(n1 > 0, np.nansum(d1, axis=0) / np.maximum(n1, 1), 0.0)
    s2 = np.where(n1 > 1, np.nansum((d1 - b) ** 2, axis=0) / np.maximum(n1, 1), 1.0) + var_floor
    fz = np.zeros(N, dtype=np.int64)
    z = np.full((T, N), np.nan)
    for t in range(T):
        ok = np.isfinite(y[t])
        if not ok.any():
            continue
        zt, bn, s2n, fzn = ttc_slow_step(b, s2, np.where(ok, y[t], b), fz, alpha, freeze, fmax)
        z[t] = np.where(ok, zt, np.nan)
        b, s2, fz = np.where(ok, bn, b), np.where(ok, s2n, s2), np.where(ok, fzn, fz)
    # M25 — fast residual against the mean of ticks t−lag1 … t−lag0−1 (≥ half the window valid)
    r = np.full((T, N), np.nan)
    for t in range(lag1, T):
        w = y[t - lag1:t - lag0]
        cnt = np.isfinite(w).sum(axis=0)
        m = np.where(cnt > 0, np.nansum(w, axis=0) / np.maximum(cnt, 1), np.nan)
        r[t] = np.where(cnt >= (lag1 - lag0) // 2, y[t] - m, np.nan)
    # M26 — conformal p per station and local 4-hour bin, calibration set from the first `cal_days`
    tod_bin = (((np.arange(T) * tick_s + t_start + tz_hours * 3600) % 86400) // (86400 // bins)).astype(int)
    cal_end = cal_days * day
    p = np.ones((T, N))
    for k in range(bins):
        sel = tod_bin == k
        cal_idx = np.flatnonzero(sel[:cal_end])
        for i in range(N):
            cal = np.sort(r[cal_idx, i][np.isfinite(r[cal_idx, i])])
            if cal.size == 0:
                continue
            idx = np.flatnonzero(sel)
            a = r[idx, i]
            ge = cal.size - np.searchsorted(cal, np.where(np.isfinite(a), a, np.inf), side="left")
            p[idx, i] = np.where(np.isfinite(a), (1.0 + ge) / (cal.size + 1.0), 1.0)      # M26
    return {"z_slow": z, "r": r, "p": np.clip(p, P_FLOOR, 1.0)}


def replay(p, z_slow, active, cal_days: int = 7, tune_days: int = 7, target_per_node_30d: float = 1.0,
           k: float = 1.5, ref_min: int = 30, cm_z: float = 3.0, cm_frac: float = 0.25, pad_min: int = 60,
           h_lo: float = 0.5, h_hi: float = 5000.0, iters: int = 22, tick_s: int = TICK_S):
    """M28 on real data: −ln p evidence, one h for the network replay-tuned to the target on the tuning days with
    common-mode ticks (share of slow z ≥ cm_z at least cm_frac, padded) excluded; candidates on the test days."""
    tick_min = tick_s // 60
    day = 86400 // tick_s
    T, N = p.shape
    S = -np.log(p)                                                                   # M28 — node evidence
    elev = np.nan_to_num(z_slow, nan=-np.inf) >= cm_z
    frac = share(elev, active, min_active=1)
    cm = cm_mask(np.nan_to_num(frac, nan=0.0), cm_frac, pad_min // tick_min)
    t0, t1 = cal_days * day, (cal_days + tune_days) * day
    n_active = float(active[t0:t1].any(axis=0).sum())
    target = target_per_node_30d / 30.0 * n_active * tune_days
    ref = ref_min // tick_min
    h = tune_h(S[t0:t1], k, cm[t0:t1], target, h_lo, h_hi, iters, ref)
    ts, ns = cusum_replay(S[t1:], k, h, ref)
    return {"h": float(h), "h_at_cap": bool(h >= h_hi), "cand_t": ts + t1, "cand_node": ns, "cm_mask": cm,
            "test0": t1, "test_ticks": T - t1}
