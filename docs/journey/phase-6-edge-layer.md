# Phase 6 — PRAHARI edge layer, evidence trace and live mode

## Goal

Complete the decision core: turn node candidates into alarms the way the design intends — group nearby candidates,
reject network-wide events, combine evidence, weigh it against how likely a fire is today, and escalate — with an
explanation for every alarm. Add a live connection to the engine so the dashboard can watch a run as it happens and
switch mechanisms on the fly, while replay stays the default.

## What was built

- **Edge stages** (real, beside the untouched stubs):
  - `edge_real.py` — clustering (M30; default "legacy" form, advanced "components" form), SCMR (M31), Fisher (M32);
  - `decide_real.py` — legacy day-type prior (M33, new `srp` random stream, per-day overrides) and the risk-adaptive
    quorum (M34; legacy 2/3 quorum by default, Bayes form selectable);
  - `escalate_real.py` — incident ladder WATCH → CANDIDATE → CONFIRMED → ESCALATED (M35).
- **Pipeline**: `step_edge` shared by recordings and the experiment harness; traces record the rule that decided, the
  incident and the triggering node; `Simulation.switch_module` for live switching.
- **Harness**: pipeline P2 (node + edge layers), sharing the protocol's day types with the prior.
- **Server** (`server/`): FastAPI with `GET /scenarios`, `POST /run`, `GET /health`, `POST /modules` and WebSocket
  `/frames`, streaming exactly the recording's line format.
- **Dashboard**: `LiveSource` and the Live engine panel; "Why this alarm" (View 3) with the escalation ladder, SCMR
  gauge, Fisher evidence, prior and Bayes bar; mechanism switches with live counters (View 5), using pre-recorded
  variants in replay.
- **Scenarios**: `node_mature` now has a dry, busy day 31; new variant `node_mature__scmr-stub`.

## How it works

