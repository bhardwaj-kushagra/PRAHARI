"""Learning loop (SPEC §5.10). Real M36 fitted likelihood ratio: `learn_real.py` (Phase 9).

Stub and off: the Sellke–Bayarri–Berger bound of M34.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import BayesFactors, Fisher
from prahari.core.registry import Stage, register
from prahari.detect.prahari.qcc import P_FLOOR


def sbb_bound(p):
    """M34 — BF(p) ≤ 1 / (−e p ln p) for p < 1/e; 1 otherwise. p clipped at 1e-300 (SPEC §10)."""
    p = np.clip(np.asarray(p, dtype=float), P_FLOOR, 1.0)
    with np.errstate(divide="ignore"):
        bf = 1.0 / (-np.e * p * np.log(p))
    return np.where(p < 1.0 / np.e, bf, 1.0)


@register("learn", kind="stub")
class LearnStub(Stage):
    equation = "M34 (bound)"
    tag = "LIT"
    description = "Sellke–Bayarri–Berger Bayes-factor bound"

    def step(self, fisher: Fisher, ctx) -> BayesFactors:
        if isinstance(fisher, tuple):                    # Phase 9: the pipeline also passes clusters, SCMR and c (M36)
            fisher = fisher[0]
        return BayesFactors(bf=tuple(float(b) for b in sbb_bound(fisher.p_cluster)))


@register("learn", kind="off")
class LearnOff(LearnStub):
    pass
