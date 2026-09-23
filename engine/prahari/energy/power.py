"""Node energy maths (SPEC §5.13, Phase 8): daily budget (M41), solar harvest (M42), supercapacitor store (M43).
Pure functions; energies in watt-hours, currents in milliamps, times in seconds."""
from __future__ import annotations

import numpy as np

MODES = ("standard", "ulp", "off")                     # node power modes (SoC ≥ 20%, < 20%, < 5%)


def sensor_current_ma(p: dict, mode: str) -> float:
    """M41 — continuous sensor current: BME688 scan mode by node mode, or the MQ-2 heater (P = 950 mW at V)."""
    if mode == "off":
        return 0.0
    if p["sensor_kind"] == "mq2":
        return p["mq2_heater_mw"] / p["voltage_v"]
    return p["bme688_ma"]["ulp" if mode == "ulp" else p["bme688_mode"]]


def mcu_current_ma(p: dict, mode: str) -> float:
    """M41 — ESP32 average current: active `mcu_active_s` per minute at `mcu_active_ma`, deep sleep otherwise."""
    if mode == "off":
        return p["mcu_sleep_ma"]
    a = p["mcu_active_s_per_min"] / 60.0
    return a * p["mcu_active_ma"] + (1.0 - a) * p["mcu_sleep_ma"]


def radio_wh(p: dict, toa_s) -> np.ndarray:
    """M41 — one frame: transmit for its time on air, then the two Class A receive windows."""
    toa = np.asarray(toa_s, dtype=float)
    mah = (p["tx_ma"] * toa + p["rx_ma"] * p["rx_window_s"] * 2) / 3600.0
    return mah * p["voltage_v"] / 1000.0


def daily_budget_wh(p: dict, mode: str, frames_per_day: float, toa_s: float) -> float:
    """M41 — E_day = V Σ I_m t_m for one node in `mode`, with `frames_per_day` uplinks of `toa_s` each."""
    base_ma = sensor_current_ma(p, mode) + mcu_current_ma(p, mode)
    radio = 0.0 if mode == "off" else frames_per_day * float(radio_wh(p, toa_s))
    return base_ma * 24.0 * p["voltage_v"] / 1000.0 + radio


def solar_power_w(tod_min, e_day_wh):
    """M42 — half-sine harvest from 06:00 to 18:00 that integrates to `e_day_wh` over the day (W)."""
    h = np.asarray(tod_min, dtype=float) / 60.0
    shape = np.where((h >= 6.0) & (h < 18.0), np.sin(np.pi * (h - 6.0) / 12.0), 0.0)
    return np.asarray(e_day_wh, dtype=float) * np.pi / 24.0 * shape    # ∫ sin over 12 h = 24/π h


def solar_day_wh(p: dict) -> float:
    """M42 — E_solar,day = A η G_day k_canopy (Wh) on a clear day."""
    return p["panel_kw"] * p["irradiance_kwh_m2_day"] * p["canopy_k"] * 1000.0


def usable_wh(capacitance_f: float, v_max: float, v_min: float, cells: int) -> float:
    """M43 — E = ½ C (V² − V_min²) per cell, in Wh."""
    return cells * 0.5 * capacitance_f * (v_max ** 2 - v_min ** 2) / 3600.0


def next_mode(soc, mode, ulp_below: float, stop_below: float, resume_at: float) -> np.ndarray:
    """M43 — standard ≥ ulp_below; ULP below it; off below stop_below until SoC recovers to resume_at."""
    soc = np.asarray(soc, dtype=float)
    was_off = np.asarray(mode) == 2
    off = np.where(was_off, soc < resume_at, soc < stop_below)
    return np.where(off, 2, np.where(soc < ulp_below, 1, 0))
