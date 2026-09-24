"""Pure helpers that turn stage outputs into frame-contract dictionaries (SPEC §4.6)."""
from __future__ import annotations

import base64

import numpy as np

# Node state codes (SPEC §4.6)
NORMAL, ELEVATED, CANDIDATE, CONFIRMED, FAULT, LOW_POWER = range(6)


def node_states(p_node, recent_candidate, confirmed, fault, soc, elevated_p: float, low_soc: float) -> np.ndarray:
    """Map per-node evidence to a display state; later rules take precedence."""
    s = np.full(p_node.shape[0], NORMAL, dtype=int)
    s[p_node < elevated_p] = ELEVATED
    s[recent_candidate] = CANDIDATE
    s[confirmed] = CONFIRMED
    if fault is not None:
        s[fault] = FAULT
    s[soc < low_soc] = LOW_POWER
    return s


def sig4(a) -> list:
    """Round to 4 significant figures for compact, deterministic JSON."""
    return [float(f"{v:.4g}") for v in np.asarray(a, dtype=float).ravel().tolist()]


def weather_dict(env, fuel) -> dict:
    return {"T": float(f"{env.T:.4g}"), "RH": float(f"{env.RH:.4g}"), "wind_ms": float(f"{env.wind_ms:.4g}"),
            "wind_dir_deg": float(f"{env.wind_dir_deg:.4g}"), "rain_mm": float(f"{env.rain_mm:.4g}"),
            "ffmc": float(f"{fuel.ffmc:.4g}"), "dew_c": float(f"{env.dew_c:.4g}")}


def fires_list(src) -> list:
    return [{"id": int(i), "x": float(f"{x:.4g}"), "y": float(f"{y:.4g}"), "area_m2": float(f"{a:.4g}"),
             "age_min": int(age), "q": float(f"{q:.4g}")}
            for i, x, y, a, age, q in zip(src.ids, src.x, src.y, src.area_m2, src.age_min, src.q)]


def plume_grid(field_fn, fire_x, fire_y, width_m: float, height_m: float, cell_m: float, margin_m: float) -> dict:
    """Coarse plume grid for the heat overlay (SPEC §5.5): the active plume model evaluated on cell centres over the
    fires' bounding box ± margin, clipped to the map; float16 little-endian, base64. Row 0 is the southern row."""
    x0 = max(0.0, np.floor((min(fire_x) - margin_m) / cell_m) * cell_m)
    y0 = max(0.0, np.floor((min(fire_y) - margin_m) / cell_m) * cell_m)
    x1 = min(width_m, np.ceil((max(fire_x) + margin_m) / cell_m) * cell_m)
    y1 = min(height_m, np.ceil((max(fire_y) + margin_m) / cell_m) * cell_m)
    nx, ny = max(1, int(round((x1 - x0) / cell_m))), max(1, int(round((y1 - y0) / cell_m)))
    gx, gy = np.meshgrid(x0 + cell_m * (np.arange(nx) + 0.5), y0 + cell_m * (np.arange(ny) + 0.5))
    c = np.asarray(field_fn(np.column_stack([gx.ravel(), gy.ravel()])), dtype=float)
    c = np.clip(np.nan_to_num(c, nan=0.0, posinf=6.0e4), 0.0, 6.0e4)          # float16 range
    return {"x0": float(x0), "y0": float(y0), "cell_m": float(cell_m), "nx": nx, "ny": ny,
            "max": float(f"{c.max():.4g}"), "data": base64.b64encode(c.astype("<f2").tobytes()).decode("ascii")}


def decode_plume_grid(grid: dict) -> np.ndarray:
    """Inverse of plume_grid's encoding: (ny, nx) float array."""
    raw = np.frombuffer(base64.b64decode(grid["data"]), dtype="<f2").astype(float)
    return raw.reshape(grid["ny"], grid["nx"])
