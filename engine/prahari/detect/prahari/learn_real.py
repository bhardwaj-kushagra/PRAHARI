"""Learning loop — real implementation (SPEC §5.10, M36, Phase 9).

Controlled burns (scripted ignitions) and quiet periods give labelled cluster windows. Each window is described by
f = [X_C, |C|, ln ρ_C, c̄] — Fisher statistic, cluster size, SCMR ratio and mean health weight — and a logistic
regression with an L2 penalty, fitted by iteratively reweighted least squares, estimates P(fire | f). Dividing its
odds by the training odds gives a likelihood ratio that replaces the Sellke–Bayarri–Berger bound in M34 once the
model has seen at least `k_min` burns; below that, and with no model file, the stage keeps the bound.

The fit is done offline by `prahari experiment --preset learning` (`eval/learning.py`), which writes the model file.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from prahari.core.contracts import BayesFactors
from prahari.core.registry import Stage, register
from prahari.detect.prahari.learn import sbb_bound

FEATURES = ("X_C", "size", "ln_rho", "c_bar")
LN_BF_MAX = 690.0                                   # exp(690) ≈ 1e300: the contract keeps BF finite


def window_features(X, size, ratio, c_bar, rho_clip=(1e-3, 1e3)) -> np.ndarray:
    """M36 — f = [X_C, |C|, ln ρ_C, c̄] per cluster window, as a (k, 4) array."""
    X = np.asarray(X, dtype=float)
    k = X.shape[0]
    ratio = np.ones(k) if ratio is None or len(ratio) == 0 else np.asarray(ratio, dtype=float)
    c_bar = np.ones(k) if c_bar is None or len(c_bar) == 0 else np.asarray(c_bar, dtype=float)
    return np.column_stack([X, np.asarray(size, dtype=float), np.log(np.clip(ratio, *rho_clip)), c_bar])


def fit_logistic(F, y, l2: float = 1.0, iters: int = 100, tol: float = 1e-9) -> dict:
    """M36 — logistic regression P(1 | f) with an L2 penalty on the standardised weights (not the intercept),
    fitted by Newton's method (IRLS). A feature with no spread is left at zero weight."""
    F, y = np.asarray(F, dtype=float), np.asarray(y, dtype=float)
    mu = F.mean(axis=0)
    sd = F.std(axis=0)
    sd = np.where(sd > 1e-12, sd, 1.0)
    Z = np.column_stack([np.ones(len(y)), (F - mu) / sd])
    pen = np.full(Z.shape[1], float(l2))
    pen[0] = 0.0
    w = np.zeros(Z.shape[1])
    pi = float(y.mean())
    w[0] = np.log(max(pi, 1e-12) / max(1.0 - pi, 1e-12))
    for it in range(iters):
        p = expit(Z @ w)
        grad = Z.T @ (y - p) - pen * w
        hess = (Z * (p * (1.0 - p))[:, None]).T @ Z + np.diag(pen) + 1e-12 * np.eye(len(w))
        step = np.linalg.solve(hess, grad)
        w += step
        if np.max(np.abs(step)) < tol:
            break
    return {"features": list(FEATURES), "mu": mu.tolist(), "sd": sd.tolist(), "w": w.tolist(), "l2": float(l2),
            "pi_train": pi, "n_pos": int(y.sum()), "n_neg": int(len(y) - y.sum()), "iterations": it + 1}


def ln_lr_hat(model: dict, F) -> np.ndarray:
    """M36 — ln LR̂(f) = logit P(1 | f) − logit π_train (the fitted odds over the training odds)."""
    F = np.atleast_2d(np.asarray(F, dtype=float))
    Z = (F - np.asarray(model["mu"])) / np.asarray(model["sd"])
    w = np.asarray(model["w"])
    eta = w[0] + Z @ w[1:]
    pi = min(max(float(model["pi_train"]), 1e-12), 1.0 - 1e-12)
    return eta - np.log(pi / (1.0 - pi))


def lr_hat(model: dict, F) -> np.ndarray:
    """M36 — LR̂(f), clipped so it stays a finite positive number."""
    return np.exp(np.clip(ln_lr_hat(model, F), -LN_BF_MAX, LN_BF_MAX))


def load_model(path) -> dict | None:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        p = Path(__file__).resolve().parents[4] / path       # relative to the repository root
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


@register("learn", kind="real")
class LearnReal(Stage):
    equation = "M36 (bound below k_min)"
    tag = "DER"
    description = "Fitted likelihood ratio from controlled burns (logistic, L2); the SBB bound until K ≥ k_min"

    def reset(self, ctx) -> None:
        self.model = load_model(self.params.get("model_file"))
        self.k = int(self.model.get("K", 0)) if self.model else 0
        self.fitted = self.model is not None and self.k >= int(self.params["k_min"])   # M36 step 5

    def step(self, inputs, ctx) -> BayesFactors:
        fisher, clusters, scmr, c = inputs if isinstance(inputs, tuple) else (inputs, None, None, None)
        if not self.fitted or clusters is None:
            return BayesFactors(bf=tuple(float(b) for b in sbb_bound(fisher.p_cluster)))
        c_bar = None
        if c is not None:
            cn = np.asarray(c, dtype=float).min(axis=1)
            c_bar = [float(cn[list(m)].mean()) for m in clusters.members]
        F = window_features(fisher.X, [len(m) for m in clusters.members], scmr.ratio if scmr else None, c_bar,
                            tuple(self.params["rho_clip"]))
        return BayesFactors(bf=tuple(float(b) for b in lr_hat(self.model, F)) if len(F) else ())

    def snapshot(self) -> dict:
        return {"model_K": self.k, "fitted_in_use": self.fitted, "k_min": int(self.params["k_min"])}

