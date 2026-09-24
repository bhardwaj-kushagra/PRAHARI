"""Sensor faults — real implementation (SPEC §5.6, M21, Phase 9).

Four faults, each a Poisson process per node (rates per node per 30 days) or scripted by the scenario:
stuck-at (the reading freezes at its last value — or at a scripted value — for a while), offset jump (a permanent step
of ±U(0.5, 1.5) su), spike burst (5–20 samples of ±5 su) and dropout (no data for 10–600 minutes; the node reports
`missing` and its last reading is held, so no NaN enters the pipeline). Faults act on both channels, compensated and
raw. `fault` marks nodes with an injected fault (ground truth, for the record only).
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Readings
from prahari.core.registry import Stage, register

KINDS = ("stuck", "offset", "spike", "dropout")


@register("faults", kind="real")
class FaultsReal(Stage):
    equation = "M21"
    tag = "ASM"
    description = "Stuck-at, offset jump, spike burst and dropout faults (Poisson rates or scripted)"

    def reset(self, ctx) -> None:
        n = ctx.n_nodes
        self._offset = np.zeros(n)
        self._stuck_until = np.full(n, -1)
        self._stuck_val = np.zeros((n, 2))
        self._spike_left = np.zeros(n, dtype=int)
        self._spike_sign = np.ones(n)
        self._drop_until = np.full(n, -1)
        self._last = None
        self._script = sorted(self.params["scripted"], key=lambda f: (f["t_min"], f["node"]))
        self.started: list[tuple[int, int, str]] = []            # (t, node, kind) for the frame's events

    def _start(self, i: int, kind: str, t: int, dur=None, amount=None) -> None:
        p, rng = self.params, self.rng
        if kind == "stuck":
            self._stuck_until[i] = t + int(dur if dur is not None else rng.uniform(*p["stuck_duration_min"]))
            self._stuck_val[i] = self._last[i] if amount is None else amount
        elif kind == "offset":
            self._offset[i] += float(amount) if amount is not None else rng.choice([-1.0, 1.0]) * rng.uniform(*p["offset_su"])
        elif kind == "spike":
            self._spike_left[i] = int(dur) if dur is not None else int(rng.integers(p["spike_samples"][0], p["spike_samples"][1] + 1))
            self._spike_sign[i] = rng.choice([-1.0, 1.0])
        elif kind == "dropout":
            self._drop_until[i] = t + int(dur if dur is not None else rng.uniform(*p["dropout_min"]))
        self.started.append((t, i, kind))

    def step(self, readings: Readings, ctx) -> Readings:
        p, t, n = self.params, ctx.t, ctx.n_nodes
        x = np.stack([readings.x[:, 0], readings.x_raw[:, 0]], axis=1)
        if self._last is None:
            self._last = x.copy()
        self.started = []
        while self._script and self._script[0]["t_min"] <= t:     # scripted faults (scenario)
            f = self._script.pop(0)
            self._start(int(f["node"]), f["kind"], t, f.get("duration_min"), f.get("value_su"))
        rates = np.array([p["rate_per_node_30d"][k] for k in KINDS]) / (30.0 * 1440.0) * ctx.tick_minutes
        hits = self.rng.random((n, len(KINDS))) < rates                            # M21 — Poisson faults
        for i, k in zip(*np.nonzero(hits)):
            self._start(int(i), KINDS[k], t)
        x = x + self._offset[:, None]                                              # offset jump (permanent)
        spike = self._spike_left > 0
        x = x + (spike * self._spike_sign * float(p["spike_su"]))[:, None]         # spike burst
        self._spike_left = np.maximum(self._spike_left - 1, 0)
        stuck = self._stuck_until > t
        x = np.where(stuck[:, None], self._stuck_val, x)                           # stuck-at
        missing = self._drop_until > t
        x = np.where(missing[:, None], self._last, x)                              # dropout: hold, flag missing
        self._last = x.copy()
        fault = stuck | missing | spike | (self._offset != 0)
        return Readings(x=x[:, :1], x_raw=x[:, 1:], fault=fault, missing=missing)

    def snapshot(self) -> dict:
        return {"rates_per_node_30d": dict(self.params["rate_per_node_30d"]), "scripted": len(self.params["scripted"])}
