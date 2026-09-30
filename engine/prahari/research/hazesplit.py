"""Inside/outside-haze decomposition of false incidents (DECISIONS R2-10; descriptive, not part of protocol R1's tests).

`incident_list` is M46's merge rule (`eval.stats.incidents`) returning each incident instead of the count; the count
is identical by construction and tested. Haze episodes are the contiguous minutes with H(t) > 0 (M20, trapezoids
including their ramps). An incident is *inside* haze when an episode is active at its first alarm (primary tag) or
within the 60 minutes before it (secondary tag, the M28 common-mode padding).
"""
from __future__ import annotations

import numpy as np

PAD_MIN = 60                                   # secondary tag: the M28 common-mode padding (cm_pad_min)


def incident_list(alarms, dist, R: float, t_from: int, t_to: int, merge_min: int = 60,
                  merge_factor: float = 2.0) -> list:
    """M46 — the incidents themselves: [first alarm minute, last alarm minute, nodes], in order of their first alarm."""
    inc: list = []
    for t, i, loc in alarms:
        if t < t_from or t >= t_to:
            continue
        for m in inc:
            if t - m[1] <= merge_min and min(dist[i, j] for j in m[2]) <= merge_factor * R:
                m[1] = t
                m[2].update(loc)
                break
        else:
            inc.append([t, t, set(loc)])
    return inc


def episodes(level) -> list:
    """Haze episodes as [start minute, end minute (exclusive), peak H] from the per-minute level H(t)."""
    on = np.asarray(level) > 0
    if not on.any():
        return []
    d = np.diff(on.astype(np.int8), prepend=0, append=0)
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return [[int(a), int(b), round(float(np.max(level[a:b])), 4)] for a, b in zip(starts, ends)]


def active_mask(eps: list, T: int, pad: int = 0):
    """Minutes with an episode active, or ended at most `pad` minutes earlier."""
    m = np.zeros(T, dtype=bool)
    for a, b, _ in eps:
        m[a:min(b + pad, T)] = True
    return m


def fire_overlaps(eps: list, fires, T: int, window: int = 180) -> list[bool]:
    """Per protocol fire: does a haze episode overlap [t0, t0 + window)?"""
    m = active_mask(eps, T)
    return [bool(m[int(t0):min(int(t0) + window, T)].any()) for t0, _ in fires]
