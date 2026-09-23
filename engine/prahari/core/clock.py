"""Simulation clock: one tick per `tick_minutes` from `start` for `days` (SPEC §3.3)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

MINUTES_PER_DAY = 1440


@dataclass(frozen=True)
class Clock:
    start: datetime
    days: float
    tick_minutes: int = 1

    @classmethod
    def from_run(cls, run: dict) -> "Clock":
        return cls(datetime.fromisoformat(run["start"]), float(run["days"]), int(run["tick_minutes"]))

    @property
    def n_ticks(self) -> int:
        return int(round(self.days * MINUTES_PER_DAY / self.tick_minutes))

    def minutes(self):
        """Yield t, the minutes since the start, for every tick."""
        for k in range(self.n_ticks):
            yield k * self.tick_minutes

    def wall(self, t: int) -> datetime:
        return self.start + timedelta(minutes=t)

    def tod_minutes(self, t: int) -> int:
        w = self.wall(t)
        return w.hour * 60 + w.minute
