# Research protocol R2 — common-mode handling and the false-alarm floor

**Status: REGISTERED on 30 Sep 2026**, after the developer's review and approval, and before any R2 seed was run
(charter rule 1). §10 records the implementation details fixed at registration. Any change from here on is a logged
deviation in `DECISIONS.md`.

**Configuration:** [`configs/research/r2.yaml`](../../configs/research/r2.yaml). **Code:** `python -m prahari.research
r2-run | r2-analyse | r2-figures` (`engine/prahari/research/*_r2.py`, `edge2.py`, `gate.py`, `mei.py`; M20b in
`engine/prahari/sensors/haze.py`).

**Scope.** Simulation, with real-data anchors where they exist ([realdata.md](realdata.md)). Every number R2 produces
is labelled **SIM**.

**Why R2.** R1 found three things:

- P2 (PRAHARI with SCMR) cannot go below about 5 false incidents a month.
- The floor disappears without haze and grows with it.
- Median subtraction outperforms SCMR, but only when every node sees the haze alike.

R2 asks which common-mode strategy holds up when haze is realistic: uneven, patchy and moving. It also asks how large
the floor is under each.

## 1. Questions

1. **Floor.** Under realistic haze, what is each common-mode strategy's lowest achievable network false-incident rate,
   and how much of it happens inside haze?
2. **Detection at a common budget.** At a false-alarm budget every compared method can meet, how many fires within
   3 h does each confirm?
3. **Where each breaks.** Across synchronous, uneven and narrow-patch haze, which strategy fails first, and how?

## 2. Data-generating scenarios

Everything not listed below is R1's golden configuration: release-1.0 models, 100 nodes at 70 m, the legacy plume,
and the M46 protocol (14 d calibration, 14 d tuning, 30 d test).

Haze episodes keep M20's rate (1 per 10 days), duration U(180, 720) min, amplitude U(0.8, 2.5) su and 60-minute
ramps. What changes is **how each node sees an episode**, through the new haze model M20b:

h_i(t) = g_i · u_i,e · c_i,e · A_e · trapezoid(t − t_e − δ_i,e)

- **gᵢ, the node gain:**
  - a spatially correlated field: gᵢ = clip(1 + σ_g (ρ_s Zᵢ + √(1−ρ_s²) εᵢ), 0.3, 2.0);
  - Z is a Gaussian field over node positions with correlation length L = 200 m (ASM), with ρ_s = 0.7 (ASM);
  - ε is independent N(0, 1).
- **u_i,e, per-episode unevenness:** u_i,e = exp(s_e η_i,e − s_e²/2), with η ~ N(0, 1) and s_e ~ U(0.1, 0.6) (DATA).
  This gives an across-node CV of about 0.1–0.66, covering the event-to-event amplitude spread of the real networks
  (Stuttgart median 0.42; N5 unattributed 0.25–0.34). Stuttgart's most extreme event (CV 2.49) lies outside it.
- **Episode start time:** a start falls between 20:00 and 08:00 local with probability 0.7 (DATA: 7 of 10 real
  unattributed events, 1 of 3 in N5 and 6 of 7 in Stuttgart), uniformly within the chosen window. The rate stays 1 per
  10 days.
- **c_i,e, the coverage of episode e:**
  - a swath of width W_e = f_e × 630 m (the network width), random orientation and offset, with soft edges (20 m);
  - nodes outside the swath see a floor of 0.1;
  - f_e = 1 means the whole network.
- **δ_i,e, the arrival delay:** the node's position along a random direction θ_e divided by the front speed v_e,
  shifted so that the first node has zero delay. A per-node jitter U(0, J_e) is added, with J_e ~ U(0, 60) min (DATA:
  onsets spread 15–140 min, median 40, across a 1.7 km network; its size at 70 m is ASM).

| Scenario | Role | Gain spread σ_g | Coverage f_e | Front speed v_e | Seeds |
| --- | --- | --- | --- | --- | --- |
| **H-mix (primary)** | confirmatory | 0.3 (DATA) | 1 with p 0.5; else U(0.3, 1.0) (DATA) | U(1, 6) m/s (DATA) | selection 1901–1920, test 2001–2100 |
| H-sync | continuity with R1 (no unevenness, jitter or night weighting) | 0.2, uncorrelated | 1 | ∞ (synchronous) | test 2101–2150 |
| H-gain | where median subtraction breaks | 0.4 | 1 | U(1, 6) m/s | test 2151–2200 |
| H-patch | where SCMR and medians break | 0.3 | U(0.2, 0.5) | U(1, 6) m/s | test 2201–2250 |
| H-mix, Gaussian plume | plume-conditional detection | as H-mix | as H-mix | as H-mix | test 2251–2300 |

H-sync reproduces R1's haze model exactly, which is a fidelity check. The `DATA` ranges and their conversion to 70 m
are in §7.

## 3. Methods

All PRAHARI variants share R1's node layer (M24–M28) and edge (M30–M34, legacy RAQ quorum). RAQ is stated plainly as a
prior-dependent quorum (2 on dry days, 3 on wet); with one p-value per candidate, the Fisher combination is a count.

