# 6. Demo walkthrough

A route through the dashboard for a 3–5 minute explanation, as of Phase 6. The final conference storyboard is in
SPEC §11 and will be completed in Phase 10. Every value on screen is simulator output, and the SIMULATION badge stays
visible throughout.

## Setup (before the audience arrives)

```bash
cd dashboard && npm run build && npm run preview     # open http://localhost:4173
```

Pre-open the recordings you will use: `node_mature`, `signals_3day`, `siting_greedy`, `fires_day`.

## The route

**1. The place (30 s) — `siting_greedy`.**
Turn on *Interfaces* and *Ignition likelihood*. "Fires here start near people: footpaths, the village, the road and
the power line." Use the *Layout* buttons: grid 24%, corridor 49%, greedy 83% of ignition likelihood within 50 m of a
node (SIM). "Where you put a hundred cheap nodes matters more than how many you have." Optionally turn on
*Satellite pixels*: one 375 m pixel covers about 29 node cells.

**2. The problem (45 s) — `signals_3day`.**
Open the *Signals* tab: daily temperature and humidity cycles, fuel dryness (FFMC), and the grey haze band on day 2.
Click a node: its reading drifts, cycles and spikes, with no fire at all. Turn on the *Baselines* layer and scrub
through day 2: grey triangles (fixed threshold, P0) and grey rings (v1, P1) cover the map. "This is what the older
approaches do: they cry wolf." The *Results* tab gives the numbers: P0 ≈ 341 and P1 ≈ 136 false incidents per month
(SIM).

**3. PRAHARI's node layer (60 s) — `node_mature`.**
"This network has run for 28 days: 14 to calibrate, 14 to tune its thresholds. We are watching days 29 to 31."
Scrub to day 31, 13:00, when the fire starts beside the north-east footpath. Watch nodes near it glow with smoke and
then pulse as candidates. Click node 41 or 31 and open the *Node* tab:

- *Reading and slow baseline*: the baseline stays calm while the reading jumps.
- *Detection residual*: the fast residual isolates the jump.
- *QCC p-value*: it drops to its floor, 1/3361 (the node has 3,360 calibration values in this 4-hour bin).
- *Node CUSUM*: the evidence climbs and crosses h (about 227, tuned on the network's own quiet days); the ember dot
  marks the candidate.

The fire is confirmed when a second nearby node agrees, about two hours after ignition in this run (SIM). A satellite
would need an overpass plus processing time and a much bigger fire.

**3b. Why this alarm (45 s) — *Alerts* tab, still on `node_mature`.**
The latest alert opens "Why this alarm": the escalation ladder lit at CONFIRMED; the SCMR gauge (the fire's
neighbourhood is 11× more active than the network, well above 3); Fisher combining the two nodes' evidence; today's
prior ("dry, busy day — 2 agreeing nodes needed"); the Bayes bar (posterior odds 0.42 against a 0.01 threshold).
"Every number here comes from the recorded trace; nothing on this panel is free text."

**3c. Switch SCMR off (30 s).** Scrub to day 30 around 14:00 (the haze day). The counter reads 3 false alarms. Press
*SCMR* in the Mechanisms row: the same run with SCMR off loads at the same moment and the counter jumps to 15.
"Haze is everywhere at once; a fire is local. That one rule removes most of the haze alarms."

**4. Honesty (30 s) — *Results* tab.**
The node-layer table shows the two calibration checks: about 1.1% of quiet p-values fall below 1% (target 0.8–2.0%)
and about 0.65 local false candidates per node per 30 days (target 0.5–1.5). "Where our numbers miss the report's
intervals, we show that too, and we checked against the original simulation over 20 seeds." See
[../results/validation.md](../results/validation.md).

**4b. What each mechanism buys (40 s) — *Results* tab, lower charts.**
The ablation chart: take away QCC, TTC, SCMR or RAQ and false incidents rise every time (SIM). The operating dial:
the design point confirms in about an hour at a few false incidents a month; asking for faster confirmation moves
along the curve and costs more false alarms. The spacing chart: at 70 m most fires reach two nodes; at 150 m almost
none do. Every footer names the seeds and simulated days.

**5. Robustness (optional, 20 s) — *Health & model card* tab.**
Every module, its equation, its source tag and its state. "If any real model fails during a run, its simple stub
takes over and the demo keeps going."

## Likely questions

| Question | Short answer |
| --- | --- |
| Is this real data? | No. Everything is simulation, labelled SIM. The models are calibrated to literature, datasheets or stated assumptions, and each parameter carries its tag. |
| Why not just use satellites? | They see fires only after overpass and processing, and only once fires are hot and large. Early fires under canopy are too small. |
| Why these node spacings? | The spacing chart: a fire's smoke reaches two nodes reliably only when they are about 70 m apart (SIM). |
| What does each mechanism contribute? | The ablation chart: removing any of QCC, TTC, SCMR or RAQ raises false incidents (SIM). |
| Why not a threshold on each sensor? | Daily cycles, drift and haze cross any fixed line. The P0 row in Results shows the cost. |
| What stops haze triggering PRAHARI? | Two things: common-mode periods are excluded when thresholds are tuned, and spatial common-mode rejection needs a cluster to be at least 3× more active than the network. Switch SCMR off and watch the difference (3 vs 15 alarms on the haze day, SIM). |
| How do you know the p-values are right? | They are conformal: ranked against each node's own quiet history, so on quiet data about 1% fall below 1%. We measure that (1.10%, SIM). |
| Why did detection take about two hours in the demo? | The node needs sustained evidence to cross a threshold set for one false candidate per node per month, and a second node must agree. The operating curve (Phase 7) shows the trade-off. |
| What happens if a node fails? | Health weights (M29) and fault injection (M21) arrive in Phase 9; module-level failures already fall back to stubs. |
| How long did it take to build? | See [../journey/README.md](../journey/README.md): phases 0–6 so far, each ending with a working dashboard. |
