"""Offline baselines over recorded readings (protocol R1 §3): P0 (M22), the v1 z series (M23, M24) and the AR(1)
residual chart (R1, R2). The functions reproduce the online stages' arithmetic step for step, so at the configured
knobs they give the same alarms (checked by `tests/unit/test_research_fidelity.py`)."""
from __future__ import annotations

from collections import deque

import numpy as np

from prahari.detect.baselines.fixed import first_day_threshold
from prahari.detect.baselines.v1 import v1_ewma_step
from prahari.detect.baselines.v1t import confirm_step
from prahari.detect.prahari.ttc_real import ttc_slow_step


def p0_alarms(x_raw, n_sigma: float, p: dict) -> list:
    """M22 — rising edges above μ + kσ of the first day, 30-min refractory, alarms after `start_min`.
    Returns alarms (t, node, [node]) in time order, as the online stage emits them."""
    init = int(p["init_min"])
    thr = first_day_threshold(x_raw[:init], n_sigma)                 # M22 — μ_i + kσ_i
    above = x_raw[init:] > thr
    prev = np.vstack([np.zeros((1, above.shape[1]), dtype=bool), above[:-1]])
    edge = above & ~prev
    ref, start = int(p["refractory_min"]), int(p["start_min"])
    out = []
    for i in range(edge.shape[1]):                                    # per node over its (sparse) edge times
        last = -(10 ** 9)
        for t in (np.flatnonzero(edge[:, i]) + init).tolist():
            if t <= start or t - last < ref:
                continue
            last = t
            out.append((t, i, [i]))
    out.sort(key=lambda a: (a[0], a[1]))
    return out


def v1_z(x, p: dict):
    """M23/M24 without the cap (P1): z per tick from `init_min` on (rows before are 0)."""
    init = int(p["init_min"])
    b = x[:init].mean(axis=0)
    s2 = x[:init].var(axis=0) + p["var_floor"]
    alpha, fr = 1.0 / p["slow_tau_min"], p["freeze_z"]
    for row in x[:init]:                                               # day 1 replayed from day-1 statistics
        _, b, s2 = v1_ewma_step(b, s2, row, alpha, fr)
    z = np.zeros_like(x)
    for t in range(init, x.shape[0]):
        z[t], b, s2 = v1_ewma_step(b, s2, x[t], alpha, fr)
    return z


def capped_z(x, p: dict):
    """M24 with the freeze cap (P1t): z per tick from `init_min` on (rows before are 0)."""
    init = int(p["init_min"])
    b = x[:init].mean(axis=0)
    s2 = x[:init].var(axis=0) + p["var_floor"]
    fz = np.zeros(x.shape[1], dtype=np.int64)
    alpha, fr, cap = 1.0 / p["slow_tau_min"], p["freeze_z"], int(p["freeze_cap_min"])
    for row in x[:init]:
        _, b, s2, fz = ttc_slow_step(b, s2, row, fz, alpha, fr, cap)
    z = np.zeros_like(x)
    for t in range(init, x.shape[0]):
        z[t], b, s2, fz = ttc_slow_step(b, s2, x[t], fz, alpha, fr, cap)
    return z


def ar_innovation(z, t0: int, t1: int):
    """R1, R2 — per-node AR(1) coefficient fitted by least squares on z over [t0, t1), and the standardised
    innovation u_t = (z_t − φ z_{t−1}) / σ for every t > t0 (rows up to t0 are 0). Returns (u, φ, σ)."""
    a, b = z[t0 + 1:t1], z[t0:t1 - 1]
    phi = (a * b).sum(axis=0) / np.maximum((b * b).sum(axis=0), 1e-12)   # R1 — φ_i
    e = np.zeros_like(z)
    e[t0 + 1:] = z[t0 + 1:] - phi * z[t0:-1]                             # R2 — innovation
    sd = np.maximum(e[t0 + 1:t1].std(axis=0), 1e-9)
    return e / sd, phi, sd


def confirm(cands: dict, nbr, window: int, quorum: int) -> list:
    """M23 — v1 confirmation over candidates {t: [nodes]} in time order → alarms (t, node, members)."""
    recent: deque = deque()
    out = []
    for t in sorted(cands):
        for i, members in confirm_step(recent, t, cands[t], nbr, window, quorum):
            out.append((t, i, list(members)))
    return out
