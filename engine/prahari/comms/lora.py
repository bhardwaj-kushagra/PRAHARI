"""LoRa link-layer maths (SPEC §5.12, Phase 8): time on air (M39), ALOHA collisions with capture (M40), node-to-node
links and TS011 relay choice (M38). Pure functions — arrays in, arrays out."""
from __future__ import annotations

import math

import numpy as np

from prahari.comms.pathloss import path_loss, rx_power, select_sf


def time_on_air(payload_b: int, sf: int, bw_hz: float = 125e3, cr: int = 1, crc: int = 1, ih: int = 0,
                de: int | None = None, n_preamble: int = 8) -> float:
    """M39 — Semtech time on air in seconds; low-data-rate optimisation DE on for SF11–12 unless given."""
    de = (1 if sf >= 11 else 0) if de is None else de
    t_sym = 2.0 ** sf / bw_hz
    n_pay = 8 + max(math.ceil((8 * payload_b - 4 * sf + 28 + 16 * crc - 20 * ih) / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (n_preamble + 4.25) * t_sym + n_pay * t_sym


def collide(start_s, toa_s, channel, sf, prx_dbm, capture_db: float) -> np.ndarray:
    """M40 — True where a frame is lost: it overlaps in time another frame on the same channel and SF and is not at
    least `capture_db` stronger than every such frame (capture effect). Frames are 1-D arrays of equal length."""
    s = np.asarray(start_s, dtype=float)
    e = s + np.asarray(toa_s, dtype=float)
    n = s.size
    if n < 2:
        return np.zeros(n, dtype=bool)
    same = (np.asarray(channel)[:, None] == np.asarray(channel)[None, :]) & \
           (np.asarray(sf)[:, None] == np.asarray(sf)[None, :])
    overlap = same & (s[:, None] < e[None, :]) & (s[None, :] < e[:, None])
    np.fill_diagonal(overlap, False)
    p = np.asarray(prx_dbm, dtype=float)
    weaker = p[:, None] < p[None, :] + capture_db                 # frame i does not capture over frame j
    return (overlap & weaker).any(axis=1)


def node_links(xy, p: dict, shadow_db=None):
    """M38 between nodes (same forest law, ASM): received power (N, N) and the lowest closing SF (0 = none)."""
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    pl = path_loss(d, p["pl_ref_db"], p["d_ref_m"], p["pl_exponent"])
    if shadow_db is not None:
        pl = pl + shadow_db
    prx = rx_power(pl, p["ptx_dbm"], p["gain_tx_dbi"], p["gain_rx_dbi"])
    np.fill_diagonal(prx, -np.inf)
    return prx, select_sf(prx, {int(k): v for k, v in p["sensitivity_dbm"].items()}, p["margin_db"])


def pick_relays(direct_sf, prx_nn, sf_nn) -> np.ndarray:
    """TS011 — for each node without a direct gateway link, the strongest neighbour that has one and whose
    node-to-node link closes; −1 where no relay exists (and for nodes with a direct link)."""
    ok = (sf_nn > 0) & (np.asarray(direct_sf)[None, :] > 0)
    cand = np.where(ok, prx_nn, -np.inf)
    best = cand.argmax(axis=1)
    has = np.isfinite(cand[np.arange(len(best)), best])
    return np.where((np.asarray(direct_sf) == 0) & has, best, -1)
