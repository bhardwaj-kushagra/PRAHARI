"""Communications (SPEC §5.12). Real M38–M40: Phase 8. Stub and off: perfect link, zero latency."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Candidates, Delivered
from prahari.core.registry import Stage, register


@register("comms", kind="stub")
class CommsStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Perfect link, zero latency"

    def reset(self, ctx) -> None:
        self._gw = []
        if ctx.gateways:
            g = np.array([[gw["x"], gw["y"]] for gw in ctx.gateways], dtype=float)
            d = np.hypot(ctx.xy[:, None, 0] - g[None, :, 0], ctx.xy[:, None, 1] - g[None, :, 1])
            self._gw = [ctx.gateways[j]["id"] for j in d.argmin(axis=1)]

    def step(self, cand: Candidates, ctx) -> Delivered:
        packets = tuple({"from": int(i), "to": self._gw[i] if self._gw else None, "ok": True, "sf": None}
                        for i in cand.nodes)
        return Delivered(nodes=cand.nodes, p=cand.p, packets=packets)


@register("comms", kind="off")
class CommsOff(CommsStub):
    pass
