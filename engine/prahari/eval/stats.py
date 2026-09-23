"""Evaluation statistics and counting rules (SPEC §5.14): M44, M45, M46.

`incidents` and `detect` follow `reference/prahari_simulation.py` line for line so that counts match the report.
Alarms are tuples (t, node, members) in time order.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import chi2


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """M44 — Wilson score interval for k successes in n trials."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float((c - h) / d), float((c + h) / d)


def poisson_ci(k: int, alpha: float = 0.05) -> tuple[float, float]:
    """M45 — exact Poisson interval for an observed count k: [½χ²_{α/2}(2k), ½χ²_{1−α/2}(2k+2)]."""
    lo = 0.5 * chi2.ppf(alpha / 2, 2 * k) if k > 0 else 0.0
    return float(lo), float(0.5 * chi2.ppf(1 - alpha / 2, 2 * k + 2))


def per_month(k: int, days: float, month_days: float = 30.0) -> dict:
    """M45 — rate per month with its exact interval, from k events over `days`."""
    lo, hi = poisson_ci(k)
    s = month_days / days
    return {"rate": k * s, "ci95": [lo * s, hi * s], "count": int(k), "days": float(days)}


def incidents(alarms, dist, R: float, t_from: int, t_to: int, merge_min: int = 60, merge_factor: float = 2.0) -> int:
    """M46 — merge alarms within `merge_min` minutes and `merge_factor`·R of an incident's nodes; count incidents."""
    inc = []  # [t_last, nodes]
    for t, i, loc in alarms:
        if t < t_from or t >= t_to:
            continue
        for m in inc:
            if t - m[0] <= merge_min and min(dist[i, j] for j in m[1]) <= merge_factor * R:
                m[0] = t
                m[1].update(loc)
                break
        else:
            inc.append([t, set(loc)])
    return len(inc)


def detect(alarms, fires, xy, radius: float = 150.0, window_min: int = 180) -> list:
    """M46 — per fire (t0, (x, y)): latency to the first alarm within `window_min` involving a node within `radius`
    of the ignition; None when missed."""
    al = sorted(alarms)
    lat = []
    for t0, ign in fires:
        near = None
        for t, i, loc in al:
            if t < t0:
                continue
            if t > t0 + window_min:
                break
            if any(np.hypot(*(xy[n] - ign)) <= radius for n in loc):
                near = t - t0
                break
        lat.append(near)
    return lat
