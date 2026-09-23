"""Ignition stage (SPEC §5.3). Stub: scripted ignitions from the scenario. Off: no fires. Real M8: Phase 3a."""
from __future__ import annotations

from prahari.core.contracts import Fire, Fires
from prahari.core.registry import Stage, register


@register("ignition", kind="stub")
class IgnitionStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Fires at scripted times and places from the scenario file"

    def reset(self, ctx) -> None:
        script = sorted(self.params.get("scripted", []), key=lambda s: (s["t_min"], s["x"], s["y"]))
        self._pending = [Fire(id=k, x=float(s["x"]), y=float(s["y"]), t0=int(s["t_min"])) for k, s in enumerate(script)]
        self._active: list[Fire] = []

    def step(self, inputs, ctx) -> Fires:
        t = inputs[0]
        new = [f for f in self._pending if f.t0 <= t]
        self._pending = [f for f in self._pending if f.t0 > t]
        self._active += new
        life = float(self.params["fire_lifetime_min"])
        self._active = [f for f in self._active if t - f.t0 < life]
        return Fires(active=tuple(self._active), new=tuple(f.id for f in new))

    def snapshot(self) -> dict:
        return {"pending": len(self._pending), "active": len(self._active)}


@register("ignition", kind="off")
class IgnitionOff(Stage):
    description = "No fires"

    def step(self, inputs, ctx) -> Fires:
        return Fires()
