"""Nuisance events (SPEC §5.6, M20). Real: roadside and interior Poisson events. Stub and off: none."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Additive
from prahari.core.registry import Stage, register


def event_signal(age, amp, tau, duration: float):
    """M20 — a · exp(−(t − t0)/τ) for 0 ≤ t − t0 < duration, else 0."""
    age = np.asarray(age, dtype=float)
    return np.where((age >= 0) & (age < duration), amp * np.exp(-age / tau), 0.0)


@register("nuisance", kind="real")
class NuisanceReal(Stage):
    equation = "M20 (nuisance)"
    tag = "ASM"
    description = "Short exponential spikes: roadside nodes 1/day, others 1 per 5 days"

    def reset(self, ctx) -> None:
        p, n = self.params, ctx.n_nodes
        self.roadside = self.rng.random(n) < p["roadside_frac"]
        self._rate = np.where(self.roadside, p["rate_roadside_per_day"], p["rate_other_per_day"]) / 1440.0
        self._node = np.zeros(0, dtype=int)
        self._t0 = np.zeros(0)
        self._amp = np.zeros(0)
        self._tau = np.zeros(0)
        self.counts = np.zeros(n, dtype=int)

    def step(self, t, ctx) -> Additive:
        p, rng, n = self.params, self.rng, ctx.n_nodes
        start = rng.random(n) < 1.0 - np.exp(-self._rate * ctx.tick_minutes)        # Poisson starts per tick
        k = int(start.sum())
        if k:
            nodes = np.flatnonzero(start)
            amp = np.exp(rng.normal(np.log(p["amp_median"]), p["amp_sigma_log"], k))  # M20 — a ~ LN(ln 1.5, 0.6)
            tau = rng.uniform(p["tau_range"][0], p["tau_range"][1], k)                # M20 — τ ~ U(2, 10)
            self._node = np.concatenate([self._node, nodes])
            self._t0 = np.concatenate([self._t0, np.full(k, float(t))])
            self._amp = np.concatenate([self._amp, amp])
            self._tau = np.concatenate([self._tau, tau])
            self.counts[nodes] += 1
        live = t - self._t0 < p["duration_min"]
        self._node, self._t0, self._amp, self._tau = (a[live] for a in (self._node, self._t0, self._amp, self._tau))
        contrib = event_signal(t - self._t0, self._amp, self._tau, p["duration_min"])
        return Additive(v=np.bincount(self._node, weights=contrib, minlength=n).astype(float))

    def snapshot(self) -> dict:
        return {"active_events": int(self._node.size), "events_total": int(self.counts.sum())}


@register("nuisance", kind="stub")
class NuisanceStub(Stage):
    equation = "—"
    description = "No nuisance events"

    def step(self, t, ctx) -> Additive:
        return Additive(v=np.zeros(ctx.n_nodes))


@register("nuisance", kind="off")
class NuisanceOff(NuisanceStub):
    pass