| Id | Common-mode handling | Knobs |
| --- | --- | --- |
| P2 | SCMR: hold a cluster unless its local candidate share is at least ρ times the network share (M31) | r × ρ, with ρ ∈ {0 (off), 1.5, 2, 3, 4, 6, 10} |
| P2-med | node input x − median over nodes (R3) | r |
| P2-medSCMR | median input and SCMR (hybrid) | r × ρ |
| P2-factor | one-factor gain-weighted reference (R9) | r |
| P2-gate | evidence gate (R10): hold alarms while the share of nodes with p ≤ 0.01 in the last 30 min is at least θ | r × θ, with θ ∈ {0.05, 0.1, 0.15, 0.2, 0.3, 0.5, off} |
| Mei | sum of local CUSUMs on −ln p (R11), no common-mode handling | h_M |
| Mei-med | Mei on the median-referenced evidence | h_M |
| AR | R1's AR(1) residual chart, for context | r |

**Grids:**

- r uses R1's target grid {0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 4.3, 6, 10}, with h replay-tuned per seed as in R1.
- h_M ∈ {20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500}.

**New equations:**

- **R9 — one-factor reference.**
  - On the calibration days, over the minutes when at least 25% of nodes have slow z ≥ 3 (M28's common-mode minutes),
    fit ĝᵢ by least squares of dᵢ(t) on m(t) = median_j d_j(t), where d = x − b is the deviation from the slow
    baseline (M24). ĝᵢ is clipped to [0.2, 3]; it is 1 if there are fewer than 120 such minutes.
  - The node input is then x̃ᵢ = xᵢ − ĝᵢ · median_j(d_j / ĝ_j).
- **R10 — evidence share.** e(t) = the share of nodes whose M26 p-value was ≤ 0.01 at least once in (t − 30 min, t].
  An alarm at t is held when e(t) ≥ θ.
- **R11 — Mei's procedure** (Mei 2010, sum of local CUSUMs).
  - Wᵢ ← max(0, Wᵢ − ln pᵢ − k), with k = 1.5; S = Σᵢ Wᵢ.
  - An alarm fires when S > h_M. The alarm's node is argmax Wᵢ; its members are the nodes with Wᵢ ≥ ½ max W.
  - Then all Wᵢ reset to 0, followed by a 30-minute refractory period.

## 4. Operating points

- **Selection:** made on the selection seeds of H-mix only.
- **Budget B*:** the smallest of {1, 3, 10, 30} false incidents a month that every compared method reaches there.
- **Operating point:** for each method, the knob (or knob pair) with the highest pooled detection whose pooled false
  incidents are ≤ B*. This is the Pareto point.
- **Floor knob:** the knob (pair) with the lowest pooled false incidents on the selection seeds.
- **Secondary scenarios:**
  - *deployment view:* the knobs are those chosen on H-mix;
  - *equal-false-alarm view:* each scenario's own curve is interpolated at B* (R8's rule).

## 5. Endpoints and tests

**Primary scenario (H-mix, test seeds 2001–2100):**

- **E1, the false-alarm floor:** each method's pooled false incidents per month at its floor knob, with a seed-bootstrap
  interval (R5).
- **E2, detection at B*:** confirmed within 3 h at each method's operating point, with a paired seed-bootstrap
  interval.
- **E3, decomposition:** at the floor knob, false incidents starting inside haze (an episode active at the first alarm)
  and outside, plus the padded variant (R2-10's tags).
- **E4, AMOC curves:** the mean time to confirmation (a miss counts as 180 min) against false incidents per month, over
  each method's knob grid.
- **E5, haze overlap:** detection at B* for fires whose first 3 h overlap haze, and for the others.

**Hypotheses (Holm within each family, α 0.05, two-sided Wilcoxon on per-seed values):**

- **Family F (floor):** P2-med, P2-medSCMR, P2-factor and P2-gate each differ from P2 in per-seed false incidents at
  their floor knobs.
- **Family D (detection):** P2-med, P2-medSCMR, P2-factor, P2-gate, Mei and Mei-med each differ from P2 in per-seed
  detection at B*.

**Descriptive only:** every secondary scenario, the AMOC curves, E3 and E5.

Every comparison is reported, whatever its outcome. No model, grid, budget or seed changes after the first R2 result
file.

## 6. Records

Each seed file keeps, per method and knob:

- false-incident counts, their first-alarm minutes and every fire's latency;
- for the haze: its episodes, each episode's type, coverage, direction and speed, and each fire's overlap with haze.

This makes E3 and E5 reproducible without re-running.

## 7. Values taken from real data (`DATA`, with their conversion)

The values below come from the N5 networks (`results/research/real_thompson2026.json`) and the Stuttgart network
(`results/research/real_sensorcommunity_stuttgart.json`). They are copied into `configs/research/r2.yaml` with their
source keys.

- **Amplitude spread across stations in unattributed events:** CV 0.25–0.34 (N5).
  - Gain spread σ_g = 0.3 for H-mix. H-gain's 0.4 is above what the real events show; it is kept as the stress case
    from R1's sweep.
- **Share of stations involved:** 0.5–1.0 (N5).
  - H-mix draws partial coverage U(0.3, 1.0) half the time. H-patch's U(0.2, 0.5) is below the observed range (the
    stress case).
