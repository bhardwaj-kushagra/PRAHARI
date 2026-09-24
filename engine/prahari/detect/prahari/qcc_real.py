"""Quantile-calibrated conformal p-values, QCC — real implementation (SPEC §5.8, M26).

For each node and each 4-hour time-of-day bin, the calibration scores are the fast residuals α = r (M25) seen so far.
p_t = (1 + #{α_j ≥ α_t}) / (n + 1), so p never falls below p_min = 1/(n + 1) and the floor falls as the set grows.

- `window: frozen` (default, the report simulation): the set grows over the first `cal_days`, then is frozen,
  sorted once and searched with a binary search.
- `window: sliding` (advanced, SPEC maturity window): the set keeps the last `window_days` of scores per bin.

While a set is still growing, each score is compared with the set so far and then appended (online conformal).

`form: robust_z` is the report simulation's "minus conformal" ablation (P7-12): no ranks, only the fast residual
scaled by each node's calibration median and MAD; the signed z travels in `PValues.z` for a z-statistic CUSUM.
"""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr

from prahari.core.clock import MINUTES_PER_DAY
from prahari.core.contracts import PValues, Residuals
from prahari.core.registry import Stage, register
from prahari.detect.prahari.qcc import P_FLOOR


def conformal_p_counts(cal, n: int, score):
    """M26 by counting — cal (M, ≥ n) rows of calibration scores (unsorted), score (M,) → p (M,)."""
    ge = (cal[:, :n] >= score[:, None]).sum(axis=1)
    return (1.0 + ge) / (n + 1.0)


def robust_z(r, med, mad):
    """Legacy ablation — z = (r − median) / (1.4826 · MAD), the report simulation's `gauss_z` (MAD passed unscaled)."""
    return (r - med) / (1.4826 * mad)


class RowSearch:
    """M26 with a binary search on every row at once: rows are sorted, offset so that the concatenation is sorted,
    and searched with one `numpy.searchsorted` call."""

    def __init__(self, cal):
        self.rows = np.sort(cal, axis=1)
        m, self.n = self.rows.shape
        lo, hi = (float(self.rows.min()), float(self.rows.max())) if self.rows.size else (0.0, 0.0)
        self.clip = (lo - 1.0, hi + 1.0)
        self.off = np.arange(m) * (hi - lo + 4.0)            # row bands never overlap, even after clipping
        self.flat = (self.rows + self.off[:, None]).ravel()
        self.start = np.arange(m) * self.n

    def p(self, score):
        """M26 — p = (1 + |{j : α_j ≥ α_t}|) / (n + 1), counted with a binary search."""
        if self.n == 0:
            return np.ones_like(score)
        q = np.clip(score, *self.clip) + self.off
        ge = self.n - (np.searchsorted(self.flat, q, side="left") - self.start)
        return (1.0 + ge) / (self.n + 1.0)


@register("qcc", kind="real")
class QCCReal(Stage):
    equation = "M26"
    tag = "LIT"
    description = "Conformal p-value of the fast residual per node and 4-hour time-of-day bin"

    def reset(self, ctx) -> None:
        p, tick = self.params, ctx.tick_minutes
        self._bins = int(p["bins"])
        self._bin_min = MINUTES_PER_DAY // self._bins
        self._sliding = p["window"] == "sliding"
        days = int(p["window_days"] if self._sliding else p["cal_days"])
        self._cap = days * self._bin_min // tick                 # samples per bin once the window is full
        self._freeze_t = int(p["cal_days"]) * MINUTES_PER_DAY    # frozen mode: scores from t < this calibrate
        self._cal = None
        self._n = np.zeros(self._bins, dtype=np.int64)          # samples in each bin (all nodes alike)
        self._head = np.zeros(self._bins, dtype=np.int64)       # next write position (sliding ring)
        self._search: dict[int, RowSearch] = {}
        self._robust = p.get("form", "conformal") == "robust_z"
        self._hist: list = []                                    # robust_z: calibration residuals, then (med, mad)
        self._scale = None

    def step(self, res: Residuals, ctx) -> PValues:
        if self._robust:
            return self._robust_step(res, ctx)
        a = res.r                                                # M26 — α = r, the fast residual
        shape = a.shape
        a = a.reshape(-1)
        if self._cal is None:
            self._cal = np.zeros((self._bins, a.size, self._cap))
        b = ctx.clock.tod_minutes(ctx.t) // self._bin_min
        ok = np.isfinite(a)
        s = np.where(ok, a, 0.0)
        n = int(self._n[b])
        if b in self._search:
            p = self._search[b].p(s)
        elif n == 0:
            p = np.ones_like(s)
        else:
            p = conformal_p_counts(self._cal[b], n, s)
        p = np.where(ok, p, 1.0)                                 # missing data carries no evidence
        self._learn(b, a, ok, ctx.t)
        n_cal = np.full(shape[0], float(n))                      # the set this p was computed against: floor 1/(n+1)
        return PValues(p=np.clip(p, P_FLOOR, 1.0).reshape(shape), n_cal=n_cal)

    def _robust_step(self, res: Residuals, ctx) -> PValues:
        """Legacy "minus conformal": median and MAD per node over the calibration days, then z and p = Φ(−z)."""
        r = res.r
        if self._scale is None and ctx.t >= self._freeze_t and self._hist:
            h = np.stack(self._hist)                             # (T_cal, N, C)
            med = np.median(h, axis=0)
            self._scale = (med, np.median(np.abs(h - med), axis=0))
            self._hist = []
        if self._scale is None:
            self._hist.append(np.array(r, dtype=float))
            z, p = np.zeros_like(r, dtype=float), np.ones_like(r, dtype=float)   # no evidence before the scale exists
        else:
            z = robust_z(r, *self._scale)
            z = np.where(np.isfinite(z), z, 0.0)
            p = np.clip(ndtr(-z), P_FLOOR, 1.0)
        return PValues(p=p, n_cal=np.zeros(r.shape[0]), z=z)

    def _learn(self, b: int, a, ok, t: int) -> None:
        if b in self._search or not ok.all():                    # frozen, or a gap: keep the set exchangeable
            return
        if not self._sliding and t >= self._freeze_t:
            n = int(self._n[b])
            self._search[b] = RowSearch(self._cal[b, :, :n])
            return
        self._cal[b, :, self._head[b] % self._cap] = a
        self._head[b] += 1
        self._n[b] = min(self._n[b] + 1, self._cap)

    def snapshot(self) -> dict:
        p = self.params
        return {**({"form": "robust_z"} if self._robust else {}), "window": p["window"], "cal_days": p["cal_days"],
                "bins": p["bins"], "window_days": p["window_days"] if p["window"] == "sliding" else p["cal_days"]}
