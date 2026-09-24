"""Energy comparison for the Results view (SPEC §5.13, Phase 8): M41 daily budgets per sensor and scan mode, the M42
harvest on clear and cloudy days, and the M43 store — computed from the configuration, no random draws."""
from __future__ import annotations

from prahari.comms.lora import time_on_air
from prahari.energy.power import daily_budget_wh, solar_day_wh, usable_wh

ROWS = (("BME688", "ULP", "bme688", "ulp"), ("BME688", "low power", "bme688", "lp"),
        ("BME688", "standard", "bme688", "standard"), ("MQ-2", "heater on", "mq2", "standard"))


def energy_table(cfg: dict) -> dict:
    """M41–M43 comparison from the configuration (no random draws): daily budget per sensor mode, days on a
    full store, clear and cloudy harvest."""
    p, c = cfg["params"]["energy"], cfg["params"]["comms"]
    frames = 1440 / float(c["heartbeat_min"])                         # hourly heartbeats; candidates are rare
    toa = time_on_air(int(c["payload_b"]), 7, float(c["bw_hz"]), int(c["cr"]))
    store = usable_wh(float(p["capacitance_f"]), float(p["v_max"]), float(p["v_min"]), int(p["cells"]))
    rows = []
    for sensor, label, kind, mode in ROWS:
        q = dict(p, sensor_kind=kind, bme688_mode=mode if mode != "ulp" else p["bme688_mode"])
        wh = daily_budget_wh(q, "ulp" if mode == "ulp" else "standard", frames, toa)     # M41
        rows.append({"sensor": sensor, "mode": label, "wh_day": round(wh, 4), "autonomy_days": round(store / wh, 2)})
    clear = solar_day_wh(p)                                            # M42
    lo, hi = (float(v) for v in p["cloudy_factor"])
    return {"label": "SIMULATION", "what": "M41 daily budget per sensor mode; M42 harvest; M43 store",
            "rows": rows, "harvest_wh_day": {"clear": round(clear, 4), "cloudy": [round(clear * lo, 4), round(clear * hi, 4)]},
            "store_wh": round(store, 3), "frames_per_day": frames, "toa_ms": round(toa * 1e3, 1),
            "voltage_v": p["voltage_v"], "source": "configs/default.yaml (params.energy, params.comms)"}
