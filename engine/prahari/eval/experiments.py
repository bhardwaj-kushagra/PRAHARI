"""Headless evaluation harness (SPEC §7 Phases 4 and 7, M46 protocol).

Per seed: a quiet pass (no fires) counts false incidents; a fire pass (the same seed, so the same background, plus
protocol fires) measures detection. No frames are built. The baselines are stepped live; PRAHARI's node layer is
stepped live and recorded, and its edge variants and the operating dial are replayed offline (`offline.py`). Node-layer
ablations (P2-QCC, P2-TTC) get passes of their own.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np

from prahari.core.pipeline import Simulation
from prahari.core.rng import make_rngs
from prahari.eval.node_metrics import NodeObserver, summarise_node
from prahari.eval.offline import ScoreRecorder, edge_alarms, edge_stages, replay_candidates, tuned_h
from prahari.eval.stats import detect, incidents, per_month, wilson
from prahari.record.writer import write_text_atomic

PIPELINE_STAGES = {"P0": "baseline_p0", "P1": "baseline_p1", "P1t": "baseline_p1t"}
# PRAHARI and its ablations (SPEC §9.3): module states that differ from the configuration's.
ABLATIONS = {"P2": {}, "P2-SCMR": {"scmr": "stub"}, "P2-RAQ": {"raq": "stub"}, "P2-QCC": {"qcc": "stub"},
             "P2-TTC": {"ttc": "stub"}}
NODE_MODULES = ("ttc", "qcc", "score", "cusum")
# `experiment.ablation_form: legacy` (P7-12): the report simulation's node ablations, as parameter overrides —
# "minus conformal" = CUSUM on the median/MAD z of the fast residual (k 0.5); "minus two-timescale" = conformal p of
# the capped slow z. Edge ablations are the same in both forms.
LEGACY_ABLATIONS = {"P2-QCC": {"qcc.form": "robust_z", "cusum.statistic": "z"}, "P2-TTC": {"ttc.detect_on": "slow"}}
REFERENCE = Path(__file__).resolve().parents[2] / "tests" / "golden" / "report_reference.json"


def protocol_fires(seed: int, ev: dict, xy: np.ndarray, t_total: int) -> tuple[list, list]:
    """M46 — fires at 6-hour slots in the test period, kept with p 0.8 (dry) / 0.2 (wet), uniform in the grid."""
    rng = make_rngs(seed)["protocol"]
    dry = rng.random(t_total // 1440 + 1) < ev["dry_day_prob"]          # first draw: see protocol_day_types
    test0 = (ev["calibration_days"] + ev["tuning_days"]) * 1440
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    fires = []
    for s0 in range(test0 + ev["slot_start_min"], t_total - ev["slot_end_margin_min"], ev["slot_min"]):
        t0 = s0 + int(rng.integers(0, ev["slot_jitter_min"]))
        if rng.random() > (ev["fire_prob_dry"] if dry[t0 // 1440] else ev["fire_prob_wet"]):
            continue
        fires.append((t0, rng.uniform(lo, hi)))
    return fires, dry.tolist()


def protocol_day_types(seed: int, ev: dict, t_total: int) -> list[bool]:
    """M46 — the protocol's day types (True = dry, busy); the same first draw as `protocol_fires`."""
    return (make_rngs(seed)["protocol"].random(t_total // 1440 + 1) < ev["dry_day_prob"]).tolist()


def run_pass(cfg: dict, pipelines, scripted=(), observe=None) -> tuple[Simulation, dict]:
    """Step signals and the baselines in `pipelines` for the whole run; return their alarms (t, node, members).
    With `observe`, the node layer is stepped too and `observe(t, res, pv, cand)` is called every tick."""
    cfg = copy.deepcopy(cfg)
    cfg["params"]["ignition"]["scripted"] = [{"t_min": int(t0), "x": float(p[0]), "y": float(p[1])} for t0, p in scripted]
    sim = Simulation(cfg)
    sim.prepare()
    want = {name: PIPELINE_STAGES[name] for name in pipelines if name in PIPELINE_STAGES}
    alarms = {name: [] for name in want}
    for tick, t in enumerate(sim.clock.minutes()):
        sim.ctx.tick = tick
        *_, x = sim.step_signals(t)
        for name, stage in want.items():
            out = sim.stage(stage, x)
            alarms[name].extend((t, i, list(members)) for i, members in out.alarms)
        if observe is not None:
            res, pv, _, cand = sim.step_node(x)
            observe(t, res, pv, cand)
    return sim, alarms


def protocol_config(base_cfg: dict, seed: int) -> tuple[dict, dict, int, int]:
    """The M46 protocol applied to a configuration: run length, CUSUM start, tuning window, shared day types."""
    ev = base_cfg["params"]["evaluation"]
    days = ev["calibration_days"] + ev["tuning_days"] + ev["test_days"]
    test0, t_total = (ev["calibration_days"] + ev["tuning_days"]) * 1440, days * 1440
    cfg = copy.deepcopy(base_cfg)
    cfg["run"]["seed"], cfg["run"]["days"] = seed, days
    dry = protocol_day_types(seed, ev, t_total)                 # M33 legacy prior shares the protocol's day types
    cfg["params"]["srp"]["day_type_overrides"] = [{"day": d + 1, "type": "dry_busy" if v else "wet_quiet"}
                                                  for d, v in enumerate(dry)]
    for stage in [*PIPELINE_STAGES.values(), "cusum"]:
        cfg["params"][stage]["start_min"] = test0              # the report starts every CUSUM at the test period
    for stage in ("cusum", "baseline_p1t"):                     # M28 tuning days follow the protocol
        cfg["params"][stage]["tune_start_min"] = ev["calibration_days"] * 1440
        cfg["params"][stage]["tune_end_min"] = test0
    cfg["params"]["qcc"]["cal_days"] = ev["calibration_days"]
    return cfg, ev, test0, t_total


def _node_overrides(name: str, form: str) -> dict:
    """Node-layer overrides of a PRAHARI variant: module states ("qcc": "stub") or parameters ("qcc.form": …)."""
    if form == "legacy" and name in LEGACY_ABLATIONS:
        return LEGACY_ABLATIONS[name]
    return {m: s for m, s in ABLATIONS[name].items() if m in NODE_MODULES}


def _groups(pipelines, form: str = "stub") -> dict:
    """PRAHARI variants grouped by their node-layer overrides: each group needs its own pair of passes."""
    groups: dict[tuple, list] = {}
    for name in pipelines:
        if name in ABLATIONS:
            key = tuple(sorted(_node_overrides(name, form).items()))
            groups.setdefault(key, []).append(name)
    if any(n in PIPELINE_STAGES for n in pipelines):
        groups.setdefault((), [])
    return groups


def _row(quiet, fire_lat, dist, R, ev, test0, t_total, state) -> dict:
    k = incidents(quiet, dist, R, test0, t_total, ev["merge_min"], ev["merge_radius_factor"])
    return {"false_incidents": k, "false_incidents_per_month": k / ev["test_days"] * ev["month_days"],
            "alarms_quiet": len(quiet), "latencies_min": fire_lat,
            "detected": sum(v is not None for v in fire_lat), "state": state}


def run_seed(base_cfg: dict, seed: int, pipelines, node_metrics: bool = False, dial=()) -> dict:
    """The M46 protocol for one seed: quiet and fire passes, baselines stepped live, PRAHARI variants replayed
    offline, optional node metrics and operating dial; returns the seed's rows."""
    cfg0, ev, test0, t_total = protocol_config(base_cfg, seed)
    out = {"seed": seed, "test_days": ev["test_days"], "pipelines": {}}
    fires = None
    for key, names in _groups(pipelines, base_cfg["experiment"].get("ablation_form", "stub")).items():
        cfg = copy.deepcopy(cfg0)
        for k, v in key:                                         # module state, or "module.param" override
            if "." in k:
                m, param = k.split(".", 1)
                cfg["params"][m][param] = v
            else:
                cfg["modules"][k] = v
        base = key == ()
        n = int(cfg["world"]["n_nodes"])
        rec_q = ScoreRecorder(t_total, n, cfg["params"]["cusum"]["cm_z"])
        obs = NodeObserver(test0, t_total, ev["exceed_p"], cfg["params"]["cusum"]["cm_z"]) if node_metrics and base else None
        both = (lambda *a: (rec_q(*a), obs(*a))) if obs is not None else rec_q
        baselines = [p for p in pipelines if p in PIPELINE_STAGES] if base else []
        sim, quiet = run_pass(cfg, baselines, observe=both)
        xy, dist, R = sim.ctx.xy, sim.ctx.dist, sim.ctx.radius_m
        if fires is None:
            fires, dry = protocol_fires(seed, ev, xy, t_total)
            out.update(n_fires=len(fires), fires=[{"t0": int(t0), "x": round(float(p[0]), 2), "y": round(float(p[1]), 2),
                                                   "dry": bool(dry[t0 // 1440])} for t0, p in fires])
        rec_f = ScoreRecorder(t_total, n, cfg["params"]["cusum"]["cm_z"])
        _, burn = run_pass(cfg, baselines, fires, observe=rec_f)
        for name in baselines:
            lat = detect(burn[name], fires, xy, ev["detect_radius_m"], ev["detect_window_min"])
            out["pipelines"][name] = _row(quiet[name], lat, dist, R, ev, test0, t_total,
                                          sim.slots[PIPELINE_STAGES[name]].health.state)
        h = sim.slots["cusum"].stage.snapshot().get("h")
        cand_lat = detect([(t, i, [i]) for t, (ns, _) in rec_f.cands.items() if t >= test0 for i in ns], fires, xy,
                          ev["detect_radius_m"], ev["detect_window_min"])
        for name in names:
            edge_over = {m: s for m, s in ABLATIONS[name].items() if m not in NODE_MODULES}
            alarms = [edge_alarms(rec.cands, edge_stages(cfg, sim.ctx, make_rngs(seed)["srp"], edge_over), sim.ctx)
                      for rec in (rec_q, rec_f)]
            lat = detect(alarms[1], fires, xy, ev["detect_radius_m"], ev["detect_window_min"])
            row = _row(alarms[0], lat, dist, R, ev, test0, t_total, "real")
            row.update(h=h, candidate_detected=sum(v is not None for v in cand_lat), candidate_latencies_min=cand_lat)
            out["pipelines"][name] = row
        if base and dial:
            p = cfg["params"]["cusum"]
            out["dial"] = []
            for target in dial:                                  # the operating dial: re-tune h for other targets
                hr, cap = tuned_h(rec_q.S, rec_q.frac, p["tune_start_min"], p["tune_end_min"], p, float(target))
                al = [edge_alarms(replay_candidates(r.S, test0, hr, p), edge_stages(cfg, sim.ctx, make_rngs(seed)["srp"]),
                                  sim.ctx) for r in (rec_q, rec_f)]
                lat = detect(al[1], fires, xy, ev["detect_radius_m"], ev["detect_window_min"])
                out["dial"].append({"target_per_node_30d": float(target), "h": hr, "h_at_cap": cap,
                                    **_row(al[0], lat, dist, R, ev, test0, t_total, "real")})
        if obs is not None:
            out["node"] = obs.summary(sim, ev)
    return out


def _pool(rows: list, days: float, ev: dict) -> dict:
    """M45 false incidents per month and M44 detection pooled over seeds."""
    k = sum(r["false_incidents"] for r in rows)
    lat = [v for r in rows for v in r["latencies_min"]]
    det = [v for v in lat if v is not None]
    lo, hi = wilson(len(det), len(lat))
    out = {"false_incidents_per_month": {**per_month(k, days, ev["month_days"]),
                                         "per_seed": [r["false_incidents_per_month"] for r in rows]},
           "confirmed_within_3h": {"k": len(det), "n": len(lat), "rate": len(det) / len(lat) if lat else None,
                                   "ci95": [lo, hi]},
           "latency_median_min": float(np.median(det)) if det else None}
    if "candidate_latencies_min" in rows[0]:                  # single-node alerts: any candidate within 150 m, 3 h
        cl = [v for r in rows for v in r["candidate_latencies_min"]]
        cd = sum(v is not None for v in cl)
        out["single_node_within_3h"] = {"k": cd, "n": len(cl), "rate": cd / len(cl) if cl else None,
                                        "ci95": list(wilson(cd, len(cl)))}
        out["h_per_seed"] = [r["h"] for r in rows]
    return out


def summarise(per_seed: list, preset: str, cfg: dict) -> dict:
    """Pool the per-seed rows of a preset into the summary (M44, M45) with the report's reference values."""
    ev = cfg["params"]["evaluation"]
    days = sum(s["test_days"] for s in per_seed)
    pipes = {name: _pool([s["pipelines"][name] for s in per_seed], days, ev) for name in per_seed[0]["pipelines"]}
    summary = {"label": "SIMULATION", "preset": preset, "scenario": cfg["scenario"]["name"],
               "seeds": [s["seed"] for s in per_seed], "n_nodes": cfg["world"]["n_nodes"],
               "spacing_m": cfg["world"]["spacing_m"],
               "days": {"calibration": ev["calibration_days"], "tuning": ev["tuning_days"], "test": ev["test_days"]},
               "ablation_form": cfg["experiment"].get("ablation_form", "stub"),
               "pipelines": pipes}
    if all("node" in s for s in per_seed):
        summary["node"] = summarise_node([{"seed": s["seed"], **s["node"]} for s in per_seed], ev)
    if all("dial" in s for s in per_seed):
        summary["dial"] = [{"target_per_node_30d": pt["target_per_node_30d"],
                            "h_per_seed": [s["dial"][j]["h"] for s in per_seed],
                            **_pool([s["dial"][j] for s in per_seed], days, ev)}
                           for j, pt in enumerate(per_seed[0]["dial"])]
    if REFERENCE.is_file():
        summary["reference"] = json.loads(REFERENCE.read_text(encoding="utf-8"))
    return summary


def _seed_job(args):
    cfg, seed, pipelines, node_metrics, dial = args
    return run_seed(cfg, seed, pipelines, node_metrics, dial)


def run_experiment(cfg: dict, preset: str, seeds, pipelines, out_dir: str | Path, node_metrics: bool = False,
                   jobs: int = 1, dial=(), spacings=()) -> dict:
    """Run the protocol for every seed (in `jobs` processes) and, with `spacings`, for every node spacing; write
    `<preset>_seed<N>.json`, `<preset>.json`, and the combined `summary.json` (`report.combine`)."""
    from prahari.eval.report import combine
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def run_all(c):
        tasks = [(c, int(s), list(pipelines), node_metrics, list(dial)) for s in seeds]
        if jobs > 1:
            import multiprocessing as mp
            with mp.get_context("fork").Pool(min(jobs, len(tasks))) as pool:
                return pool.map(_seed_job, tasks)
        return [_seed_job(t) for t in tasks]

    if spacings:
        summary = {"label": "SIMULATION", "preset": preset, "seeds": [int(s) for s in seeds], "by_spacing": {}}
        for sp in spacings:
            c = copy.deepcopy(cfg)
            c["world"]["spacing_m"] = sp
            per_seed = run_all(c)
            for res in per_seed:
                write_text_atomic(out / f"{preset}_{int(sp)}m_seed{res['seed']}.json", json.dumps(res, indent=1))
            summary["by_spacing"][str(int(sp))] = summarise(per_seed, preset, c)
    else:
        per_seed = run_all(cfg)
        for res in per_seed:
            write_text_atomic(out / f"{preset}_seed{res['seed']}.json", json.dumps(res, indent=1))
        summary = summarise(per_seed, preset, cfg)
    write_text_atomic(out / f"{preset}.json", json.dumps(summary, indent=1))
    combine(out, preset)
    return summary
