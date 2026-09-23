"""
PRAHARI simulation study (SIMULATED results; all model parameters are stated assumptions).
Compares: P0 fixed threshold (abstract-era), P1 v1 (Gaussian-z CUSUM with nominal-ARL h, fixed 2-of-N),
P1t v1 with replay-tuned h, P2 v2 full (conformal + replay-tuned CUSUM + risk-adaptive quorum + spatial
common-mode rejection), plus ablations.
"""
import numpy as np, json, sys, time
from collections import deque
from scipy.signal import lfilter

QUICK = len(sys.argv) > 1 and sys.argv[1] == "quick"
MPD = 1440
import os
D_CAL, D_TUNE, D_TEST = (4, 4, 10) if QUICK else (14, 14, int(os.environ.get('TEST_DAYS', 30)))
T = (D_CAL + D_TUNE + D_TEST) * MPD
CAL = slice(0, D_CAL * MPD)
TUNE = slice(D_CAL * MPD, (D_CAL + D_TUNE) * MPD)
TEST0 = (D_CAL + D_TUNE) * MPD
SIDE = 10; N = SIDE * SIDE
WIN = 30            # quorum window, minutes
REFR = 30           # candidate refractory, minutes
TARGET_R = 1 / 30   # design target: 1 false candidate per node per 30 days
L_DECAY = 40.0      # plume decay length, m (assumption, tuned to ~50 m downwind detection)
Q50 = 2.5           # full-growth downwind signal at 50 m (assumption, ~9x residual sd)

def background(rng):
    t = np.arange(T); tod = (t % MPD) / MPD; day = t // MPD
    ndays = T // MPD
    damp = np.clip(1 + 0.3 * rng.standard_normal(ndays), 0.3, 2.0).astype(np.float32)
    phase = rng.uniform(-0.3, 0.3, N).astype(np.float32)
    diur = (np.sin(2*np.pi*tod[None, :] - np.pi/2 + phase[:, None]) * damp[day][None, :]).astype(np.float32)
    comp = rng.uniform(0.2, 0.4, N).astype(np.float32)[:, None]
    drift = np.cumsum(rng.normal(0, 0.002, (N, T)).astype(np.float32), axis=1)
    drift += (rng.normal(0, 0.5, N) / T).astype(np.float32)[:, None] * t[None, :].astype(np.float32)
    het = (1 + 0.6*np.clip(np.sin(2*np.pi*tod - np.pi/2), 0, None)).astype(np.float32)  # noisier by day
    innov = rng.normal(0, 0.05, (N, T)).astype(np.float32) * het[None, :]
    ar = lfilter([1], [1, -0.95], innov, axis=1).astype(np.float32)
    ht = (0.05 * rng.standard_t(3, (N, T))).astype(np.float32)
    nuis = np.zeros((N, T), np.float32)
    rate = np.where(rng.random(N) < 0.5, 1/MPD, 1/(5*MPD))
    for i in range(N):
        k = rng.poisson(rate[i] * T)
        for s, a, tau in zip(rng.integers(0, T-60, k), np.exp(rng.normal(np.log(1.5), 0.6, k)), rng.uniform(2, 10, k)):
            nuis[i, s:s+60] += a * np.exp(-np.arange(60) / tau)
    reg = np.zeros(T, np.float32)
    for s in rng.integers(0, T-900, rng.poisson(T/(10*MPD))):
        dur = rng.uniform(180, 720); amp = rng.uniform(0.8, 2.5)
        tt = np.arange(int(dur) + 120)
        reg[s:s+len(tt)] += amp * np.clip(np.minimum(tt/60, (dur+120-tt)/60), 0, 1)
    regfac = np.clip(1 + 0.2*rng.standard_normal(N), 0.5, 1.5).astype(np.float32)
    xc = comp*diur; xc += drift; del drift; xc += ar; del ar, innov; xc += ht; del ht
    xc += nuis; del nuis; xc += regfac[:, None]*reg[None, :]
    xr = xc + 0.7*diur; del diur
    return xc, xr, day, (t % MPD)

def geometry(spacing):
    g = np.arange(SIDE) * spacing
    xy = np.array([(a, b) for a in g for b in g], float)
    R = 1.6 * spacing
    dist = np.hypot(xy[:, None, 0]-xy[None, :, 0], xy[:, None, 1]-xy[None, :, 1])
    return xy, dist, R

