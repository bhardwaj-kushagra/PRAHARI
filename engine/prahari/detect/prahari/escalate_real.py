"""Graded escalation, real implementation (SPEC §5.9, M35). The stub (CONFIRMED when the quorum is met) is in
`escalate.py`.

Clusters are tracked as incidents: a cluster joins the incident holding any node within R of its members, or starts a
new one. Per incident the level only rises until the incident clears:

- WATCH      a cluster that fails SCMR;
- CANDIDATE  any node candidate;
- CONFIRMED  the M34 rule is met;
- ESCALATED  a confirmed incident with another confirmed incident within `escalate_km`, or one that grew by
             `growth_nodes` or more nodes within `growth_min`;
- cleared    no candidates in the incident for `clear_min` minutes.

A new alert is raised when an incident first reaches CONFIRMED or ESCALATED. (The SPEC's prior-only WATCH has no
cluster to attach to; the header strip shows the day type and quorum instead.)
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Decision
from prahari.core.registry import Stage, register

LEVELS = ("WATCH", "CANDIDATE", "CONFIRMED", "ESCALATED")
RANK = {lv: k for k, lv in enumerate(LEVELS)}


class Incident:
    def __init__(self, iid: int, t: int):
        self.id, self.t_last, self.level = iid, t, "WATCH"
        self.nodes: set = set()
        self.sizes: list[tuple[int, int]] = []               # (t, size) after each update

    def grew_by(self, t: int, window: int) -> int:
        """Nodes gained since the start of the window (or since the incident's first cluster, if younger)."""
        before = [s for ts, s in self.sizes if ts <= t - window]
        base = before[-1] if before else self.sizes[0][1]
        return len(self.nodes) - base


@register("escalate", kind="real")
class EscalateReal(Stage):
    equation = "M35"
    tag = "ASM"
    description = "Incident ladder WATCH → CANDIDATE → CONFIRMED → ESCALATED; cleared after 120 min"

    def reset(self, ctx) -> None:
        self._inc: list[Incident] = []
        self._next = 0
        self._last_conf = np.full(ctx.n_nodes, -np.inf)

    def _find(self, members, nbr) -> Incident | None:
        m = list(members)
        for inc in self._inc:
            if nbr[np.ix_(m, sorted(inc.nodes))].any():
                return inc
        return None

    def step(self, inputs, ctx) -> Decision:
        clusters, scmr, raq = inputs
        p, t, nbr = self.params, ctx.t, ctx.neighbours
        self._inc = [inc for inc in self._inc if inc.t_last > t - int(p["clear_min"])]      # M35 — cleared
        levels, new, ids = [], [], []
        for members, ok, dec in zip(clusters.members, scmr.passed, raq.decide):
            inc = self._find(members, nbr)
            if inc is None:
                inc = Incident(self._next, t)
                self._next += 1
                self._inc.append(inc)
            before = inc.level if inc.sizes else None                # None: a new incident
            inc.nodes.update(int(i) for i in members)
            inc.t_last = t
            inc.sizes.append((t, len(inc.nodes)))
            step_level = "CONFIRMED" if dec else ("CANDIDATE" if ok else "WATCH")
            inc.level = step_level if before is None else max(before, step_level, key=RANK.get)
            if RANK[inc.level] >= RANK["CONFIRMED"]:
                self._last_conf[list(members)] = t
                if self._escalates(inc, ctx):
                    inc.level = "ESCALATED"
            raised = inc.level in ("CONFIRMED", "ESCALATED") and (before is None or RANK[inc.level] > RANK[before])
            levels.append(inc.level)
            new.append(bool(raised))
            ids.append(inc.id)
        return Decision(levels=tuple(levels), new_alert=tuple(new), incident=tuple(ids))

    def _escalates(self, inc: Incident, ctx) -> bool:
        p = self.params
        if inc.grew_by(ctx.t, int(p["growth_min"])) >= int(p["growth_nodes"]):
            return True
        mine = ctx.xy[sorted(inc.nodes)]
        for other in self._inc:
            if other is inc or RANK[other.level] < RANK["CONFIRMED"]:
                continue
            d = np.hypot(*(mine[:, None, :] - ctx.xy[sorted(other.nodes)][None, :, :]).transpose(2, 0, 1))
            if d.min() <= 1000.0 * float(p["escalate_km"]):
                return True
        return False

    def confirmed_since(self, t_from: float) -> np.ndarray:
        return self._last_conf > t_from

    def snapshot(self) -> dict:
        return {"active_incidents": len(getattr(self, "_inc", []))}
