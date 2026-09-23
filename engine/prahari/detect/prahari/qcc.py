"""Quantile-calibrated conformal p-values, QCC (SPEC §5.8). Real M26: Phase 5.

Stub and off: Gaussian upper-tail p-value from the TTC z-score.
"""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr

from prahari.core.contracts import PValues, Residuals
from prahari.core.registry import Stage, register

P_FLOOR = 1e-300    # SPEC §10 — clip p to avoid overflow in p ln p


def gaussian_p(z):
    """Stub p-value: p = 1 − Φ(z), clipped to [1e-300, 1]."""
    return np.clip(ndtr(-np.asarray(z, dtype=float)), P_FLOOR, 1.0)


def conformal_p(sorted_scores, score):
    """M26 — p = (1 + |{j : α_j ≥ α_t}|) / (n + 1), counted with a binary search."""
    n = sorted_scores.shape[0]
    return (1.0 + n - np.searchsorted(sorted_scores, score, side="left")) / (n + 1.0)


@register("qcc", kind="stub")
class QCCStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Gaussian p-value from the z-score"

    def step(self, res: Residuals, ctx) -> PValues:
        return PValues(p=gaussian_p(res.z), n_cal=np.zeros(ctx.n_nodes))


@register("qcc", kind="off")
class QCCOff(QCCStub):
    description = "Gaussian p-value (off)"
