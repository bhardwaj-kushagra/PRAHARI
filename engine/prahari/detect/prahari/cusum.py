"""Node CUSUM (SPEC §5.7–5.8). Real M28 (−ln p scores, k = 1.5, replay-tuned h): Phase 5.

Stub: the v1 CUSUM of M23 — Gaussian z recovered from the node p-value, k = 0.5,
fixed h from Siegmund's ARL approximation. Off: single-sample threshold on the node score.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtri

from prahari.core.contracts import Candidates, Scores
from prahari.core.registry import Stage, register


def siegmund_arl(h: float, k: float) -> float:
    """M23 — ARL0 ≈ (e^{−2Δb} + 2Δb − 1) / (2Δ²), Δ = −k, b = h + 1.166."""
    delta, b = -k, h + 1.166
    return (np.exp(-2 * delta * b) + 2 * delta * b - 1) / (2 * delta * delta)


def h_for_arl(arl: float, k: float) -> float:
    """M23 — solve ARL0(h) = arl for h (h ≈ 8.8 for k = 0.5, ARL 43,200)."""
    return float(brentq(lambda h: siegmund_arl(h, k) - arl, 0.0, 200.0))


def cusum_step(G, s, k, h, refractory, ref_min, tick_min):
    """M28 form — G ← max(0, G + S − k); candidate when G > h outside refractory, then G ← 0."""
    G = np.maximum(0.0, G + s - k)
    hit = (G > h) & (refractory <= 0)
    G = np.where(hit, 0.0, G)
    refractory = np.where(hit, ref_min, np.maximum(refractory - tick_min, 0))
    return G, hit, refractory


@register("cusum", kind="stub")
class CusumStub(Stage):
    equation = "M23"
    tag = "ASM"
    description = "v1 CUSUM on z = Φ⁻¹(1 − p) with fixed h from the ARL formula"

    def reset(self, ctx) -> None:
        n = ctx.n_nodes
        self._G = np.zeros(n)
        self._ref = np.zeros(n)
        self._h = h_for_arl(self.params["arl_min"], self.params["k"])

    def step(self, sc: Scores, ctx) -> Candidates:
        z = -ndtri(sc.p_node)                                   # Gaussian z equivalent of the node p-value
        if ctx.t < self.params["warmup_min"]:
            z = np.zeros_like(z)                                # ASM — no evidence while baselines warm up
        G_pre = self._G + z - self.params["k"]
        self._G, hit, self._ref = cusum_step(self._G, z, self.params["k"], self._h, self._ref,
                                             self.params["refractory_min"], ctx.tick_minutes)
        nodes = np.flatnonzero(hit)
        G_out = np.where(hit, np.maximum(G_pre, 0.0), self._G)    # report the crossing value on a hit
        return Candidates(nodes=tuple(int(i) for i in nodes), p=tuple(float(sc.p_node[i]) for i in nodes),
                          G=G_out, h=self._h)

    def snapshot(self) -> dict:
        return {"h": self._h}


@register("cusum", kind="off")
class CusumOff(Stage):
    description = "Single-sample threshold on the node score"

    def reset(self, ctx) -> None:
        self._ref = np.zeros(ctx.n_nodes)

    def step(self, sc: Scores, ctx) -> Candidates:
        h = float(self.params["single_sample_h"])
        hit = (sc.s > h) & (self._ref <= 0)
        self._ref = np.where(hit, self.params["refractory_min"], np.maximum(self._ref - ctx.tick_minutes, 0))
        nodes = np.flatnonzero(hit)
        return Candidates(nodes=tuple(int(i) for i in nodes), p=tuple(float(sc.p_node[i]) for i in nodes),
                          G=sc.s.copy(), h=h)
