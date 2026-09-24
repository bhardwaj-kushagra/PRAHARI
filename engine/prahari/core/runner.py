"""Failure isolation for every stage call (SPEC P5, §4.5; CLAUDE.md rule 5).

Each module runs inside a Slot. If the running implementation raises or returns
output that breaks its contract, the slot falls back down the chain
real → stub → off → hold last valid output → contract neutral output,
marks the module `degraded`, records the error and carries on. The run never crashes.
"""
from __future__ import annotations

import dataclasses
import time
from typing import Any, Callable

from prahari.core import registry
from prahari.core.contracts import ContractError
from prahari.core.health import ModuleHealth


class Slot:
    """One module in the pipeline with its fallback chain (real → stub → off). Every call goes through `run`, which
    isolates failures: an exception or invalid output switches the slot to the next implementation for the rest
    of the run and marks it degraded (CLAUDE.md rule 5)."""
    def __init__(self, name: str, state: str, params: dict, rng, out_type: type):
        self.name = name
        self.out_type = out_type
        built = registry.build(name, state, params, rng)
        chain = [built.stage]
        for kind in {"real": ("stub", "off"), "stub": ("off",), "off": ()}[built.effective]:
            cls = registry.lookup(name, kind)
            if cls is not None:
                chain.append(cls(params, rng))
        self.chain = chain
        self.pos = 0
        self.last: Any = None
        self.health = ModuleHealth(requested=state, state=built.effective, running=built.effective,
                                   version=built.stage.version)
        self.new_errors: list[str] = []

    @property
    def stage(self):
        """The implementation currently in use."""
        return self.chain[self.pos] if self.pos < len(self.chain) else None

    def reset(self, ctx) -> None:
        for impl in self.chain:
            impl.reset(ctx)

    def _fail(self, exc: Exception, ctx) -> None:
        msg = f"{type(exc).__name__}: {exc}"
        h = self.health
        h.errors += 1
        h.last_error = msg[:300]
        if h.state != "degraded":
            h.degraded_at = ctx.t
        h.state = "degraded"
        self.new_errors.append(msg[:300])
        self.pos += 1
        nxt = self.stage
        h.running = nxt.kind if nxt is not None else ("hold" if self.last is not None else "neutral")

    def run(self, inputs: Any, ctx, check: Callable[[Any], None] | None = None) -> Any:
        """Call the current implementation on `inputs`, validate its output, and fall back on failure."""
        n = ctx.n_nodes
        while self.stage is not None:
            impl = self.stage
            t0 = time.perf_counter()
            try:
                out = impl.step(inputs, ctx)
                if not isinstance(out, self.out_type):
                    raise ContractError(f"expected {self.out_type.__name__}, got {type(out).__name__}")
                out.validate(n)
                if check is not None:
                    check(out)
            except Exception as exc:          # noqa: BLE001 — isolation is the point (P5)
                self._fail(exc, ctx)
                continue
            finally:
                self.health.record_time(time.perf_counter() - t0)
            self.last = out
            return out
        return self.last if self.last is not None else self.out_type.neutral(n)


def expect_len(k: int) -> Callable[[Any], None]:
    """A check that every per-cluster field of an edge output has k entries."""
    def check(out) -> None:
        optional = getattr(type(out), "OPTIONAL", ())        # additive fields an older implementation leaves empty
        for f in dataclasses.fields(out):                     # instance fields only (not ClassVar)
            name, v = f.name, getattr(out, f.name)
            if name in optional and len(v) == 0:
                continue
            if isinstance(v, tuple) and len(v) != k:
                raise ContractError(f"{type(out).__name__}.{name}: expected {k} entries, got {len(v)}")
    return check
