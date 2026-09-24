import json, glob, numpy as np
def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k/n; d = 1+z*z/n; c = p + z*z/(2*n); h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c-h)/d, (c+h)/d)
R70 = [json.load(open(f)) for f in sorted(glob.glob('sim_s*_70.json'))]
Rsp = [json.load(open(f)) for f in sorted(glob.glob('sim_s*_100-150.json'))]
days = 30
print('seeds@70:', [r['seed'] for r in R70], ' test days each', days)
print('\nNODE LEVEL (per node-month)')
for k in ['G_nom','G_slow','G_fast','C_fast','C_slow']:
    a = [r['cand_per_node_month'][k] for r in R70]; b = [r['local_cand_per_node_month'][k] for r in R70]
    print(f'  {k:7s} all {np.mean(a):8.2f}  node-local {np.mean(b):8.2f}  h={np.mean([r["h"][k] for r in R70]):.1f}')
print('  common-mode time frac', np.mean([r['cm_time_frac_test'] for r in R70]))
print('  conformal exceed p<=1e-2 (nominal 0.01):', [round(r['conformal_exceed_1e-2'],4) for r in R70], ' p<=1e-3:', [round(r['conformal_exceed_1e-3'],5) for r in R70])
names = list(R70[0]['by_spacing']['70']['false_incidents_per_month'].keys()) + ['P2_candidate']
print('\nNETWORK LEVEL @70 m (100 nodes)')
print(f'{"config":24s} {"FA/mo":>7s} {"FA total":>8s} {"Pd180":>6s} {"95%CI":>13s} {"Pd30":>5s} {"Pd60":>5s} {"med":>5s} {"p25":>5s} {"p75":>5s} {"PdDry":>6s} {"PdWet":>6s}')
for n in names:
    fa = [r['by_spacing']['70']['false_incidents_per_month'].get(n, np.nan) for r in R70]
    lat = []; dry = []
    for r in R70:
        o = r['by_spacing']['70']; lat += o['detect'][n]; dry += o['fire_dry']
    L = np.array([np.nan if v is None else v for v in lat], float); D = np.array(dry)
    k = np.isfinite(L).sum(); N = len(L); lo, hi = wilson(k, N)
    det = L[np.isfinite(L)]
    fat = np.nansum(fa)/12*1 if False else np.nansum(np.array(fa)*days/30)
    print(f'{n:24s} {np.nanmean(fa):7.2f} {fat:8.0f} {k/N:6.2f} ({lo:.2f}-{hi:.2f}) {np.mean(L<=30):5.2f} {np.mean(L<=60):5.2f} {np.median(det):5.0f} {np.percentile(det,25):5.0f} {np.percentile(det,75):5.0f} {np.isfinite(L[D]).mean():6.2f} {np.isfinite(L[~D]).mean():6.2f}')
print('fires total @70:', N, ' dry:', int(D.sum()))
print('\nOPERATING CURVE (P2_full, 70 m, pooled over seeds)')
for j in range(4):
    rows = [r['by_spacing']['70']['curve'][j] for r in R70]
    rr = rows[0]['r_per_day']; fa = np.mean([x['P2_full']['fa_month'] for x in rows])
    L = np.array([np.nan if v is None else v for x in rows for v in x['P2_full']['lat']], float)
    det = L[np.isfinite(L)]
    print(f'  node target 1 per {1/rr:4.0f} d: h={np.mean([x["P2_full"]["h"] for x in rows]):6.1f} FA/mo {fa:5.2f}  Pd180 {np.isfinite(L).mean():.2f}  Pd60 {np.mean(L<=60):.2f} median {np.median(det):.0f} min')
print('\nSPACING (seeds', [r['seed'] for r in Rsp], ')')
for sp in ['70','100','150']:
    src = [r for r in R70 if r['seed'] in [x['seed'] for x in Rsp]] if sp=='70' else Rsp
    for n in ['P0_fixed','P1_v1_as_written','P2_full','P2_candidate']:
        L = np.array([np.nan if v is None else v for r in src for v in r['by_spacing'][sp]['detect'][n]], float)
        fa = np.mean([r['by_spacing'][sp]['false_incidents_per_month'].get(n, np.nan) for r in src])
        det = L[np.isfinite(L)]
        print(f'  {sp:>3s} m {n:18s} FA/mo {fa:7.2f} Pd180 {np.isfinite(L).mean():.2f} Pd60 {np.mean(L<=60):.2f} median {np.median(det) if len(det) else float("nan"):.0f}  n={len(L)}')
