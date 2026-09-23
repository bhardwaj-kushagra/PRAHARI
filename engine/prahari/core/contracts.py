"""Typed data passed between stages (SPEC §4.1, §4.6).

Contracts are additive (CLAUDE.md rule 3): fields may be added with defaults,
never renamed or removed without bumping CONTRACT_VERSION.

Every contract has ``validate(n)`` (raises ContractError on NaN, wrong shape or
out-of-range values) and a ``neutral(n)`` classmethod used by the runner as the
last-resort fallback so that a run never crashes (SPEC P5).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from prahari.core.contract_checks import ContractError, _arr, _num, _same_len  # noqa: F401
from prahari.core.contracts_edge import (  # noqa: F401 — edge contracts are re-exported from here
    BayesFactors, Clusters, Decision, Fisher, Prior, Raq, Scmr)
from prahari.core.contracts_world import Landscape, Layout, Links  # noqa: F401 — world contracts (Phase 1)
from prahari.core.contracts_baselines import BaselineAlarms  # noqa: F401 — baselines (Phase 4)

CONTRACT_VERSION = "prahari.frame/1"


@dataclass(frozen=True)
class Weather:
    T: float                 # °C
    RH: float                # %
    wind_ms: float           # m/s at 10 m
    wind_dir_deg: float      # meteorological "from" direction, clockwise from north
    rain_mm: float = 0.0
    dew_c: float = 0.0       # dew point, °C (Phase 2)

    def validate(self, n: int) -> None:
        _num("T", self.T, -60, 60)
        _num("dew_c", self.dew_c, -80, 60)
        _num("RH", self.RH, 0, 100)
        _num("wind_ms", self.wind_ms, 0, 60)
        _num("wind_dir_deg", self.wind_dir_deg, 0, 360)
        _num("rain_mm", self.rain_mm, 0)

    @classmethod
    def neutral(cls, n: int) -> "Weather":
        return cls(T=30.0, RH=40.0, wind_ms=1.5, wind_dir_deg=270.0)


@dataclass(frozen=True)
class FuelState:
    ffmc: float

    def validate(self, n: int) -> None:
        _num("ffmc", self.ffmc, 0, 101)

    @classmethod
    def neutral(cls, n: int) -> "FuelState":
        return cls(ffmc=85.0)


@dataclass(frozen=True)
class Fire:
    id: int
    x: float
    y: float
    t0: int                  # ignition time, minutes since run start


@dataclass(frozen=True)
class Fires:
    active: tuple = ()       # tuple[Fire, ...]
    new: tuple = ()          # ids ignited this tick
    new_causes: tuple = ()   # "scripted" or "poisson", parallel to `new` (Phase 3a)
    attempts: int = 0        # ignition attempts so far, sustained or not (Phase 3a)

    def validate(self, n: int) -> None:
        for f in self.active:
            _num("fire.x", f.x)
            _num("fire.y", f.y)

    @classmethod
    def neutral(cls, n: int) -> "Fires":
        return cls()


@dataclass(frozen=True)
class Sources:
    """Source terms for active fires (arrays of length M = number of fires)."""
    ids: tuple = ()
    x: np.ndarray = field(default_factory=lambda: np.zeros(0))
    y: np.ndarray = field(default_factory=lambda: np.zeros(0))
    age_min: np.ndarray = field(default_factory=lambda: np.zeros(0))
    q_max: np.ndarray = field(default_factory=lambda: np.zeros(0))
    tau_g: float = 10.0
    q: np.ndarray = field(default_factory=lambda: np.zeros(0))
    area_m2: np.ndarray = field(default_factory=lambda: np.zeros(0))

    def validate(self, n: int) -> None:
        m = (len(self.ids),)
        for k in ("x", "y", "age_min", "q_max", "q", "area_m2"):
            _arr(f"sources.{k}", getattr(self, k), m, lo=None if k in ("x", "y") else 0.0)
        _num("tau_g", self.tau_g, 1e-6)

    @classmethod
    def neutral(cls, n: int) -> "Sources":
        return cls()


@dataclass(frozen=True)
class Concentration:
    c: np.ndarray            # (N,) su at each node

    def validate(self, n: int) -> None:
        _arr("concentration", self.c, (n,), lo=0.0, hi=1e6)

    @classmethod
    def neutral(cls, n: int) -> "Concentration":
        return cls(c=np.zeros(n))


@dataclass(frozen=True)
class Additive:
    """An additive signal component per node (nuisance events, haze)."""
    v: np.ndarray            # (N,) su
    level: float = 0.0       # regional driver, e.g. haze H(t) before node gains (Phase 2)

    def validate(self, n: int) -> None:
        _arr("additive", self.v, (n,), hi=1e6)
        _num("additive.level", self.level, 0.0, 1e6)

    @classmethod
    def neutral(cls, n: int) -> "Additive":
        return cls(v=np.zeros(n))


@dataclass(frozen=True)
class Readings:
    x: np.ndarray            # (N, C) compensated channels, su
    x_raw: np.ndarray        # (N, C) uncompensated channels (fixed-threshold baseline)
    fault: np.ndarray | None = None   # (N,) bool, True where a fault is injected

    def validate(self, n: int) -> None:
        c = self.x.shape[1] if self.x.ndim == 2 else -1
        _arr("readings.x", self.x, (n, c))
        _arr("readings.x_raw", self.x_raw, (n, c))
        if self.fault is not None and self.fault.shape != (n,):
            raise ContractError("readings.fault: wrong shape")

    @classmethod
    def neutral(cls, n: int) -> "Readings":
        return cls(x=np.zeros((n, 1)), x_raw=np.zeros((n, 1)))


@dataclass(frozen=True)
class Residuals:
    r: np.ndarray            # (N, C) detection residual
    z: np.ndarray            # (N, C) residual scaled by the slow-baseline spread
    b: np.ndarray            # (N, C) slow baseline

    def validate(self, n: int) -> None:
        c = self.r.shape[1] if self.r.ndim == 2 else -1
        for k in ("r", "z", "b"):
            _arr(f"residuals.{k}", getattr(self, k), (n, c))

    @classmethod
    def neutral(cls, n: int) -> "Residuals":
        z = np.zeros((n, 1))
        return cls(r=z, z=z, b=z)


@dataclass(frozen=True)
class PValues:
    p: np.ndarray            # (N, C) in (0, 1]
    n_cal: np.ndarray        # (N,) calibration-set size (0 for the Gaussian stub)
    z: np.ndarray | None = None   # (N, C) signed statistic of a Gaussian-form QCC (legacy ablation, P7-12)

    def validate(self, n: int) -> None:
        c = self.p.shape[1] if self.p.ndim == 2 else -1
        _arr("p", self.p, (n, c), lo=1e-300, hi=1.0)
        _arr("n_cal", self.n_cal, (n,), lo=0)

    @classmethod
    def neutral(cls, n: int) -> "PValues":
        return cls(p=np.ones((n, 1)), n_cal=np.zeros(n))


@dataclass(frozen=True)
class Scores:
    s: np.ndarray            # (N,) node score S_t (M27), >= 0
    p_node: np.ndarray       # (N,) node-level p-value
    c: np.ndarray            # (N, C) health weights in [0, 1] (M29)
    z: np.ndarray | None = None   # (N,) signed node statistic passed on from PValues.z (legacy ablation, P7-12)

    def validate(self, n: int) -> None:
        _arr("score", self.s, (n,), lo=0.0)
        _arr("p_node", self.p_node, (n,), lo=1e-300, hi=1.0)
        _arr("health", self.c, (n, self.c.shape[1] if self.c.ndim == 2 else -1), lo=0.0, hi=1.0)

    @classmethod
    def neutral(cls, n: int) -> "Scores":
        return cls(s=np.zeros(n), p_node=np.ones(n), c=np.ones((n, 1)))


@dataclass(frozen=True)
class Candidates:
    nodes: tuple             # node ids raising a candidate this tick
    p: tuple                 # node p-value at the candidate, same order
    G: np.ndarray            # (N,) CUSUM statistic after this tick
    h: float                 # threshold in use

    def validate(self, n: int) -> None:
        _same_len("candidates", self.nodes, self.p)
        _arr("cusum", self.G, (n,), lo=0.0)
        _num("h", self.h, 0.0)
        for i in self.nodes:
            if not 0 <= i < n:
                raise ContractError(f"candidate node {i} out of range")
        for p in self.p:
            _num("candidate p", p, 1e-300, 1.0)

    @classmethod
    def neutral(cls, n: int) -> "Candidates":
        return cls(nodes=(), p=(), G=np.zeros(n), h=0.0)


@dataclass(frozen=True)
class Delivered:
    nodes: tuple             # candidate frames delivered to the edge this tick
    p: tuple
    packets: tuple = ()      # dicts for the dashboard: {"from", "to", "ok", "sf"}

    def validate(self, n: int) -> None:
        _same_len("delivered", self.nodes, self.p)

    @classmethod
    def neutral(cls, n: int) -> "Delivered":
        return cls(nodes=(), p=())


@dataclass(frozen=True)
class EnergyState:
    soc: np.ndarray              # (N,) state of charge in [0, 1]

    def validate(self, n: int) -> None:
        _arr("soc", self.soc, (n,), lo=0.0, hi=1.0)

    @classmethod
    def neutral(cls, n: int) -> "EnergyState":
        return cls(soc=np.ones(n))


@dataclass(frozen=True)
class SatelliteAlerts:
    alert_t: tuple = ()          # tuple of (fire_id, alert time in minutes)

    def validate(self, n: int) -> None:
        for _, t in self.alert_t:
            _num("satellite alert time", t, 0.0)

    @classmethod
    def neutral(cls, n: int) -> "SatelliteAlerts":
        return cls()
