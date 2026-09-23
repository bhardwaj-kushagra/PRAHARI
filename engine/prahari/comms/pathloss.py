"""Radio links (SPEC §5.12): log-distance path loss and spreading-factor selection (M38, no shadowing yet).

Real: each node's best gateway and the lowest spreading factor that closes the link.
Stub and off: every node reaches its nearest gateway at SF7 (the comms stub's perfect link).
Shadowing (X_σ), TS011 relays and collisions arrive with the comms phase (Phase 8).
"""
from __future__ import annotations

import numpy as np

from prahari.core.contracts import Links
from prahari.core.registry import Stage, register


def path_loss(d_m, pl_ref_db: float, d_ref_m: float, exponent: float):
    """M38 — PL(d) = PL_ref + 10 n log10(d / d_ref), without the shadowing term X_σ."""
    d = np.maximum(np.asarray(d_m, dtype=float), 1.0)          # 1 m floor avoids log(0) at a gateway
    return pl_ref_db + 10.0 * exponent * np.log10(d / d_ref_m)


def exponent_from_two_points(pl1_db: float, d1_m: float, pl2_db: float, d2_m: float) -> float:
    """M38 (DER) — n = (PL2 − PL1) / (10 log10(d2 / d1)); 100 dB at 200 m and 120 dB at 400 m give 6.64."""
    return (pl2_db - pl1_db) / (10.0 * np.log10(d2_m / d1_m))


def rx_power(pl_db, ptx_dbm: float, gtx_dbi: float, grx_dbi: float):
    """M38 — P_rx = P_tx + G_tx + G_rx − PL(d)."""
    return ptx_dbm + gtx_dbi + grx_dbi - np.asarray(pl_db, dtype=float)


def select_sf(prx_dbm, sensitivity: dict, margin_db: float) -> np.ndarray:
    """M38 — lowest SF whose sensitivity plus margin the received power meets; 0 when none closes."""
    prx = np.asarray(prx_dbm, dtype=float)
    sf = np.zeros(prx.shape, dtype=int)
    for s in sorted(sensitivity, reverse=True):                   # lower SFs overwrite higher ones
        sf = np.where(prx >= float(sensitivity[s]) + margin_db, int(s), sf)
    return sf


def max_range(sf: int, p: dict) -> float:
    """Largest distance at which `sf` closes (DER, inverse of M38)."""
    budget = p["ptx_dbm"] + p["gain_tx_dbi"] + p["gain_rx_dbi"] - (p["sensitivity_dbm"][sf] + p["margin_db"])
    return float(p["d_ref_m"] * 10 ** ((budget - p["pl_ref_db"]) / (10.0 * p["pl_exponent"])))


def distances(xy, gw_xy) -> np.ndarray:
    """(N, G) node-to-gateway distances."""
    d = xy[:, None, :] - gw_xy[None, :, :]
    return np.hypot(d[..., 0], d[..., 1])


def gateway_xy(gateways: list) -> np.ndarray:
    return np.array([[g["x"], g["y"]] for g in gateways], dtype=float).reshape(-1, 2)


@register("links", kind="real")
class LinksReal(Stage):
    equation = "M38 (no shadowing)"
    tag = "LIT"
    description = "Forest log-distance path loss; best gateway and lowest closing SF per node"

    def step(self, inputs, ctx) -> Links:
        xy, gateways = inputs
        p = self.params
        n = xy.shape[0]
        if not gateways:
            z = np.zeros(n)
            return Links(gateway=np.full(n, -1), d_m=z, pl_db=z, prx_dbm=z, sf=np.zeros(n, dtype=int))
        d = distances(xy, gateway_xy(gateways))
        pl = path_loss(d, p["pl_ref_db"], p["d_ref_m"], p["pl_exponent"])
        prx = rx_power(pl, p["ptx_dbm"], p["gain_tx_dbi"], p["gain_rx_dbi"])
        best = prx.argmax(axis=1)                                   # best gateway = strongest signal
        rows = np.arange(n)
        sf = select_sf(prx[rows, best], p["sensitivity_dbm"], p["margin_db"])
        return Links(gateway=np.where(sf > 0, best, -1), d_m=d[rows, best], pl_db=pl[rows, best],
                     prx_dbm=prx[rows, best], sf=sf)


@register("links", kind="stub")
class LinksStub(Stage):
    equation = "—"
    tag = "ASM"
    description = "Perfect link to the nearest gateway at SF7"

    def step(self, inputs, ctx) -> Links:
        xy, gateways = inputs
        n = xy.shape[0]
        z = np.zeros(n)
        if not gateways:
            return Links(gateway=np.full(n, -1), d_m=z, pl_db=z, prx_dbm=z, sf=np.zeros(n, dtype=int), modelled=False)
        d = distances(xy, gateway_xy(gateways))
        best = d.argmin(axis=1)
        return Links(gateway=best, d_m=d[np.arange(n), best], pl_db=z, prx_dbm=z,
                     sf=np.full(n, 7, dtype=int), modelled=False)


@register("links", kind="off")
class LinksOff(LinksStub):
    description = "Perfect link to the nearest gateway at SF7 (off)"
