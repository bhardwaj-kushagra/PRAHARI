"""Node score (SPEC §5.8). Stub and off: M27 with health weights c = 1 (M29 stub)."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import PValues, Scores
from prahari.core.registry import Stage, register
from prahari.detect.prahari.qcc import P_FLOOR


def node_score(p, c):
    """M27 — S_t = Σ_i c_i (−ln p_i,t) over channels. p and c are (N, C); returns (N,)."""
    return (c * -np.log(np.clip(p, P_FLOOR, 1.0))).sum(axis=1)


@register("score", kind="stub")
class ScoreStub(Stage):
    equation = "M27 (c = 1)"
    tag = "ASM"
    description = "Sum of −ln p over channels, health weight 1"

    def step(self, pv: PValues, ctx) -> Scores:
        c = np.ones_like(pv.p)
        s = node_score(pv.p, c)
        z = None if pv.z is None else pv.z[:, 0]                 # passed on for a z-statistic CUSUM (P7-12)
        return Scores(s=s, p_node=np.clip(np.exp(-s), P_FLOOR, 1.0), c=c, z=z)


@register("score", kind="off")
class ScoreOff(ScoreStub):
    pass
