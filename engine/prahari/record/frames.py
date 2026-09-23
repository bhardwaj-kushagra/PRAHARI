"""Pure helpers that turn stage outputs into frame-contract dictionaries (SPEC §4.6)."""
from __future__ import annotations

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
