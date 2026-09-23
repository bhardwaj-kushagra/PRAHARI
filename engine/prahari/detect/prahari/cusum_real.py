"""Node CUSUM — real implementation (SPEC §5.8, M28): −ln p evidence, k = 1.5, replay-tuned threshold h.

Until the tuning window has been seen (runs shorter than calibration + tuning, such as demo recordings) the
threshold is `h_default` (SPEC §10 fallback, DER from the report simulation). At the end of the tuning window h is
set by bisection (`tuning.py`) and the CUSUM restarts from zero. The stub (v1 CUSUM, M23) is in `cusum.py`.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Candidates, Scores
from prahari.core.registry import Stage, register
from prahari.detect.prahari.qcc import P_FLOOR
from prahari.detect.prahari.tuning import TuningBuffer, tune_from_buffer


def elevated_fraction(z, thr: float) -> float:
    """M28 — share of nodes whose slow z (first channel) is at least `thr` (one-sided, as the report simulation)."""
    if z is None:
        return 0.0
    z = z[:, 0] if z.ndim == 2 else z
    return float((z >= thr).mean())


@register("cusum", kind="real")
class CusumReal(Stage):
    equation = "M28"
    tag = "LIT"
    description = "CUSUM of −ln p with k = 1.5; h replay-tuned to 1 node-local false candidate per node per 30 days"

    def reset(self, ctx) -> None:
        p, n = self.params, ctx.n_nodes
        self._G = np.zeros(n)
        self._ref = np.zeros(n, dtype=np.int64)
        self._ref_ticks = int(p["refractory_min"]) // ctx.tick_minutes
        self._h = float(p["h_default"])
        self._tuned = False
        self._at_cap = False
        self._buf = TuningBuffer(int(p["tune_start_min"]), int(p["tune_end_min"]), int(p["cm_pad_min"]),
                                 ctx.tick_minutes)

    def step(self, sc: Scores, ctx) -> Candidates:
        p, t = self.params, ctx.t
        s = -np.log(np.clip(sc.p_node, P_FLOOR, 1.0))           # M28 — node evidence −ln p^node
        if self._buf is not None:
            self._buf.add(t, s, elevated_fraction(getattr(ctx, "z_slow", None), float(p["cm_z"])))
        if self._buf is not None and self._buf.ready(t):
            self._h, self._at_cap = tune_from_buffer(self._buf, p, float(p["k_node"]), self._ref_ticks)
            self._tuned = True
            self._buf = None
            self._G[:] = 0.0
            self._ref[:] = 0
        if t < p["start_min"]:
            return Candidates(nodes=(), p=(), G=self._G.copy(), h=self._h)
        G_pre = np.maximum(0.0, self._G + s - float(p["k_node"]))    # M28 — G ← max(0, G − ln p − k)
        hit = (G_pre > self._h) & (self._ref == 0)
        self._G = np.where(hit, 0.0, G_pre)
        self._ref = np.where(hit, self._ref_ticks, self._ref)
        self._ref = np.maximum(self._ref - 1, 0)                 # refractory as in the report simulation
        nodes = np.flatnonzero(hit)
        G_out = np.where(hit, G_pre, self._G)                    # report the crossing value on a hit
        return Candidates(nodes=tuple(int(i) for i in nodes), p=tuple(float(sc.p_node[i]) for i in nodes),
                          G=G_out, h=self._h)

    def snapshot(self) -> dict:
        return {"h": round(self._h, 3), "tuned": self._tuned, "at_cap": self._at_cap,
                "h_default": self.params["h_default"], "k": self.params["k_node"]}
