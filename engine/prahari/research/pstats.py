"""Statistics of protocol R1 (§3, R4–R8): pooled operating curves, operating-point selection, seed bootstrap, paired
comparisons with Holm's correction, and the partial area under the curve. Pure functions over per-seed rows."""
from __future__ import annotations

import numpy as np
from scipy.stats import wilcoxon

from prahari.eval.stats import per_month


def seed_matrix(rows: list[dict]) -> dict:
    """Per-seed, per-knob counts of one pipeline: false incidents F (S, K), detected D (S, K), fires n (S,),
    test days (S,)."""
    F = np.array([r["false_incidents"] for r in rows], dtype=float)
    D = np.array([[sum(v is not None for v in lat) for lat in r["latencies"]] for r in rows], dtype=float)
    n = np.array([len(r["latencies"][0]) for r in rows], dtype=float)
    days = np.array([r["test_days"] for r in rows], dtype=float)
    return {"F": F, "D": D, "n": n, "days": days, "grid": rows[0]["grid"], "knob": rows[0]["knob"]}


def pooled(m: dict, month_days: float = 30.0) -> dict:
    """Pooled curve: false incidents per month and detection share per knob (R5 point estimates)."""
    fa = m["F"].sum(axis=0) / m["days"].sum() * month_days
    det = m["D"].sum(axis=0) / m["n"].sum()
    return {"fa": fa, "det": det}


def permissive_order(knob: str, K: int) -> list[int]:
    """Grid indices from strictest to most permissive: the target grows permissive, k and h grow strict."""
    return list(range(K)) if knob == "target" else list(range(K - 1, -1, -1))


def select(m: dict, budget: float, month_days: float = 30.0):
    """R4 — the most permissive grid index whose pooled false incidents per month are ≤ budget (None if none is)."""
    fa = pooled(m, month_days)["fa"]
    ok = [j for j in permissive_order(m["knob"], fa.size) if fa[j] <= budget]
    return ok[-1] if ok else None


def resample_weights(n_seeds: int, resamples: int, rng) -> np.ndarray:
    """R5 — seed bootstrap as weights (B, S): how often each seed is drawn in each resample."""
    idx = rng.integers(0, n_seeds, size=(resamples, n_seeds))
    W = np.zeros((resamples, n_seeds))
    np.add.at(W, (np.repeat(np.arange(resamples), n_seeds), idx.ravel()), 1.0)
    return W


def boot_curve(m: dict, W: np.ndarray, month_days: float = 30.0) -> dict:
    """R5 — 95% percentile intervals of the pooled false-incident rate and detection share at every knob."""
    fa = (W @ m["F"]) / (W @ m["days"])[:, None] * month_days
    det = (W @ m["D"]) / (W @ m["n"])[:, None]
    q = lambda a: np.percentile(a, [2.5, 97.5], axis=0).T                        # noqa: E731
    return {"fa_ci": q(fa), "det_ci": q(det)}


def interp_det(fa, det, x: float):
    """R8 interpolation — detection at false-incident rate x, linear in log₁₀ FA over the curve sorted by FA; 0 below
    the lowest achieved FA (not reachable), the last value above the highest."""
    fa, det = np.asarray(fa, float), np.asarray(det, float)
    order = np.argsort(fa, kind="stable")
    f, d = fa[order], det[order]
    pos = f > 0
    if x < f.min():
        return 0.0
    if not pos.any():
        return float(d[-1])
    lf = np.log10(np.where(pos, f, f[pos].min()))
    return float(np.interp(np.log10(x), lf, d))


def pauc(fa, det, lo: float, hi: float, points: int = 400) -> float:
    """R8 — partial AUC of detection against log₁₀ FA over [lo, hi], normalised to [0, 1]."""
    xs = np.logspace(np.log10(lo), np.log10(hi), points)
    ys = np.array([interp_det(fa, det, x) for x in xs])
    return float(np.trapezoid(ys, np.log10(xs)) / (np.log10(hi) - np.log10(lo)))


def per_seed_det(m: dict, j: int) -> np.ndarray:
    """Detection share per seed at knob index j (seeds without fires give NaN)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return m["D"][:, j] / m["n"]


def paired(a: np.ndarray, b: np.ndarray, W: np.ndarray) -> dict:
    """R6 — per-seed differences a − b: mean with its paired-bootstrap interval, and Wilcoxon signed-rank."""
    d = a - b
    ok = ~np.isnan(d)
    d, Wk = d[ok], W[:, ok]
    boot = (Wk @ d) / Wk.sum(axis=1)
    nz = d[d != 0]
    p = float(wilcoxon(d, zero_method="wilcox").pvalue) if nz.size else 1.0
    return {"mean_diff": float(d.mean()), "ci95": np.percentile(boot, [2.5, 97.5]).tolist(), "p_wilcoxon": p,
            "n_seeds": int(d.size), "wins": int((d > 0).sum()), "losses": int((d < 0).sum())}


def holm(pvals: dict, alpha: float = 0.05) -> dict:
    """R7 — Holm step-down: adjusted p-values and rejections, keyed as the input."""
    keys = sorted(pvals, key=lambda k: pvals[k])
    m, running, out = len(keys), 0.0, {}
    for i, k in enumerate(keys):
        running = max(running, min(1.0, (m - i) * pvals[k]))
        out[k] = {"p": pvals[k], "p_holm": running, "reject": running <= alpha}
    return out


def fa_intervals(m: dict, j: int, W: np.ndarray, month_days: float = 30.0) -> dict:
    """False incidents at knob j: pooled rate, exact Poisson interval (M45) and seed-bootstrap interval (R5)."""
    k, days = int(m["F"][:, j].sum()), float(m["days"].sum())
    boot = (W @ m["F"][:, j]) / (W @ m["days"]) * month_days
    return {**per_month(k, days, month_days), "ci95_bootstrap": np.percentile(boot, [2.5, 97.5]).tolist()}


def time_to_confirm(rows: list[dict], j: int, step: int = 5, horizon: int = 180) -> dict:
    """Share of fires confirmed by each minute 0…horizon at knob index j (pooled over seeds)."""
    lat = [v for r in rows for v in r["latencies"][j]]
    mins = list(range(0, horizon + 1, step))
    n = len(lat)
    return {"minutes": mins, "share": [sum(v is not None and v <= t for v in lat) / n if n else None for t in mins]}
