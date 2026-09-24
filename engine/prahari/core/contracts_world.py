"""World contracts (SPEC §5.1, §5.12): landscape raster, node layout and radio links.

Produced once per run by the setup modules `landscape`, `siting` and `links`.
Re-exported by `prahari.core.contracts`; import them from there. Same additive rules apply.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from prahari.core.contract_checks import ContractError, _arr, _num

LAYOUTS = ("grid", "corridor", "greedy")
SPREADING_FACTORS = (7, 8, 9, 10, 11, 12)


@dataclass(frozen=True)
class Landscape:
    """Static raster over the map. Row i, column j is the cell centred at (x0 + j·cell, y0 + i·cell)."""
    cell_m: float
    x0: float
    y0: float
    lam: np.ndarray                          # (ny, nx) ignition intensity λ(x) (M3), 0 outside the forest
    forest: np.ndarray                       # (ny, nx) bool, False where nodes and ignitions are excluded
    width_m: float
    height_m: float
    dist: dict = field(default_factory=dict)  # class -> (ny, nx) distance field D_k (M2), present classes only
    modelled: bool = True                    # False for the uniform stub

    def validate(self, n: int) -> None:
        _num("cell_m", self.cell_m, 1e-3)
        if self.lam.ndim != 2:
            raise ContractError("landscape.lam must be 2-D")
        _arr("landscape.lam", self.lam, self.lam.shape, lo=0.0)
        if self.forest.shape != self.lam.shape or self.forest.dtype != bool:
            raise ContractError("landscape.forest must be a bool array shaped like lam")
        if not self.forest.any() or float((self.lam * self.forest).sum()) <= 0.0:
            raise ContractError("landscape has no forest cells with positive intensity")
        for k, d in self.dist.items():
            _arr(f"landscape.dist[{k}]", d, self.lam.shape, lo=0.0)

    @classmethod
    def neutral(cls, n: int) -> "Landscape":
        return cls(cell_m=10.0, x0=5.0, y0=5.0, lam=np.ones((1, 1)), forest=np.ones((1, 1), dtype=bool),
                   width_m=10.0, height_m=10.0, modelled=False)

    def centres(self) -> np.ndarray:
        """(ny·nx, 2) cell-centre coordinates in row-major order."""
        ny, nx = self.lam.shape
        xs = self.x0 + self.cell_m * np.arange(nx)
        ys = self.y0 + self.cell_m * np.arange(ny)
        gx, gy = np.meshgrid(xs, ys)
        return np.column_stack([gx.ravel(), gy.ravel()])


@dataclass(frozen=True)
class Layout:
    name: str                                # the layout the run simulates
    xy: np.ndarray                           # (N, 2) node positions, m
    covered: float = -1.0                    # M4 objective as a fraction of total λ; −1 when not computed
    alternatives: dict = field(default_factory=dict)   # name -> {"xy": (N, 2), "covered": float}
    corridor_spacing_m: float = 0.0          # effective corridor spacing (DER), 0 when not built

    def validate(self, n: int) -> None:
        if self.name not in LAYOUTS:
            raise ContractError(f"unknown layout {self.name!r}")
        _arr("layout.xy", self.xy, (n, 2))
        if not (self.covered == -1.0 or 0.0 <= self.covered <= 1.0):
            raise ContractError(f"layout.covered {self.covered} outside [0, 1]")
        for k, alt in self.alternatives.items():
            if k not in LAYOUTS:
                raise ContractError(f"unknown alternative layout {k!r}")
            _arr(f"layout.alternatives[{k}].xy", alt["xy"], (n, 2))
            _num(f"layout.alternatives[{k}].covered", alt["covered"], -1.0, 1.0)

    @classmethod
    def neutral(cls, n: int) -> "Layout":
        side = int(np.ceil(np.sqrt(max(n, 1))))
        k = np.arange(n)
        return cls(name="grid", xy=np.column_stack([(k // side) * 70.0, (k % side) * 70.0]).astype(float))


@dataclass(frozen=True)
class Links:
    """Best uplink for every node (M38). `gateway` is −1 and `sf` is 0 where no link closes."""
    gateway: np.ndarray                      # (N,) int gateway index
    d_m: np.ndarray                          # (N,) distance to that gateway
    pl_db: np.ndarray                        # (N,) path loss
    prx_dbm: np.ndarray                      # (N,) received power
    sf: np.ndarray                           # (N,) int spreading factor, 0 = no link
    modelled: bool = True                    # False for the perfect-link stub
    prx_all: np.ndarray | None = None        # (N, G) received power at every gateway (Phase 8, re-routing)
    sf_all: np.ndarray | None = None         # (N, G) lowest closing SF per gateway, 0 = none (Phase 8)
    relay: np.ndarray | None = None          # (N,) TS011 relay node for nodes with no direct link, −1 = none
    relay_sf: np.ndarray | None = None       # (N,) SF of the hop to that relay, 0 = none
    relay_prx: np.ndarray | None = None      # (N,) received power at that relay (dBm)

    def validate(self, n: int) -> None:
        for k in ("gateway", "d_m", "pl_db", "prx_dbm", "sf"):
            _arr(f"links.{k}", getattr(self, k), (n,))
        if not np.isin(self.sf, (0,) + SPREADING_FACTORS).all():
            raise ContractError("links.sf must be 0 or 7..12")
        if ((self.sf == 0) != (self.gateway < 0)).any():
            raise ContractError("links: sf 0 must coincide with gateway −1")
        _arr("links.d_m", self.d_m, (n,), lo=0.0)

    @classmethod
    def neutral(cls, n: int) -> "Links":
        z = np.zeros(n)
        return cls(gateway=np.full(n, -1), d_m=z, pl_db=z, prx_dbm=z, sf=np.zeros(n, dtype=int), modelled=False)