def inject_fires(rng, xy, daytype):
    """Fires at 6-hour slots in the test period; 80% of dry-day slots, 20% of wet-day slots."""
    fires = []; sig = {}
    qmax_ref = Q50 / np.exp(-50 / L_DECAY)
    for s0 in range(TEST0 + 120, T - 400, 360):
        t0 = s0 + int(rng.integers(0, 60))
        if rng.random() > (0.8 if daytype[t0 // MPD] else 0.2):
            continue
        ign = rng.uniform(0, xy[:, 0].max(), 2)   # uniform inside the deployed grid
        th = rng.uniform(0, 2*np.pi); u = rng.uniform(30, 120)  # m/min
        qmax = qmax_ref * np.exp(rng.normal(0, 0.5))
        v = xy - ign; d = np.hypot(v[:, 0], v[:, 1]) + 1e-6
        cosphi = (v[:, 0]*np.cos(th) + v[:, 1]*np.sin(th)) / d
        hdir = 0.1 + 0.9*((1 + cosphi)/2)**2
        tau = np.arange(180)[None, :] - (d / u)[:, None]
        Q = np.where(tau > 0, qmax*(1 - np.exp(-np.clip(tau, 0, None)/10.0)), 0.0)
        inter = np.exp(rng.normal(0, 0.5, Q.shape) - 0.125)
        sig[t0] = (Q * (np.exp(-d/L_DECAY)*hdir)[:, None] * inter).astype(np.float32)
        fires.append((t0, ign))
    return fires, sig

def add_fires(x, sig):
    y = x.copy()
    for t0, s in sig.items():
        y[:, t0:t0+180] += s
    return y

def ewma_z(x, alpha=1/720, freeze=3.0, fmax=180, lockup_fix=True):
    """EWMA baseline with freeze. lockup_fix=True caps a freeze at fmax minutes, then
    re-baselines with a residual winsorised at +/-freeze*s (v2). False = v1 rule as written."""
    b = x[:, :MPD].mean(1); s2 = x[:, :MPD].var(1) + 1e-4
    z = np.empty_like(x); fz = np.zeros(x.shape[0], np.int32)
    for t in range(x.shape[1]):
        xt = x[:, t]; d = xt - b; s = np.sqrt(s2); zt = d / s; z[:, t] = zt
        u = np.abs(zt) < freeze
        fz = np.where(u, 0, fz + 1)
        if lockup_fix:
            force = fz > fmax
            dw = np.clip(d, -freeze*s, freeze*s)
            u2 = u | force
            b = np.where(u2, b + alpha*dw, b); s2 = np.where(u2, s2 + alpha*(dw*dw - s2), s2)
        else:
            b = np.where(u, b + alpha*d, b); s2 = np.where(u, s2 + alpha*(d*d - s2), s2)
    return z

def conformal_p(z, tod):
    hb = tod // 240; p = np.empty_like(z); cal_idx = np.zeros(T, bool); cal_idx[CAL] = True
    for b in range(6):
        m = hb == b; mc = m & cal_idx
        for i in range(N):
            c = np.sort(z[i, mc]); n = len(c)
            p[i, m] = (1 + n - np.searchsorted(c, z[i, m], side='left')) / (n + 1)
    return p

def cusum(score, k, h, t0=0, t1=None):
    t1 = score.shape[1] if t1 is None else t1
    G = np.zeros(N, np.float32); ref = np.zeros(N, np.int32); out = []
    for t in range(t0, t1):
        G = np.maximum(0, G + score[:, t] - k)
        hit = (G > h) & (ref == 0)
        if hit.any():
            for i in np.nonzero(hit)[0]: out.append((t, int(i)))
            G[hit] = 0; ref[hit] = REFR
        ref = np.maximum(ref - 1, 0)
    return out

def cm_mask(z, frac=0.25, pad=60):
    """Common-mode episodes: >= frac of all nodes elevated (|z|>=3) at once, padded +/- pad min.
    The edge can observe this from the candidate flow; node thresholds are tuned for node-local noise."""
    m = (z >= 3).mean(0) >= frac
    c = np.convolve(m.astype(float), np.ones(2*pad+1), 'same') > 0
    return c

def tune_h(score, k, cm, r=TARGET_R):
    target = r * N * D_TUNE
    lo, hi = 0.5, 400.0
    for _ in range(18):
        mid = 0.5*(lo + hi)
        n = sum(1 for t, i in cusum(score, k, mid, TUNE.start, TUNE.stop) if not cm[t])
        if n > target: lo = mid
        else: hi = mid
    return hi

def confirm(cands, dist, R, daytype, raq, contrast):
    nbr = (dist <= R); nn = nbr.sum(1)
    recent = deque(); alarms = []
    for t, i in cands:
        while recent and recent[0][0] < t - WIN: recent.popleft()
        recent.append((t, i))
        nodes = {j for _, j in recent}
        local = [j for j in nodes if nbr[i, j]]
        k = 2 if (not raq or daytype[t // MPD]) else 3
        if len(local) < k: continue
        if contrast:
            f_loc = len(local) / nn[i]; f_net = len(nodes) / N
            if f_loc / max(f_net, 1/N) < 3.0: continue
        alarms.append((t, i, local))
    return alarms

def incidents(alarms, dist, R, t_from, t_to):
    inc = []  # (t_last, nodes)
    for t, i, loc in alarms:
        if t < t_from or t >= t_to: continue
        for m in inc:
            if t - m[0] <= 60 and min(dist[i, j] for j in m[1]) <= 2*R:
                m[0] = t; m[1].update(loc); break
        else:
            inc.append([t, set(loc)])
    return len(inc)

def p0_alarms(xr, thr, t_from, t_to):
    above = xr[:, t_from:t_to] > thr[:, None]
    out = []
    for i in range(N):
        on = np.flatnonzero(above[i, 1:] & ~above[i, :-1]) + 1 + t_from
        last = -10**9
        for t in on:
            if t - last >= REFR: out.append((int(t), i, [i])); last = t
    out.sort(); return out

def detect(alarms, fires, xy, radius=150.0):
    lat = []
    j = 0; al = sorted(alarms)
    for t0, ign in fires:
        near = None
        for t, i, loc in al:
            if t < t0: continue
            if t > t0 + 180: break
            if any(np.hypot(*(xy[n] - ign)) <= radius for n in loc):
                near = t - t0; break
        lat.append(near)
    return lat

def fast_resid(x, lag0=60, lag1=180):
    """Two-timescale conditioning: detection residual against a lagged 60-180 min window mean."""
    cs = np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(x, axis=1, dtype=np.float64)], axis=1)
    t = np.arange(x.shape[1]); a = np.clip(t - lag1, 0, None); b = np.clip(t - lag0, 1, None)
    base = (cs[:, b] - cs[:, a]) / np.maximum(b - a, 1)
    return (x - base).astype(np.float32)

def gauss_z(r):
    med = np.median(r[:, CAL], axis=1); mad = 1.4826*np.median(np.abs(r[:, CAL] - med[:, None]), axis=1)
    return ((r - med[:, None]) / mad[:, None]).astype(np.float32)

def scores(xc, tod):
    z1 = ewma_z(xc, lockup_fix=False)          # v1 as written
    zs = ewma_z(xc)                            # slow residual, lock-up fixed
    rf = fast_resid(xc)
    zf = gauss_z(rf)                           # fast residual, Gaussian scaling
    pf = conformal_p(rf, tod)                  # fast residual, conformal
    ps = conformal_p(zs, tod)                  # slow residual, conformal
    return {'G_nom': z1, 'G_slow': zs, 'G_fast': zf, 'C_fast': -np.log(pf), 'C_slow': -np.log(ps)}, zs, pf

KS = {'G_nom': 0.5, 'G_slow': 0.5, 'G_fast': 0.5, 'C_fast': 1.5, 'C_slow': 1.5}

def run(seed, spacings=(70.0, 100.0, 150.0), do_curve=True):
    rng = np.random.default_rng(seed)
    xc, xr, day, tod = background(rng)
    daytype = rng.random(T // MPD + 1) < 0.5   # True = dry/busy day
    sc, zs, pf = scores(xc, tod)
    cm = cm_mask(zs)
    H = {'G_nom': 8.8}                         # Siegmund: nominal ARL0 ~ 30 d at k=0.5 for iid N(0,1)
    for k in ['G_slow', 'G_fast', 'C_fast', 'C_slow']:
        H[k] = tune_h(sc[k], KS[k], cm)
    cq = {k: cusum(sc[k], KS[k], H[k], TEST0) for k in H}
    for k in ['G_nom', 'G_fast', 'C_slow']: del sc[k]
    print('quiet pass done', flush=True)
    thr0 = xr[:, :MPD].mean(1) + 3*xr[:, :MPD].std(1)
    res = {'seed': seed, 'h': H,
           'cand_per_node_month': {k: len(v)/N/D_TEST*30 for k, v in cq.items()},
           'local_cand_per_node_month': {k: sum(1 for t, i in v if not cm[t])/N/D_TEST*30 for k, v in cq.items()},
           'cm_time_frac_test': float(cm[TEST0:].mean()),
           'conformal_exceed_1e-2': float((pf[:, TEST0:] <= 1e-2).mean()),
           'conformal_exceed_1e-3': float((pf[:, TEST0:] <= 1e-3).mean()),
           'conformal_floor': float(pf[:, TEST0:].min()),
           'by_spacing': {}}
    configs = {  # name: (candidate source, risk-adaptive quorum, spatial common-mode rejection)
        'P1_v1_as_written': ('G_nom', False, False),
        'P1t_v1_replay_tuned': ('G_slow', False, False),
        'P2_full': ('C_fast', True, True),
        'P2_minus_conformal': ('G_fast', True, True),
        'P2_minus_two_timescale': ('C_slow', True, True),
        'P2_minus_SCMR': ('C_fast', True, False),
        'P2_minus_RAQ': ('C_fast', False, True),
    }
    for sp in spacings:
        xy, dist, R = geometry(sp)
        out = {'false_incidents_per_month': {}}
        out['false_incidents_per_month']['P0_fixed'] = incidents(p0_alarms(xr, thr0, TEST0, T), dist, R, TEST0, T)/D_TEST*30
        for name, (src, raq, con) in configs.items():
            out['false_incidents_per_month'][name] = incidents(confirm(cq[src], dist, R, daytype, raq, con), dist, R, TEST0, T)/D_TEST*30
        frng = np.random.default_rng(seed*100 + int(sp))
        fires, sig = inject_fires(frng, xy, daytype)
        xcf = add_fires(xc, sig); xrf = add_fires(xr, sig)
        scf, _, _ = scores(xcf, tod)
        cf = {k: cusum(scf[k], KS[k], H[k], TEST0) for k in H}
        lat = {'P0_fixed': detect(p0_alarms(xrf, thr0, TEST0, T), fires, xy)}
        for name, (src, raq, con) in configs.items():
            lat[name] = detect(confirm(cf[src], dist, R, daytype, raq, con), fires, xy)
        lat['P2_candidate'] = detect([(t, i, [i]) for t, i in cf['C_fast']], fires, xy)
        if int(sp) == 70 and do_curve:   # operating curve: node false-candidate target vs network outcome
            curve = []
            for rr in [1/60, 1/30, 1/14, 1/7]:
                row = {'r_per_day': rr}
                for src, name in [('C_fast', 'P2_full')]:
                    h = tune_h(sc[src], KS[src], cm, rr)
                    raq, con = (True, True) if name == 'P2_full' else (False, False)
                    fa = incidents(confirm(cusum(sc[src], KS[src], h, TEST0), dist, R, daytype, raq, con), dist, R, TEST0, T)/D_TEST*30
                    lt = detect(confirm(cusum(scf[src], KS[src], h, TEST0), dist, R, daytype, raq, con), fires, xy)
                    row[name] = {'h': h, 'fa_month': fa, 'lat': lt}
                curve.append(row)
            out['curve'] = curve
        del scf, xcf, xrf
        print('spacing', sp, 'done', flush=True)
        out['detect'] = lat; out['n_fires'] = len(fires)
        out['fire_dry'] = [bool(daytype[t0 // MPD]) for t0, _ in fires]
        res['by_spacing'][str(int(sp))] = out
    return res

if __name__ == '__main__':
    if QUICK:
        r = run(11, (70.0,)); json.dump([r], open('/home/claude/sim_results.json', 'w')); print('saved')
    else:
        seed = int(sys.argv[1]); sps = tuple(float(v) for v in sys.argv[2].split(','))
        curve = len(sys.argv) > 3 and sys.argv[3] == 'curve'
        t = time.time(); r = run(seed, sps, curve)
        json.dump(r, open(f'/home/claude/sim_s{seed}_{sys.argv[2].replace(",", "-")}.json', 'w'))
        print(f'seed {seed} spacings {sps} done in {time.time()-t:.0f}s', flush=True)
