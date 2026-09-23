"""Graded escalation (SPEC §5.9). Real M35 state machine: Phase 6.

Stub and off: CONFIRMED when the quorum is met, otherwise CANDIDATE (or WATCH when SCMR fails).
A new alert is raised only if no member was confirmed within the clear-down time.
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Decision
from prahari.core.registry import Stage, register


@register("escalate", kind="stub")
class EscalateStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "CONFIRMED when the quorum is met"

    def reset(self, ctx) -> None:
        self._last_conf = np.full(ctx.n_nodes, -np.inf)

    def step(self, inputs, ctx) -> Decision:
        clusters, scmr, raq = inputs
        levels, new = [], []
        for members, ok, dec in zip(clusters.members, scmr.passed, raq.decide):
            m = np.asarray(members, dtype=int)
            if dec:
                fresh = bool(np.all(self._last_conf[m] <= ctx.t - self.params["clear_min"]))
                self._last_conf[m] = ctx.t
                levels.append("CONFIRMED")
                new.append(fresh)
            else:
                levels.append("CANDIDATE" if ok else "WATCH")
                new.append(False)
        return Decision(levels=tuple(levels), new_alert=tuple(new))

    def confirmed_since(self, t_from: float) -> np.ndarray:
        return self._last_conf > t_from


@register("escalate", kind="off")
class EscalateOff(EscalateStub):
    pass
