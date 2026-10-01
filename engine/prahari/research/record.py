"""One recording pass per seed and pass type (protocol R1 §3): the readings and every node-layer variant's CUSUM input.

The main simulation steps the signals and its node layer; each extra variant is a second `Simulation` built from a
configuration with that variant's overrides. Its node stages are stepped on the same readings: the median-referenced
input (R3) for `med`, the one-factor gain-weighted reference (protocol R2, R9) for `factor`, unchanged readings
otherwise. Nothing is written; arrays stay in memory for `operating.py` and `operating_r2.py`.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np

from prahari.core.contracts import Readings
from prahari.core.pipeline import Simulation
from prahari.detect.prahari.cusum_real import elevated_fraction
from prahari.eval.experiments import LEGACY_ABLATIONS
from prahari.detect.prahari.qcc import P_FLOOR

# Node-layer variants: parameter overrides ("module.param") and the input reference: None (the readings), "med"
# (network median, R3) or "factor" (one-factor gain-weighted reference, R2 R9).
NODE_VARIANTS = {"main": ({}, None), "med": ({}, "med"), "factor": ({}, "factor"),
                 "qcc": (LEGACY_ABLATIONS["P2-QCC"], None), "ttc": (LEGACY_ABLATIONS["P2-TTC"], None)}
FACTOR_MIN_MINUTES = 120                     # R9 — fewer common-mode calibration minutes: ĝ = 1
FACTOR_CLIP = (0.2, 3.0)                     # R9 — ĝ clipped


@dataclass
class NodeTrace:
    """A node-layer variant over the run: CUSUM input s (T, N), node p-values (T, N), elevated-node share (T,)."""
    s: np.ndarray
    p: np.ndarray
    frac: np.ndarray
    k: float
    params: dict


@dataclass
class PassRecord:
    """Readings (channel 0) of one pass, the regional haze level H(t) per minute (M20; R2-10), and the node traces of
    every requested variant."""
    x: np.ndarray
    x_raw: np.ndarray
    nodes: dict = field(default_factory=dict)
    haze: np.ndarray | None = None
    haze_notes: dict = field(default_factory=dict)      # the haze stage's snapshot (M20b episodes) and node gains
    factor_gain: np.ndarray | None = None               # R9 — the fitted ĝ (None without the factor variant)


def fit_factor_gain(D, clip=FACTOR_CLIP, min_minutes: int = FACTOR_MIN_MINUTES) -> np.ndarray:
    """R9 — ĝ_i by least squares of d_i(t) on m(t) = median_j d_j(t) over the common-mode calibration minutes D
    (T_cm, N), no intercept; clipped; ones when there are fewer than `min_minutes` minutes."""
    D = np.asarray(D, dtype=float)
    if D.ndim != 2 or D.shape[0] < min_minutes:
        return np.ones(D.shape[1] if D.ndim == 2 else 0)
    m = np.median(D, axis=1)
    mm = float(m @ m)
    if mm <= 0:
        return np.ones(D.shape[1])
    return np.clip((m @ D) / mm, clip[0], clip[1])


def factor_input(x0, b0, g) -> np.ndarray:
    """R9 — x̃_i = x_i − ĝ_i · median_j(d_j / ĝ_j), with d = x − b (b the slow baseline, M24)."""
    return x0 - g * np.median((x0 - b0) / g)


def variant_config(cfg: dict, overrides: dict) -> dict:
    """The configuration with "module.param" overrides applied (as `run_seed` applies the legacy ablations)."""
    c = copy.deepcopy(cfg)
    for key, v in overrides.items():
        m, param = key.split(".", 1)
        c["params"][m][param] = v
    return c


def _node_step(sim: Simulation, t: int, tick: int, readings: Readings):
    sim.ctx.t, sim.ctx.tick = t, tick
    _, _, sc, _ = sim.step_node(readings)
    return sc


def record_pass(cfg: dict, scripted=(), variants=("main",)) -> tuple[Simulation, PassRecord]:
    """Run one pass (quiet, or with the scripted fires) and record channel-0 readings and the node traces."""
    cfg = copy.deepcopy(cfg)
    cfg["params"]["ignition"]["scripted"] = [{"t_min": int(t0), "x": float(p[0]), "y": float(p[1])} for t0, p in scripted]
    sim = Simulation(cfg)
    sim.prepare()
    variants = sorted(variants, key=lambda v: v != "main")           # main first: the factor reference reads it
    if "factor" in variants and "main" not in variants:
        raise ValueError("the factor variant needs the main node layer")
    extra = {}
    for v in variants:
        if v != "main":
            s = Simulation(variant_config(cfg, NODE_VARIANTS[v][0]))
            s.prepare()
            extra[v] = s
    T, n = int(sim.clock.n_ticks), sim.ctx.n_nodes
    rec = PassRecord(x=np.zeros((T, n)), x_raw=np.zeros((T, n)))
    hz = np.zeros(T)
    buf = {v: (np.zeros((T, n)), np.zeros((T, n)), np.zeros(T)) for v in variants}
    stat_z = {v: _cusum_params(cfg, v).get("statistic", "neglogp") == "z" for v in variants}
    cm_z, cm_frac = float(cfg["params"]["cusum"]["cm_z"]), float(cfg["params"]["cusum"]["cm_frac"])
    fit_at = int(cfg["params"]["cusum"]["tune_start_min"])          # R9 — ĝ fitted when the calibration days end
    g_hat, cm_rows, b0 = np.ones(n), [], None
    for tick, t in enumerate(sim.clock.minutes()):
        if t != tick:
            raise ValueError("research passes assume one-minute ticks starting at minute 0")
        sim.ctx.tick = tick
        *_, haze, x = sim.step_signals(t)
        hz[tick] = float(getattr(haze, "level", 0.0) or 0.0)                               # M20 — H(t), R2-10
        rec.x[tick], rec.x_raw[tick] = x.x[:, 0], x.x_raw[:, 0]
        for v in variants:
            if v == "main":
                res, _, sc, _ = sim.step_node(x)
                z = sim.ctx.z_slow
                b0 = res.b[:, 0]
                if "factor" in variants and t < fit_at and elevated_fraction(z, cm_z) >= cm_frac:
                    cm_rows.append(x.x[:, 0] - b0)                                    # R9 — common-mode minutes
            else:
                s = extra[v]
                xin = x
                ref = NODE_VARIANTS[v][1]
                if ref == "med":                             # R3 — network-median reference
                    xin = Readings(x=x.x - np.median(x.x, axis=0, keepdims=True), x_raw=x.x_raw,
                                   fault=x.fault, missing=x.missing)
                elif ref == "factor":                        # R9 — one-factor gain-weighted reference
                    if x.x.shape[1] != 1:
                        raise ValueError("the factor reference is defined for one channel")
                    if t == fit_at:
                        g_hat = fit_factor_gain(np.array(cm_rows) if cm_rows else np.zeros((0, n)))
                        rec.factor_gain = g_hat
                    xin = Readings(x=factor_input(x.x[:, 0], b0, g_hat)[:, None], x_raw=x.x_raw,
                                   fault=x.fault, missing=x.missing)
                sc = _node_step(s, t, tick, xin)
                z = s.ctx.z_slow
            S, P, F = buf[v]
            P[tick] = sc.p_node
            S[tick] = sc.z if stat_z[v] else -np.log(np.clip(sc.p_node, P_FLOOR, 1.0))   # M28 input (as CusumReal)
            F[tick] = elevated_fraction(z, cm_z)                                           # M28 common mode
    rec.haze = hz
    hs = sim.slots["haze"].chain[0]
    rec.haze_notes = {**hs.snapshot(), "gain": [round(float(g), 4) for g in np.atleast_1d(getattr(
        getattr(hs, "_b", None) or hs, "gain", []))]}
    for v in variants:
        p = _cusum_params(cfg, v)
        k = float(p["k_z"] if p.get("statistic", "neglogp") == "z" else p["k_node"])
        rec.nodes[v] = NodeTrace(*buf[v], k=k, params=p)
    return sim, rec


def _cusum_params(cfg: dict, v: str) -> dict:
    return variant_config(cfg, NODE_VARIANTS[v][0])["params"]["cusum"]
