"""Driver for the real-data analysis (docs/research/realdata-plan.md): per cluster, the common-mode event catalogue and
the node-layer replay decomposition, written to results/research/real_thompson2026.json (REAL, exploratory)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from prahari.record.writer import write_text_atomic
from prahari.research.realdata import (CLUSTERS, DAY, TICK_S, cluster_arrays, event_stats, find_events, haversine_km,
                                       load, local_excursions, node_layer, replay, rolling_baseline, share)

ZIP = Path("data/real/thompson2026/raw/Ground-smoke-sensors-2026-01-12.zip")
FIRE_RADIUS_KM, FIRE_LEAD_S = 20.0, 6 * 3600


def _q(a, qs=(10, 50, 90)):
    a = np.asarray([v for v in a if v is not None], float)
    return [round(float(v), 2) for v in np.percentile(a, qs)] if a.size else None


def analyse_cluster(data: dict, cluster: str) -> dict:
    """Events, local excursions and the node-replay decomposition for one site cluster."""
    c = cluster_arrays(data, cluster)
    y, pm, t_start, tz = c["y"], c["pm"], c["t_start"], CLUSTERS[cluster]
    T, N = y.shape
    active = np.isfinite(y)
    med, sc = rolling_baseline(y)
    with np.errstate(invalid="ignore"):
        elevated = np.nan_to_num((y - med) / sc, nan=-np.inf) >= 3.0
    f = share(elevated, active)
    evs = find_events(f)
    stats = [event_stats(e, elevated, active, pm, med) for e in evs]
    centroid = c["latlon"].mean(axis=0)
    for e, st in zip(evs, stats):
        st["start_utc_epoch"] = int(t_start + e[0] * TICK_S)
        st["start_local_hour"] = int(((t_start + e[0] * TICK_S + tz * 3600) % 86400) // 3600)
        st["attribution"] = "no fire records"
        if cluster == "WR":
            a0, a1 = t_start + e[0] * TICK_S, t_start + e[1] * TICK_S
            near = [fi["name"] for fi in data["fires"]
                    if haversine_km(np.array([centroid, [fi["lat"], fi["lon"]]]))[0, 1] <= FIRE_RADIUS_KM
                    and a0 - FIRE_LEAD_S <= fi["ign_epoch"] <= a1]
            st["attribution"] = ("fire: " + ",".join(near)) if near else "unattributed"
    days_valid = float(np.isfinite(f).sum()) / DAY
    d = haversine_km(c["latlon"])
    iu = np.triu_indices(N, 1)
    # node layer on real PM2.5 and the inside/outside decomposition of its test-period candidates
    nl = node_layer(y, tz, t_start)
    rp = replay(nl["p"], nl["z_slow"], active)
    t1 = rp["test0"]
    ev_mask = np.zeros(T, dtype=bool)
    for a, b in evs:
        ev_mask[max(0, a - 12):min(T, b + 12)] = True
    fire_mask = np.zeros(T, dtype=bool)
    for (a, b), st in zip(evs, stats):
        if st["attribution"].startswith("fire"):
            fire_mask[max(0, a - 12):min(T, b + 12)] = True
    # Addition to the plan (labelled in realdata.md): WR's test days contain recorded fires, so candidates within 24 h
    # after a recorded ignition within 20 km are real smoke, not false alarms.
    fire24 = np.zeros(T, dtype=bool)
    if cluster == "WR":
        for fi in data["fires"]:
            if haversine_km(np.array([centroid, [fi["lat"], fi["lon"]]]))[0, 1] <= FIRE_RADIUS_KM:
                a = (fi["ign_epoch"] - t_start) // TICK_S
                fire24[max(0, a):max(0, min(T, a + DAY))] = True
    ct = rp["cand_t"]
    test_days = rp["test_ticks"] / DAY
    n_nodes = int(active[t1:].any(axis=0).sum())
    ok = active[t1:] & ~rp["cm_mask"][t1:, None]
    exceed = float((nl["p"][t1:][ok] <= 0.01).mean()) if ok.any() else None
    return {"cluster": cluster, "stations": len(c["ids"]), "days_with_share": round(days_valid, 2),
            "spacing_km": {"min": round(float(d[iu].min()), 2), "median": round(float(np.median(d[iu])), 2),
                           "max": round(float(d[iu].max()), 2)},
            "events": stats, "n_events": len(stats),
            "events_per_day": round(len(stats) / days_valid, 3) if days_valid else None,
            "event_duration_min_q10_50_90": _q([s["duration_min"] for s in stats]),
            "onset_spread_min_q10_50_90": _q([s["onset_spread_min"] for s in stats]),
            "share_involved_q10_50_90": _q([s["share_involved"] for s in stats]),
            "peak_excess_cv_q10_50_90": _q([s["peak_excess_cv"] for s in stats]),
            "peak_excess_median_q10_50_90": _q([s["peak_excess_median"] for s in stats]),
            "local_excursions_per_station_day": round(local_excursions(elevated, f) / max(float(active.sum()) / DAY, 1e-9), 4),
            "node_replay": {"h": rp["h"], "h_at_cap": rp["h_at_cap"], "test_days": round(test_days, 2), "nodes": n_nodes,
                            "candidates": int(ct.size),
                            "candidates_per_node_30d": round(ct.size / max(n_nodes, 1) / test_days * 30, 3) if test_days > 0 else None,
                            "share_in_cm_mask": round(float(rp["cm_mask"][ct].mean()), 3) if ct.size else None,
                            "share_in_event_spans": round(float(ev_mask[ct].mean()), 3) if ct.size else None,
                            "share_in_fire_events": round(float(fire_mask[ct].mean()), 3) if ct.size else None,
                            "share_within_24h_of_recorded_fire": round(float(fire24[ct].mean()), 3) if ct.size and cluster == "WR" else None,
                            "candidates_outside_fire_windows_per_node_30d": round(float((~fire24[ct]).sum()) / max(n_nodes, 1) / max(float((~fire24[t1:]).sum()) / DAY, 1e-9) * 30, 3) if ct.size and cluster == "WR" else None,
                            "cm_mask_time_share_test": round(float(rp["cm_mask"][t1:].mean()), 3),
                            "event_time_share_test": round(float(ev_mask[t1:].mean()), 3),
                            "exceedance_outside_cm_at_1pct": round(exceed, 4) if exceed is not None else None}}


def write_realdata(out: Path, zip_path: Path = ZIP) -> list[str]:
    """Run the plan's analysis for every cluster and write results/research/real_thompson2026.json."""
    data = load(zip_path)
    res = {"label": "REAL (exploratory)", "source": "Thompson, Fusina & Jackson (2026), Fire 9:141; "
           "doi:10.5281/zenodo.18222779 (MIT)", "plan": "docs/research/realdata-plan.md", "tick_s": TICK_S,
           "clusters": {cl: analyse_cluster(data, cl) for cl in CLUSTERS}}
    p = Path(out) / "real_thompson2026.json"
    write_text_atomic(p, json.dumps(res, indent=1))
    return [str(p)]
