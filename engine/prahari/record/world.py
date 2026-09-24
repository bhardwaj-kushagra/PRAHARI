"""Header sections describing the world (SPEC §4.6, additive to prahari.frame/1)."""
from __future__ import annotations

import numpy as np

from prahari.record.frames import sig4


def interfaces_list(features: list) -> list:
    """Map interfaces (paths, village, road, power line) for the recording header."""
    return [{"kind": f["kind"], "closed": bool(f.get("closed", False)),
             "points": [[float(x), float(y)] for x, y in f["points"]]} for f in features]


def lambda_grid(land, cell_out_m: float) -> dict:
    """Ignition intensity averaged onto `cell_out_m` cells and normalised to [0, 1] for the heat layer."""
    f = max(1, int(round(cell_out_m / land.cell_m)))
    ny, nx = (s // f for s in land.lam.shape)
    w = (land.lam * land.forest)[:ny * f, :nx * f].reshape(ny, f, nx, f).mean(axis=(1, 3))
    top = float(w.max())
    vals = (w / top if top > 0 else w).ravel()
    return {"cell_m": land.cell_m * f, "x0": land.cell_m * f / 2.0, "y0": land.cell_m * f / 2.0,
            "nx": int(nx), "ny": int(ny), "modelled": bool(land.modelled),
            "values": [round(float(v), 3) for v in vals]}


def layouts_dict(layout) -> dict:
    """The active layout and all three candidate layouts with their covered likelihood (M1, M4)."""
    out = {"active": layout.name, "corridor_spacing_m": float(f"{layout.corridor_spacing_m:.4g}")}
    for k, alt in layout.alternatives.items():
        cov = float(alt["covered"])
        out[k] = {"covered": None if cov < 0 else round(cov, 4),
                  "nodes": [[float(f"{x:.5g}"), float(f"{y:.5g}")] for x, y in np.asarray(alt["xy"]).tolist()]}
    return out


def links_dict(links, gateways: list) -> dict:
    """Per-node radio links for the header (M38): gateway, SF, distance, path loss, received power, relay."""
    ids = [g["id"] for g in gateways]
    return {"modelled": bool(links.modelled),
            "gateway": [ids[g] if g >= 0 else None for g in links.gateway.tolist()],
            "sf": [int(s) if s > 0 else None for s in links.sf.tolist()],
            "d_m": sig4(links.d_m), "pl_db": sig4(links.pl_db), "prx_dbm": sig4(links.prx_dbm),
            **({"relay": [int(r) if r >= 0 else None for r in links.relay.tolist()]}          # Phase 8, TS011
               if links.relay is not None and (links.relay >= 0).any() else {})}
