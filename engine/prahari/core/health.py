"""Module health: state, error count, last error and mean step time (SPEC §4.8)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModuleHealth:
    """Health record of one module: requested and running implementation, errors, when it degraded, step timing."""
    requested: str               # state asked for in the configuration
    state: str                   # real, stub, off or degraded
    running: str                 # implementation currently running: real, stub, off, hold, neutral
    version: str = ""
    errors: int = 0
    last_error: str = ""
    degraded_at: int | None = None
    _time_s: float = 0.0
    _calls: int = 0

    def record_time(self, seconds: float) -> None:
        """Add one step's wall time to the module's timing."""
        self._time_s += seconds
        self._calls += 1

    @property
    def mean_step_ms(self) -> float:
        """Mean wall time per step in milliseconds."""
        return 1000.0 * self._time_s / self._calls if self._calls else 0.0

    def status(self) -> str:
        """Short state for frames: ok (real), stub, off or degraded."""
        return {"real": "ok"}.get(self.state, self.state)

    def public(self, with_timing: bool = False) -> dict:
        """The record as written to recordings and health files (timing only when asked)."""
        d = {"requested": self.requested, "state": self.state, "running": self.running,
             "version": self.version, "errors": self.errors, "last_error": self.last_error,
             "degraded_at": self.degraded_at}
        if with_timing:
            d["mean_step_ms"] = round(self.mean_step_ms, 4)
        return d
