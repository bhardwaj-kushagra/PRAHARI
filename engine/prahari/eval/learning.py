"""Learning curve (M36) and calibration maturity (M26) — SPEC §5.10, Phase 9.

Learning curve. Every seed runs the M46 protocol headless: a quiet pass and a fire pass whose node candidates are
replayed through the edge (cluster → SCMR → Fisher, with the prior) to list every cluster window. Training seeds
supply the burns: the windows of the first K burns (label 1, within 150 m and 3 h of the ignition) against all quiet
windows (label 0) — quiet data is cheap for a field network, burns are not. Only windows that pass SCMR are used,
since M34 is applied to no others. Held-out seeds are scored with the bound
(K = 0) and with the fit for each K. Each rule is compared at the same false-alarm budget: the threshold on the M34
posterior odds is set to the most permissive value whose false incidents on the held-out quiet passes stay within
the budget, and the confirmation rate and median latency are read from the fire passes at that threshold.

Calibration maturity. The M46 protocol is repeated with 1–14 days of quiet calibration data: the QCC floor
p_min = 1/(n + 1) falls as the calibration set grows, and node candidates come sooner.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np

from prahari.core.contracts import Delivered
from prahari.core.rng import make_rngs
from prahari.detect.prahari.learn import sbb_bound
from prahari.detect.prahari.learn_real import fit_logistic, ln_lr_hat, window_features
from prahari.eval.experiments import protocol_config, protocol_fires, run_pass, run_seed
from prahari.eval.offline import ScoreRecorder, edge_stages
from prahari.eval.stats import detect, incidents, wilson
from prahari.record.writer import write_text_atomic

COLS = ("t", "anchor", "X", "size", "ratio", "passed", "odds", "p_cluster")


def edge_windows(cands: dict, stages: dict, ctx) -> dict:
    """Replay candidates {t: (nodes, p)} through cluster, SCMR, Fisher and the prior; one row per cluster window."""
    rows, members = [], []
    for t in sorted(cands):
        nodes, p = cands[t]
        ctx.t = t
        prior = stages["srp"].step((t, None, None), ctx)
        cl = stages["cluster"].step(Delivered(nodes=tuple(nodes), p=tuple(p)), ctx)
        if not cl.members:
            continue
        sc = stages["scmr"].step(cl, ctx)
        fi = stages["fisher"].step(cl, ctx)
        anchors = cl.anchor or tuple(m[0] for m in cl.members)
        for j, m in enumerate(cl.members):
            rows.append((t, int(anchors[j]), fi.X[j], len(m), sc.ratio[j], bool(sc.passed[j]), prior.odds,
                         fi.p_cluster[j]))
            members.append([int(i) for i in m])
    cols = {c: np.array([r[k] for r in rows], dtype=float) for k, c in enumerate(COLS)}
    cols["members"] = members
    return cols


def label_windows(w: dict, fires, xy, radius: float, window_min: int) -> np.ndarray:
    """M46 — index of the fire a window belongs to (within `radius` m and `window_min` of its ignition), or −1."""
    out = np.full(len(w["members"]), -1)
    for j, (t, m) in enumerate(zip(w["t"], w["members"])):
        for f, (t0, pos) in enumerate(fires):
            if t0 <= t <= t0 + window_min and np.hypot(*(xy[m] - pos).T).min() <= radius:
                out[j] = f
                break
    return out


def seed_windows(cfg: dict, seed: int) -> dict:
    """One seed: quiet and fire passes of the M46 protocol, their cluster windows and the fire labels."""
    cfg0, ev, test0, t_total = protocol_config(cfg, seed)
    n, cm = int(cfg0["world"]["n_nodes"]), cfg0["params"]["cusum"]["cm_z"]
    rec_q = ScoreRecorder(t_total, n, cm)
    sim, _ = run_pass(cfg0, [], observe=rec_q)
    fires, _ = protocol_fires(seed, ev, sim.ctx.xy, t_total)
    rec_f = ScoreRecorder(t_total, n, cm)
    run_pass(cfg0, [], fires, observe=rec_f)
    out = {"seed": seed, "fires": [(int(t0), np.asarray(p, dtype=float)) for t0, p in fires], "xy": sim.ctx.xy,
           "dist": sim.ctx.dist, "R": sim.ctx.radius_m, "test0": test0, "t_total": t_total}
    for name, rec in (("quiet", rec_q), ("fire", rec_f)):
        w = edge_windows(rec.cands, edge_stages(cfg0, sim.ctx, make_rngs(seed)["srp"]), sim.ctx)
        w["fire"] = label_windows(w, out["fires"], sim.ctx.xy, ev["detect_radius_m"], ev["detect_window_min"]) \
            if name == "fire" else np.full(len(w["members"]), -1)
        out[name] = w
    return out


def features(w: dict, rho_clip) -> np.ndarray:
    """M36 feature matrix of a set of cluster windows (c̄ = 1 when no health weights were recorded)."""
    return window_features(w["X"], w["size"], w["ratio"], None, rho_clip)


def training_set(train: list, K: int, rho_clip) -> tuple[np.ndarray, np.ndarray]:
    """Windows of the first K burns (training seeds in order, then by time) against every quiet window — both only
    among windows that pass SCMR, the population the M34 rule is applied to."""
    pos, neg, seen = [], [], 0
    for s in train:
        f = s["fire"]["fire"]                              # fire index per fire-pass window, or −1
        keep = (f >= 0) & (f < K - seen) & (s["fire"]["passed"] > 0)
        pos.append(features(f_rows(s["fire"], keep), rho_clip))
        seen += len(s["fires"])
        neg.append(features(f_rows(s["quiet"], s["quiet"]["passed"] > 0), rho_clip))   # the same quiet data for every K
    P, N = np.vstack(pos), np.vstack(neg)
    return np.vstack([P, N]), np.concatenate([np.ones(len(P)), np.zeros(len(N))])


def f_rows(w: dict, keep) -> dict:
    """The rows of a window table selected by a boolean mask."""
    return {k: (v[keep] if isinstance(v, np.ndarray) else [m for m, ok in zip(v, keep) if ok]) for k, v in w.items()}


def ln_posterior(w: dict, model: dict | None, rho_clip) -> np.ndarray:
    """M34 — ln(BF · prior odds) with BF the SBB bound (model None) or the M36 fit."""
    ln_bf = np.log(sbb_bound(w["p_cluster"])) if model is None else ln_lr_hat(model, features(w, rho_clip))
    return ln_bf + np.log(w["odds"])


def _alarms(w: dict, score: np.ndarray, tau: float) -> list:
    ok = (w["passed"] > 0) & (score > tau)
    return [(int(w["t"][j]), int(w["anchor"][j]), w["members"][j]) for j in np.flatnonzero(ok)]


def operating_point(test: list, scores: list, budget: float, ev: dict) -> dict:
    """The most permissive threshold whose false incidents on the held-out quiet passes stay within `budget`
    (incidents in total), then detection on the fire passes at that threshold (M44–M46)."""
    def n_inc(tau):
        return sum(incidents(_alarms(s["quiet"], sq, tau), s["dist"], s["R"], s["test0"], s["t_total"],
                             ev["merge_min"], ev["merge_radius_factor"]) for s, (sq, _) in zip(test, scores))
    qs = np.unique(np.concatenate([sq[s["quiet"]["passed"] > 0] for s, (sq, _) in zip(test, scores)]))[::-1]
    tau, k = float("inf"), 0
    for q in qs:                                       # lower the threshold until the budget is first exceeded
        c = n_inc(float(q) - 1e-9)
        if c > budget:
            tau = float(q)
            break
        k = c
    else:
        tau = -float("inf")
    lat = [v for s, (_, sf) in zip(test, scores)
           for v in detect(_alarms(s["fire"], sf, tau), s["fires"], s["xy"], ev["detect_radius_m"], ev["detect_window_min"])]
    det = [v for v in lat if v is not None]
    lo, hi = wilson(len(det), len(lat))
    return {"ln_threshold": tau, "false_incidents": k, "confirmed": len(det), "fires": len(lat),
            "rate": len(det) / len(lat) if lat else None, "ci95": [lo, hi],
            "latency_median_min": float(np.median(det)) if det else None}


def legacy_point(test: list, cfg: dict) -> dict:
    """Reference: the deployed legacy rule (M34 consequence — quorum 2 on dry, busy days, 3 on wet, quiet days, after
    SCMR) on the same held-out runs, at its own false-alarm rate."""
    rq, ev, dry_odds = cfg["params"]["raq"], cfg["params"]["evaluation"], float(cfg["params"]["srp"]["odds_dry"])

    def alarms(w):
        q = np.where(w["odds"] >= dry_odds, int(rq["quorum_dry"]), int(rq["quorum_wet"]))
        return [(int(w["t"][j]), int(w["anchor"][j]), w["members"][j])
                for j in np.flatnonzero((w["passed"] > 0) & (w["size"] >= q))]
    k = sum(incidents(alarms(s["quiet"]), s["dist"], s["R"], s["test0"], s["t_total"], ev["merge_min"],
                      ev["merge_radius_factor"]) for s in test)
    lat = [v for s in test for v in detect(alarms(s["fire"]), s["fires"], s["xy"], ev["detect_radius_m"],
                                           ev["detect_window_min"])]
    det = [v for v in lat if v is not None]
    return {"false_incidents": k, "false_incidents_per_month": k / (len(test) * ev["test_days"]) * ev["month_days"],
            "confirmed": len(det), "fires": len(lat), "rate": len(det) / len(lat) if lat else None,
            "ci95": list(wilson(len(det), len(lat))), "latency_median_min": float(np.median(det)) if det else None}


def learning_curve(train: list, test: list, cfg: dict) -> dict:
    """Fit the M36 model for each K on the training seeds and compare every rule at the fixed false-alarm budget
    on the held-out seeds; also reports the legacy quorum on the same runs."""
    ev, lp, ex = cfg["params"]["evaluation"], cfg["params"]["learn"], cfg["experiment"]
    rho_clip = tuple(lp["rho_clip"])
    days = sum(ev["test_days"] for _ in test)
    budget = float(ex["fa_budget_per_month"]) * days / ev["month_days"]
    bound = operating_point(test, [(ln_posterior(s["quiet"], None, rho_clip), ln_posterior(s["fire"], None, rho_clip))
                                   for s in test], budget, ev)
    rows, models = [], {}
    for K in ex["ks"]:
        F, y = training_set(train, int(K), rho_clip)
        model = {"K": int(K), **fit_logistic(F, y, float(lp["l2"]))}
        models[int(K)] = model
        used = int(K) >= int(lp["k_min"]) and model["n_pos"] > 0
        pt = operating_point(test, [(ln_posterior(s["quiet"], model if used else None, rho_clip),
                                     ln_posterior(s["fire"], model if used else None, rho_clip)) for s in test], budget, ev)
        rows.append({"K": int(K), "rule": "fit" if used else "bound (K < k_min)", "n_pos": model["n_pos"],
                     "n_neg": model["n_neg"], "weights": model["w"], **pt})
    return {"label": "SIMULATION", "train_seeds": [s["seed"] for s in train], "test_seeds": [s["seed"] for s in test],
            "train_fires": sum(len(s["fires"]) for s in train), "test_days": days,
            "fa_budget_per_month": float(ex["fa_budget_per_month"]), "budget_incidents": budget,
            "k_min": int(lp["k_min"]), "features": list(models[max(models)]["features"]), "bound": bound,
            "legacy_quorum": legacy_point(test, cfg), "rows": rows,
            "models": models}


def maturity_curve(cfg: dict, seeds, cal_days, run=run_seed, map_fn=map) -> dict:
    """M26 maturity: the protocol with 1–14 days of calibration data; QCC floor and node-candidate latency."""
    ev = cfg["params"]["evaluation"]
    jobs = []
    for d in cal_days:
        c = copy.deepcopy(cfg)
        c["params"]["evaluation"]["calibration_days"] = int(d)
        c["params"]["evaluation"]["test_days"] = int(cfg["experiment"]["maturity_test_days"])
        jobs += [(c, int(s)) for s in seeds]
    res = list(map_fn(_maturity_job, [(c, s, run) for c, s in jobs]))
    rows = []
    for d in cal_days:
        got = [r for (c, _), r in zip(jobs, res) if c["params"]["evaluation"]["calibration_days"] == int(d)]
        lat = [v for r in got for v in r["pipelines"]["P2"]["candidate_latencies_min"]]
        det = [v for v in lat if v is not None]
        conf = [v for r in got for v in r["pipelines"]["P2"]["latencies_min"]]
        n_cal = int(d) * 1440 // int(cfg["params"]["qcc"]["bins"])          # scores per node per time-of-day bin
        rows.append({"cal_days": int(d), "n_cal": n_cal, "p_min": 1.0 / (n_cal + 1),   # M26 — conformal floor
                     "candidate_rate": len(det) / len(lat) if lat else None, "candidate_ci95": list(wilson(len(det), len(lat))),
                     "candidate_latency_median_min": float(np.median(det)) if det else None,
                     "confirmed_rate": sum(v is not None for v in conf) / len(conf) if conf else None,
                     "h": [r["pipelines"]["P2"]["h"] for r in got], "fires": len(lat)})
    return {"label": "SIMULATION", "seeds": [int(s) for s in seeds], "test_days": int(cfg["experiment"]["maturity_test_days"]),
            "tuning_days": ev["tuning_days"], "rows": rows}


def _maturity_job(args):
    cfg, seed, run = args
    return run(cfg, seed, ["P2"])


def _windows_job(args):
    return seed_windows(*args)


def run_learning(cfg: dict, out_dir, jobs: int = 1) -> dict:
    """`prahari experiment --preset learning`: learning curve and maturity → results/learning.json, the fitted
    models → results/learning_model_k<K>.json, then summary.json (`report.combine`)."""
    from prahari.eval.report import combine
    ex = cfg["experiment"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in ex["train_seeds"]] + [int(s) for s in ex["seeds"]]
    pool = None
    if jobs > 1:
        import multiprocessing as mp
        pool = mp.get_context("fork").Pool(jobs)
    try:
        mapper = pool.map if pool else map
        per_seed = list(mapper(_windows_job, [(cfg, s) for s in seeds]))
        n_train = len(ex["train_seeds"])
        curve = learning_curve(per_seed[:n_train], per_seed[n_train:], cfg)
        curve["maturity"] = maturity_curve(cfg, ex["maturity_seeds"], ex["maturity_cal_days"], map_fn=mapper)
    finally:
        if pool:
            pool.close()
    for K, model in curve.pop("models").items():
        write_text_atomic(out / f"learning_model_k{K}.json", json.dumps(model, indent=1))
    write_text_atomic(out / "learning.json", json.dumps(curve, indent=1))
    combine(out)
    return curve
