"""Nuisance events (M20, Phase 2). Stub and off: none generated."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Additive
from prahari.core.registry import Stage, register


@register("nuisance", kind="stub")
class NuisanceStub(Stage):
    equation = "—"
    description = "No nuisance events"

    def step(self, t, ctx) -> Additive:
        return Additive(v=np.zeros(ctx.n_nodes))


@register("nuisance", kind="off")
class NuisanceOff(NuisanceStub):
    pass
