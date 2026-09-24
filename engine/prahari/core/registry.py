"""Stage registry: every module has a `stub`, optionally a `real` and an `off` (SPEC §4.1–4.2, P1–P2).

Callers never import stage classes directly; they ask the registry for the
implementation that the configuration selects (CLAUDE.md rules 1–2).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

KINDS = ("real", "stub", "off")
STATES = ("real", "stub", "off")

# (name, kind) -> class
_REGISTRY: dict[tuple[str, str], type] = {}


class Stage:
    """Base class for all stages. Subclasses set the class attributes and override step()."""

    name: str = ""
    kind: str = "stub"
    version: str = "1.0"
    equation: str = ""          # M-number(s) implemented, for the model card
    tag: str = "ASM"            # provenance tag of the model (SPEC §1.5)
    description: str = ""

    def __init__(self, params: dict, rng: np.random.Generator | None):
        self.params = params
        self._rng = rng

    @property
    def rng(self) -> np.random.Generator:
        """The module's own random generator (rule 7); a stage without one must not draw random numbers."""
        if self._rng is None:
            raise RuntimeError(f"stage '{self.name}' has no RNG stream; add one to core/rng.py STREAMS")
        return self._rng

    def reset(self, ctx: Any) -> None:
        """Clear per-run state. Called once before the first tick."""

    def step(self, inputs: Any, ctx: Any) -> Any:
        raise NotImplementedError

    def snapshot(self) -> dict:
        """Small JSON-safe state for the dashboard and the trace."""
        return {}


def register(name: str, kind: str) -> Callable[[type], type]:
    """Class decorator: register a stage implementation under a module name and kind (real, stub or off)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")

    def deco(cls: type) -> type:
        key = (name, kind)
        if key in _REGISTRY and _REGISTRY[key] is not cls:
            raise ValueError(f"stage {key} registered twice")
        cls.name = name
        cls.kind = kind
        _REGISTRY[key] = cls
        return cls

    return deco


def lookup(name: str, kind: str) -> type | None:
    """The class registered for (name, kind), or None."""
    return _REGISTRY.get((name, kind))


def names() -> list[str]:
    """All registered module names, sorted."""
    return sorted({n for n, _ in _REGISTRY})


def off_allowed(name: str) -> bool:
    """Whether the module may be switched off (it has an `off` implementation)."""
    return (name, "off") in _REGISTRY


@dataclass
class Built:
    """Result of `build`: the requested state, the implementation that will run, and its effective state."""
    requested: str               # state asked for in the configuration
    stage: Stage                 # the implementation that will run
    effective: str               # real, stub or off


def build(name: str, state: str, params: dict, rng: np.random.Generator | None) -> Built:
    """Build the implementation that `state` selects.

    `real` falls back to `stub` while no real implementation exists (DECISIONS P0-4).
    `off` is an error for modules whose `off` is not allowed (SPEC §4.2).
    """
    if state not in STATES:
        raise ValueError(f"modules.{name}: state must be one of {STATES}, got {state!r}")
    if (name, "stub") not in _REGISTRY:
        raise ValueError(f"modules.{name}: no stage registered under this name; known: {names()}")
    if state == "off" and not off_allowed(name):
        raise ValueError(f"modules.{name}: 'off' is not allowed for this module (SPEC §4.2)")
    kind = state if (name, state) in _REGISTRY else "stub"
    cls = _REGISTRY[(name, kind)]
    return Built(requested=state, stage=cls(params, rng), effective=kind)
