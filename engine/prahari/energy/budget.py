"""Energy (SPEC §5.13). Real M41–M43: Phase 8. Stub and off: infinite energy."""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import EnergyState
from prahari.core.registry import Stage, register


@register("energy", kind="stub")
class EnergyStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Infinite energy"

    def step(self, t, ctx) -> EnergyState:
        return EnergyState(soc=np.ones(ctx.n_nodes))


@register("energy", kind="off")
class EnergyOff(EnergyStub):
    pass