For each new candidate (legacy form, as the report's simulation): take the candidates of the last 30 minutes within R
of it; require the local share of candidate nodes to be at least 3× the network's (SCMR); combine the members'
candidate p-values (each ≈ 6.9 × 10⁻⁴) with Fisher's method; turn p_C into a Bayes-factor bound and multiply by the
day's prior odds; alarm when the posterior odds beat the cost ratio 0.01 — which works out as 2 agreeing nodes on a
dry, busy day and 3 on a wet, quiet day. Alarms are tracked as incidents that climb the escalation ladder. Every
decision writes a trace; the "why" panel draws only from it. See [../guide/02-background.md](../guide/02-background.md).

## Challenges and issues

1. **Two readings of the edge.** The SPEC's M30/M31 describe connected components and a cluster neighbourhood; the
   report's simulation decides per candidate around the triggering node. Which is "right" for the golden numbers?
2. **Where do candidate p-values come from?** M32 says p_i ≈ r·ΔT, not the node's instantaneous QCC p-value.
3. **A new optional contract field broke the stubs.** The runner's per-cluster length check rejected the stub's empty
   `incident` field and degraded the escalation module in every stub run.
4. **Day types must agree** between the protocol's fire probabilities and the prior's quorum.
5. **The demo fire went unconfirmed** when day 31 drew "wet, quiet" (three nodes needed).
6. **P2 missed the report's intervals**: false alarms 3.4 per month (report 4.4–9.0) and detection 75.9% (79–87%).
7. **Live mode across threads**: pacing, module switches mid-run, late-joining clients, stopping cleanly.

## Decisions and trade-offs

| Decision | Pros | Cons | Ids |
| --- | --- | --- | --- |
| Legacy form by default; M30 components as an option | golden-comparable; exactly the report's rule (unit-tested) | per-candidate clusters overlap | P6-2, N-b |
| Candidate p-value r·W for Fisher | makes the legacy and Bayes forms agree, as the SPEC's worked example | Fisher then depends on cluster size only | P6-3 |
| Contracts declare optional fields (`OPTIONAL`) | stubs stay valid without edits | one more convention | P6-7 |
| New `srp` stream + per-day overrides; harness shares its calendar | reproducible, consistent day types | day types independent of weather (legacy assumption) | P6-5 |
| Day 31 of `node_mature` set to dry, busy | the storyboard's condition, stated in the file | a scripted condition in a demo scenario | P6-10 |
| Live stream = recording lines; LiveView wraps RecordingSource | every view works unchanged; one parser | a new view object per update (cheap) | P6-8 |
| Replay switches use pre-recorded variants; one variant shipped | offline demo of the key moment | other switches only live | P6-9 |
| Do not change the accepted plume stub to chase the P2 numbers | rule 4 respected; the finding is documented | P2 detection stays below the report for now | P6-11 |

## Resolution

- 1–2: implemented the report's form as default, verified alarm for alarm against its `confirm`; the SPEC's form is
  available. Acceptance 2 (legacy and Bayes agree: 2 dry, 3 wet) passes.
- 3: `Decision.OPTIONAL` plus `dataclasses.fields` in the length check; all stub, off and real runs pass without
  degradation.
- 4: the harness writes its day types into the prior's overrides.
- 5: day 31 set to dry, busy; the fire is confirmed 134 minutes after ignition by nodes 31 and 41. On the haze day,
  SCMR leaves 3 alerts; the SCMR-off variant shows 15 (SIM).
- 6: investigated, not tuned (full detail in `DECISIONS.md` P6-11):
  - our node and edge code gives the report simulation's exact result on its own data (54/63 fires, h 238.13);
  - over 20 seeds, false alarms agree (6.25 vs 7.20 per month, p 0.48), detection differs (74.0% vs 82.2%, p 0.03);
  - about half the detection gap is sampling (more haze in the engine seeds' calibration and tuning days), about half
    is fire transport (continuous weather wind vs a constant random wind per injected fire, +3.5 points when the
    report's fires are used);
  - proposal pending approval: a legacy per-fire wind option for the golden preset. Logged in `KNOWN_ISSUES.md`.
- 7: a background thread with a line buffer; switches applied between recorded frames; clients replay the buffer from
  the start; stop via an event. Tested with FastAPI's test client and in the browser.

## Acceptance results

| # | Test | Result (SIM) |
| --- | --- | --- |
| 1 | P2 reproduces the report within intervals (legacy mode) | **miss**: 3.4 (2.0–5.4) false incidents/month vs 6.4 (4.4–9.0); 75.9% vs 83% (79–87). False alarms equivalent to the report simulation over 20 seeds; detection 8 points lower, diagnosed (see above) |
| 2 | Legacy and Bayes RAQ agree on the worked example | **pass**: 2 nodes on dry days (posterior 0.42 ≥ 0.01), 3 on wet days |
| 3 | Every alert has a complete trace | **pass**: every alert's trace holds SCMR, Fisher, prior, Bayes, incident, anchor and the explanation, with the real methods named |
| 4 | Dashboard works in replay and live mode | **pass**: replay (why panel, SCMR variant keeps the clock, 3 → 15 alarms) and live (frames stream at ×3600, a module switch applied mid-run), no console errors |
| — | Reference values | Fisher 7.4e-6 (2 × 6.9e-4) and 8.6e-8 (3 ×); SBB bound 100 at 4.8e-4 and 1e4 at 2.9e-6 |
| — | Suite | 146 engine tests (6 golden skipped unless enabled), 33 dashboard tests |

P0, P1 and P1t are unchanged from Phases 4–5.

## What to show

`node_mature`, *Alerts* tab: the "Why this alarm" panel for the day-31 fire; then day 30 at 14:00 and the SCMR switch
(3 → 15 alarms). With the server running: *Live engine* ▸ *Scenarios* ▸ `node_3day` ▸ *Start* and switch SCMR live.
