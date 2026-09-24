"""One recording pass per seed and pass type (protocol R1 §3): the readings and every node-layer variant's CUSUM input.

The main simulation steps the signals and its node layer; each extra variant is a second `Simulation` built from a
configuration with that variant's overrides. Its node stages are stepped on the same readings: the median-referenced
input (R3) for `med`, unchanged readings otherwise. Nothing is written; arrays stay in memory for `operating.py`.
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

# Node-layer variants: parameter overrides ("module.param") and whether the input is median-referenced (R3).
NODE_VARIANTS = {"main": ({}, False), "med": ({}, True),
                 "qcc": (LEGACY_ABLATIONS["P2-QCC"], False), "ttc": (LEGACY_ABLATIONS["P2-TTC"], False)}


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
    """Readings (channel 0) of one pass and the node traces of every requested variant."""
    x: np.ndarray
    x_raw: np.ndarray
    nodes: dict = field(default_factory=dict)


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
    extra = {}
    for v in variants:
        if v != "main":
            s = Simulation(variant_config(cfg, NODE_VARIANTS[v][0]))
            s.prepare()
            extra[v] = s
    T, n = int(sim.clock.n_ticks), sim.ctx.n_nodes
    rec = PassRecord(x=np.zeros((T, n)), x_raw=np.zeros((T, n)))
    buf = {v: (np.zeros((T, n)), np.zeros((T, n)), np.zeros(T)) for v in variants}
    stat_z = {v: _cusum_params(cfg, v).get("statistic", "neglogp") == "z" for v in variants}
    cm_z = float(cfg["params"]["cusum"]["cm_z"])
    for tick, t in enumerate(sim.clock.minutes()):
        if t != tick:
            raise ValueError("research passes assume one-minute ticks starting at minute 0")
        sim.ctx.tick = tick
        *_, x = sim.step_signals(t)
        rec.x[tick], rec.x_raw[tick] = x.x[:, 0], x.x_raw[:, 0]
        for v in variants:
            if v == "main":
                _, _, sc, _ = sim.step_node(x)
                z = sim.ctx.z_slow
            else:
                s = extra[v]
                xin = x
                if NODE_VARIANTS[v][1]:                      # R3 — network-median reference
                    xin = Readings(x=x.x - np.median(x.x, axis=0, keepdims=True), x_raw=x.x_raw,
                                   fault=x.fault, missing=x.missing)
                sc = _node_step(s, t, tick, xin)
                z = s.ctx.z_slow
            S, P, F = buf[v]
            P[tick] = sc.p_node
            S[tick] = sc.z if stat_z[v] else -np.log(np.clip(sc.p_node, P_FLOOR, 1.0))   # M28 input (as CusumReal)
            F[tick] = elevated_fraction(z, cm_z)                                           # M28 common mode
    for v in variants:
        p = _cusum_params(cfg, v)
        k = float(p["k_z"] if p.get("statistic", "neglogp") == "z" else p["k_node"])
        rec.nodes[v] = NodeTrace(*buf[v], k=k, params=p)
    return sim, rec


def _cusum_params(cfg: dict, v: str) -> dict:
    return variant_config(cfg, NODE_VARIANTS[v][0])["params"]["cusum"]
