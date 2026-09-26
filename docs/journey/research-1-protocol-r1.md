# Research track R1 — equal-false-alarm evaluation for the paper

## Goal

Turn the simulator's results into evidence a conference paper can stand on. That meant:

- comparing pipelines **at the same false-alarm rate**;
- using fresh, pre-registered seeds;
- including the baselines reviewers expect;
- testing how much the results depend on the simulator's assumed parameters.

The scope is simulation only, at the developer's request; field experiments are a later, separate study. The work is
additive: release 1.0's models, parameters and recordings stay as they are.

## What was built

- **The protocol** ([docs/research/protocol.md](../research/protocol.md)), committed before any run. It fixes:
  - the seeds: selection 901–920, test 1001–1100, sweeps 1001–1010;
  - every pipeline's knob grid;
  - the budgets (1, 3 and 10 false incidents a month) and the endpoints;
  - the tests (paired Wilcoxon with Holm, seed bootstrap, partial AUC);
  - the sensitivity sweeps.
- **`engine/prahari/research/`**, run as `python -m prahari.research`:

| File | What it does |
| --- | --- |
| `record.py` | One recording pass per seed and pass type. It keeps the readings and every node-layer variant's CUSUM input. Each variant is a second `Simulation` whose node stages run on the same readings |
| `baselines.py` | Offline P0 (M22), the v1 z series (M23, M24), the AR(1) innovation (R1, R2) and the v1 confirmation |
| `cusum.py` | Batched CUSUM replay and bisection over many thresholds at once, bitwise equal to `cusum_replay` / `tune_h` |
| `operating.py` | Every pipeline over its knob grid, scored with the release-1.0 M46 functions. PRAHARI variants go through the registered edge stages |
| `pstats.py`, `analysis.py` | Selection (R4), bootstrap (R5), paired tests (R6, R7), pAUC (R8) and the four `results/research/r1_*.json` files |
| `figures.py` | The paper figures (optional matplotlib), built only from those files |

- **New comparators.** Three baselines reviewers would ask for: an AR(1) residual chart (the classical answer to
  autocorrelation), network-median subtraction (the obvious rival to SCMR) and a fixed quorum of 3. Plus a wrong-prior
  test for RAQ.

## How it works

1. Each seed runs the M46 protocol once in a quiet pass and once in a fire pass, recording arrays instead of
   alarms.
2. Offline, each pipeline is replayed at every knob value. For target knobs, h is replay-tuned per seed on its own
   tuning days (M28), with the bisection bracket raised to 5,000.
3. Operating points are chosen on the selection seeds, as the most permissive knob whose pooled false incidents are
   within the budget.
4. Every reported number comes from the test seeds. Comparisons are paired by seed, because each seed is one world
   shared by every pipeline.

## Fidelity: the offline replay equals the online harness

At the configured knobs every offline pipeline reproduces `run_seed` exactly: false incidents and every fire's
latency, for P0, P1, P1t, P2, P2-SCMR, P2-RAQ, P2-QCC and P2-TTC.

- **Unit test:** a short protocol and 36 nodes (`tests/unit/test_research_fidelity.py`).
- **Full-length check:** golden seed 11 against the committed `golden_seed11.json` and `ablation_seed11.json`. It
  matched: 299, 139, 14, 5, 7, 5, 13 and 16 false incidents, with identical latencies.

## Challenges and issues

1. **A release test loaded every YAML under `configs/`.** The protocol's `configs/research/r1.yaml` is not a
   simulation configuration.
   - *Resolution:* the test now skips `research/` as it already skipped `regimes/` (R2-6).
2. **A waiting loop never started the test stage.** It checked for the selection process by name, and `pgrep -f`
   matched the loop's own command line.
   - *Resolution:* found after the selection stage ended. The loop was stopped and the test stage started by hand. No
     result was affected.
3. **The sweep process stopped** when the session went idle, with 52 of 200 files written.
   - *Resolution:* restarted on four processes. The runner keeps existing files, and every file is deterministic, so
     the resumed set is identical to an uninterrupted one.
4. **The selection seeds showed that P2 cannot reach the budgets of 1 or 3 a month**, and that the median-subtraction
   ablation can.
   - *Resolution:* the pre-registered rule applies, so those comparisons are reported as "not reachable". P2-med was
     added to the sweeps (deviation R2-7, decided before any test seed ran). The false-incident floor is logged in
     `KNOWN_ISSUES.md` as a research item.
5. **The 200 m spacing point was invalid.** Ten nodes at 200 m exceed the 1,400 m landscape; the layout check
   failed, and siting fell back to a 70 m grid. The runs looked implausible (93% detection against 23% at 150 m), which
   is how it was caught.
   - *Resolution:* the point is excluded, with its reason in `r1_sweeps.json`. Seed outputs now list degraded modules,
     and the other points were checked (R2-9).
6. **Deciding which budget to plot.**
   - *Resolution:* the budget figures use 10 a month, the smallest pre-registered budget P2 reaches. All budgets are
     in `r1_analysis.json` and on the results page (R2-8).

## Decisions and trade-offs

| Decision | Pros | Cons | Ids |
| --- | --- | --- | --- |
| Pre-register, then report whatever comes out | Credible either way; no seed or knob hunting | The headline budget turned out unreachable for P2 | R2-2 |
| Offline replay from one recording pass | Every knob and variant for about 8 min per seed; exact fidelity is testable | Memory: about 1.3 GB per seed in flight | R2-1 |
| Paired seeds and bootstrap intervals, not only Poisson intervals | Honest about overdispersion between seeds | More computation | protocol R5–R7 |
| Add P2-med to the sweeps after the selection seeds | Tests the variant the evidence points to | A deviation, logged | R2-7 |

## Results (SIM, test seeds 1001–1100)

Details: [docs/research/results-r1.md](../research/results-r1.md).

- **Budgets:** P2 cannot reach 1 or 3 false incidents a month; its floor is 5.07. P2-med reaches 3 a month with
  66.0% of fires confirmed.
- **At 10 a month:**
  - P2 confirms 83.3% within 3 h;
  - the baselines: fixed threshold 46.2%, AR(1) chart 50.6%, replay-tuned v1 31.7%;
  - all three differences hold with Holm p ≤ 1.2e-15.
- **Ablations at 10 a month:**
  - without SCMR 65.9%; fixed quorum 2 74.2%; Gaussian z 69.6%; slow z 44.2%;
  - fixed quorum 3 86.2%, not significantly different from P2;
  - **median subtraction 92.1%, significantly better than P2.**
- **Wrong prior:** 10, 20 and 30% of days mislabelled give 81.9, 80.8 and 79.7%.
- **Sweeps** (10 seeds per point; 200 m excluded, R2-9):
  - at ×3 haze P2 cannot reach 10 a month, while P2-med keeps 72%;
  - at node-gain spread 0.4, P2-med falls to 65.8%, below P2 (81.5%);
  - the Gaussian plume halves every pipeline's detection;
  - the ranking against the AR chart holds everywhere.

## Acceptance

- Engine tests pass, including 11 new research tests.
- `scripts/check_all.sh` regenerates all 20 recordings byte for byte: release 1.0 is untouched.
- `r1_analysis.json` regenerates identically.

## What to show

- **Figure f2** (operating curves): P2 and P2-med well to the upper left of every baseline, and P2's curve stopping at
  about 5 false incidents a month.
- **Figure f4:** every ablation except the quorum rule costs detection, and median subtraction gains.
- **Figure f5:** the haze and gain-spread panels, where the two common-mode defences fail in opposite conditions.