- **Onset spread:** 5–35 min over networks of about 1.7–6.4 km median spacing (N5), an apparent front speed of about
  1–6 m/s.
  - At 630 m this means arrival delays of about 2–10 minutes: near-synchronous.
  - Converting km-scale spreads to 70 m assumes a constant front speed (ASM).
- **Sub-kilometre network (Stuttgart; 9 sensors, median spacing 1.7 km):** 7 events in 31 days (0.23 per day); six of
  seven start at night; onsets spread 15–140 min (median 40); amplitude CV 0.18–2.49 (median 0.42); 67–89% of
  stations involved.
  - These contradict the "near-synchronous, even" reading of the N5 events, so the ranges were **widened** before
    registration: per-node onset jitter J_e, per-episode unevenness s_e, and night-weighted starts.
  - The episode rate stays at R1's 1 per 10 days. Stuttgart's 0.23 per day is urban PM, not wildfire smoke; the rate
    is swept in R1 already, as the dose–response.

## 8. Compute and records

About 320 seed-runs, with three node-layer variants each (main, median, factor): roughly 12–14 hours on 4 processes.
Runs are resumable, and each seed file is written atomically and deterministically.

**Outputs:**

- `results/research/r2_*.json`;
- figures: the floor bars with their decomposition, Pareto and AMOC curves, and a scenario panel;
- `docs/research/results-r2.md` and entries in `docs/research/numbers.md`.

## 9. Implementation checks before registration (no protocol seed used)

- **H-sync fidelity:** with the default haze form, H-sync gives R1's haze bytes, and R1's per-seed results reproduce on
  development seed 11.
- **Fast replay:** the two-knob replay (cluster ratio and quorum computed once, then thresholded) equals the registered
  edge stages at every ρ on a short run.
- **Unit tests:** reference values for R9, R10 and R11 and for the M20b haze geometry (delays, swath coverage, gain
  field).

## 10. Fixed at registration (implementation details the draft left open)

None of these changes a scenario, method, grid, seed, budget or endpoint. Each is how the draft's text is implemented.

1. **M20b randomness.** M20b draws from the `haze` stream, which no other module reads. The default form (`m20`)
   draws exactly as release 1.0; a test pins 40 days of its output to a reference hash.
2. **Night weighting.** "Night" is 20:00–08:00 of simulated time (minute of day; runs start at 00:00). The start rate
   is multiplied by 0.7/0.5 at night and 0.3/0.5 by day, so the mean rate stays 1 per 10 days.
3. **Swath and delays.**
   - The swath centre is uniform over the nodes' span along the swath's normal. The edges are linear over 20 m.
   - Every node's delay is its front delay plus its jitter, so the first node to see an episode need not be at zero.
4. **Haze level for E3 and E5.** An episode counts as active from its start until the last node's trapezoid ends
   (the per-minute level is Σ_e A_e · max_i trapezoid(t − t_e − δ_i,e)).
5. **R9 timing.**
   - ĝ ≡ 1 during the calibration days, so the input there is x − median(x − b).
   - ĝ is fitted once, at the end of the calibration days, and then held fixed.
   - b is the main node layer's M24 slow baseline.
6. **P2-gate** is the main node layer with SCMR off, plus the R10 gate. θ = off is P2 with SCMR off.
7. **R11 refractory.** After a Mei alarm all Wᵢ reset to 0. For 30 minutes no alarm can fire, but the statistics keep
   accumulating, as the node CUSUM (M28) does.
8. **ρ grid.** P2 and P2-medSCMR share the grid {0, 1.5, 2, 3, 4, 6, 10}; ρ = 0 means SCMR off. R1's P2 is ρ = 3.
9. **B*.** B* is set by P2 and the six family-D methods. AR is reported at B* if it reaches it.
10. **Selection rules on the pooled selection seeds (H-mix):**
    - **Floor knob:** the lowest false incidents; ties go to the higher detection, then to the first cell in grid
      order.
    - **Operating point at B*:** the highest detection among cells with false incidents ≤ B*; ties go to the lower
      false incidents, then to the first cell.
11. **Fast replay guards.** The two-knob replay refuses anything other than the legacy RAQ quorum, the Bayes-factor
    stub, the real SCMR and no lightning relaxation. All of these hold in golden.
12. **Implementation checks (§9), all passed before registration** (`engine/tests/unit/test_research_r2.py`, no
    protocol seed used):
    - the fast replay equals the registered edge stages at every ρ on development seed 11;
    - with the release haze, R2's P2 at ρ = 3, its P2-med and its AR equal R1's rows on seed 11 (short protocol);
    - reference values for M20b's geometry, the gain-field correlation, R9, R10 and R11.
