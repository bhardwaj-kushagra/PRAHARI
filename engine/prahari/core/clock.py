"""Simulation clock: one tick per `tick_minutes` from `start` for `days` (SPEC §3.3)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

MINUTES_PER_DAY = 1440


@dataclass(frozen=True)
class Clock:
    """Simulated time: a start date, a run length in days and a tick length in minutes; t counts minutes from the start."""
    start: datetime
    days: float
    tick_minutes: int = 1

    @classmethod
    def from_run(cls, run: dict) -> "Clock":
        """Build the clock from the `run` block of a configuration."""
        return cls(datetime.fromisoformat(run["start"]), float(run["days"]), int(run["tick_minutes"]))

    @property
    def n_ticks(self) -> int:
        """Number of ticks in the run."""
        return int(round(self.days * MINUTES_PER_DAY / self.tick_minutes))

    def minutes(self):
        """Yield t, the minutes since the start, for every tick."""
        for k in range(self.n_ticks):
            yield k * self.tick_minutes

    def wall(self, t: int) -> datetime:
        """Calendar time of minute t (for labels only; the model runs on minutes)."""
        return self.start + timedelta(minutes=t)

    def tod_minutes(self, t: int) -> int:
        """Minutes since local midnight at minute t."""
        w = self.wall(t)
        return w.hour * 60 + w.minute
