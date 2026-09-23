"""Regional haze (M20, Phase 2). Stub and off: none generated."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Additive
from prahari.core.registry import Stage, register


@register("haze", kind="stub")
class HazeStub(Stage):
    equation = "—"
    description = "No haze"

    def step(self, t, ctx) -> Additive:
        return Additive(v=np.zeros(ctx.n_nodes))


@register("haze", kind="off")
class HazeOff(HazeStub):
    pass
