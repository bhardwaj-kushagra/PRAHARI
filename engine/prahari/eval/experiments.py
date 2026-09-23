"""Headless evaluation harness (SPEC §7 Phase 4, M46 protocol).

Per seed: a quiet pass (no fires) counts false incidents; a fire pass (the same seed, so the same background, plus
protocol fires) measures detection. Only the signal stages and the baselines are stepped — no frames are built.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np

from prahari.core.pipeline import Simulation
from prahari.core.rng import make_rngs
from prahari.eval.stats import detect, incidents, per_month, wilson

PIPELINE_STAGES = {"P0": "baseline_p0", "P1": "baseline_p1"}
REFERENCE = Path(__file__).resolve().parents[2] / "tests" / "golden" / "report_reference.json"


def protocol_fires(seed: int, ev: dict, xy: np.ndarray, t_total: int) -> tuple[list, list]:
    """M46 — fires at 6-hour slots in the test period, kept with p 0.8 (dry) / 0.2 (wet), uniform in the grid."""
    rng = make_rngs(seed)["protocol"]
    n_days = t_total // 1440 + 1
    dry = rng.random(n_days) < ev["dry_day_prob"]
    test0 = (ev["calibration_days"] + ev["tuning_days"]) * 1440
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    fires = []
    for s0 in range(test0 + ev["slot_start_min"], t_total - ev["slot_end_margin_min"], ev["slot_min"]):
        t0 = s0 + int(rng.integers(0, ev["slot_jitter_min"]))
        if rng.random() > (ev["fire_prob_dry"] if dry[t0 // 1440] else ev["fire_prob_wet"]):
            continue
        fires.append((t0, rng.uniform(lo, hi)))
    return fires, dry.tolist()


def run_pass(cfg: dict, pipelines, scripted=()) -> tuple[Simulation, dict]:
    """Step signals and baselines for the whole run; return the alarms (t, node, members) per pipeline."""
    cfg = copy.deepcopy(cfg)
    cfg["params"]["ignition"]["scripted"] = [{"t_min": int(t0), "x": float(p[0]), "y": float(p[1])} for t0, p in scripted]
    sim = Simulation(cfg)
    sim.prepare()
    alarms = {name: [] for name in pipelines}
    want = {name: PIPELINE_STAGES[name] for name in pipelines}
    for tick, t in enumerate(sim.clock.minutes()):
        sim.ctx.tick = tick
        *_, x = sim.step_signals(t)
        for name, stage in want.items():
            out = sim.stage(stage, x)
            alarms[name].extend((t, i, list(members)) for i, members in out.alarms)
    return sim, alarms


def run_seed(base_cfg: dict, seed: int, pipelines) -> dict:
    ev = base_cfg["params"]["evaluation"]
    days = ev["calibration_days"] + ev["tuning_days"] + ev["test_days"]
    test0, t_total = (ev["calibration_days"] + ev["tuning_days"]) * 1440, days * 1440
    cfg = copy.deepcopy(base_cfg)
    cfg["run"]["seed"], cfg["run"]["days"] = seed, days
    for stage in PIPELINE_STAGES.values():
        cfg["params"][stage]["start_min"] = test0
    sim, quiet = run_pass(cfg, pipelines)
    xy, dist, R = sim.ctx.xy, sim.ctx.dist, sim.ctx.radius_m
    fires, dry = protocol_fires(seed, ev, xy, t_total)
    _, burn = run_pass(cfg, pipelines, fires)
    out = {"seed": seed, "test_days": ev["test_days"], "n_fires": len(fires),
           "fires": [{"t0": int(t0), "x": round(float(p[0]), 2), "y": round(float(p[1]), 2),
                      "dry": bool(dry[t0 // 1440])} for t0, p in fires], "pipelines": {}}
    for name in pipelines:
        k = incidents(quiet[name], dist, R, test0, t_total, ev["merge_min"], ev["merge_radius_factor"])
        lat = detect(burn[name], fires, xy, ev["detect_radius_m"], ev["detect_window_min"])
        stage = sim.slots[PIPELINE_STAGES[name]]
        out["pipelines"][name] = {
            "false_incidents": k, "false_incidents_per_month": k / ev["test_days"] * ev["month_days"],
            "alarms_quiet": len(quiet[name]), "latencies_min": lat,
            "detected": sum(v is not None for v in lat), "state": stage.health.state,
        }
    return out


def summarise(per_seed: list, preset: str, cfg: dict) -> dict:
    ev = cfg["params"]["evaluation"]
    pipes = {}
    for name in per_seed[0]["pipelines"]:
        rows = [s["pipelines"][name] for s in per_seed]
        k = sum(r["false_incidents"] for r in rows)
        days = sum(s["test_days"] for s in per_seed)
        lat = [v for r in rows for v in r["latencies_min"]]
        det = [v for v in lat if v is not None]
        lo, hi = wilson(len(det), len(lat))
        pipes[name] = {
            "false_incidents_per_month": {**per_month(k, days, ev["month_days"]),
                                          "per_seed": [r["false_incidents_per_month"] for r in rows]},
            "confirmed_within_3h": {"k": len(det), "n": len(lat), "rate": len(det) / len(lat) if lat else None,
                                    "ci95": [lo, hi]},
            "latency_median_min": float(np.median(det)) if det else None,
        }
    summary = {"label": "SIMULATION", "preset": preset, "scenario": cfg["scenario"]["name"],
               "seeds": [s["seed"] for s in per_seed], "n_nodes": cfg["world"]["n_nodes"],
               "spacing_m": cfg["world"]["spacing_m"],
               "days": {"calibration": ev["calibration_days"], "tuning": ev["tuning_days"], "test": ev["test_days"]},
               "pipelines": pipes}
    if REFERENCE.is_file():
        summary["reference"] = json.loads(REFERENCE.read_text(encoding="utf-8"))
    return summary


def run_experiment(cfg: dict, preset: str, seeds, pipelines, out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    per_seed = []
    for seed in seeds:
        res = run_seed(cfg, int(seed), pipelines)
        (out / f"{preset}_seed{seed}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        per_seed.append(res)
    summary = summarise(per_seed, preset, cfg)
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary
