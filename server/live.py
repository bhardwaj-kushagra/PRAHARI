"""Live runs for the engine server (SPEC §3.1, Phase 6). A thin adapter: the engine never imports the server.

`Simulation.run` writes through a writer object; `LiveWriter` implements the same interface, but instead of a file it
appends each line (header, frame, trace, footer — the recording's own line format) to an in-memory list that WebSocket
clients read, paces frames to a chosen speed, and applies requested module switches between recorded frames.
"""
from __future__ import annotations

import threading
import time

from prahari.core.pipeline import Simulation


class _Stopped(Exception):
    pass


class LiveWriter:
    """Writer for live mode: same methods as the file writer, but lines are kept for WebSocket clients."""
    def __init__(self, run: "LiveRun"):
        self.run = run
        self.n_frames = 0
        self.n_traces = 0

    def header(self, header: dict) -> None:
        self.run.push({"header": {**header, "live": True}})

    def frame(self, frame: dict) -> None:
        self.run.before_frame(frame)
        self.run.push(frame)
        self.n_frames += 1

    def trace(self, record: dict) -> None:
        self.run.push({"trace": record})
        self.n_traces += 1

    def close(self, footer: dict) -> None:
        self.run.push({"footer": footer})


class LiveRun:
    """One simulation running in a background thread. `speed` follows the dashboard: ×60 = one simulated minute per
    second; 0 runs as fast as possible."""

    def __init__(self, cfg: dict, speed: float):
        self.sim = Simulation(cfg)
        self.speed = float(speed)
        self.messages: list[dict] = []
        self.lock = threading.Lock()
        self.pending: list[tuple[str, str]] = []
        self.stop_flag = threading.Event()
        self.done = False
        self.error: str | None = None
        self.t: int | None = None
        self._t_first: int | None = None
        self._wall0 = 0.0
        self.thread = threading.Thread(target=self._main, daemon=True)

    def start(self) -> "LiveRun":
        """Start the run in a background thread; returns self."""
        self.thread.start()
        return self

    def stop(self) -> None:
        """Ask the run to stop at the next tick."""
        self.stop_flag.set()

    def switch(self, module: str, state: str) -> None:
        """Queue a module switch, applied before the next recorded frame."""
        with self.lock:
            self.pending.append((module, state))

    def push(self, msg: dict) -> None:
        with self.lock:
            self.messages.append(msg)

    def since(self, i: int) -> list[dict]:
        """Recording lines from index i on (for a WebSocket client catching up)."""
        with self.lock:
            return self.messages[i:]

    def before_frame(self, frame: dict) -> None:
        if self.stop_flag.is_set():
            raise _Stopped
        with self.lock:
            todo, self.pending = self.pending, []
        for module, state in todo:                         # between ticks: the next tick runs the new state
            self.sim.switch_module(module, state)
            frame["events"].append({"type": "module_switch", "module": module, "state": state})
        t = frame["t"]
        self.t = t
        if self._t_first is None:
            self._t_first, self._wall0 = t, time.monotonic()
        if self.speed > 0:
            due = self._wall0 + (t - self._t_first) / (self.speed / 60.0)
            while (wait := due - time.monotonic()) > 0:
                if self.stop_flag.wait(min(wait, 0.2)):
                    raise _Stopped

    def _main(self) -> None:
        try:
            self.sim.run(LiveWriter(self))
        except _Stopped:
            self.push({"footer": {"stopped": True}})
        except Exception as exc:                            # noqa: BLE001 — reported to clients, never crashes the server
            self.error = f"{type(exc).__name__}: {exc}"
            self.push({"footer": {"error": self.error}})
        finally:
            self.done = True

    def health(self) -> dict:
        """Health of every module of the running simulation."""
        return {k: v.health.public() for k, v in self.sim.slots.items()}
