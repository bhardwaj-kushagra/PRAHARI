# Phase 8 — Communications and energy

## Goal

Show the engineering underneath the detector: a node's evidence has to cross a real radio link that can collide,
fade or go down, and the node has to live on a small solar-charged store under a forest canopy. The phase adds both
as real models, keeps them switchable, and shows them on the map, in the node views and in Results.

## What was built

- **Radio links (M38):** shadowing (a fixed random loss per link) and TS011 relays for nodes that cannot reach a
  gateway directly, in the links setup module.
- **Uplinks (M39, M40):** `comms/lora.py` (time on air, ALOHA collisions with capture, node-to-node links, relay
  choice) and `comms/lorawan_real.py` (candidate frames and hourly heartbeats, channels, retries, relay hops,
  gateway outages with re-routing and store-and-forward).
- **Energy (M41–M43):** `energy/power.py` (budget, half-sine harvest, supercapacitor store, power modes) and
  `energy/budget_real.py` (per-minute balance, cloudy days, per-node shade, ULP and stop modes).
- **Pipeline:** the energy stage now sees the minute's packets; comms skips nodes that are off; frames carry queues,
  modes and gateways out of service; packets between recorded frames are carried forward.
- **Results:** `prahari energy` writes the MQ-2 against BME688 comparison (`results/energy.json`).
- **Scenarios:** `gateway_outage` (the mature network with the gateway down across the fire) and `cloudy_days` (six
  days, days 2–4 cloudy).
- **Dashboard:** packet animation with queue badges, state-of-charge ring gauges, the gateway out-of-service mark,
  power mode and a state-of-charge chart in the node views, and the energy chart in Results.

## How it works

Every minute each node that has something to send — a candidate, or its hourly heartbeat — picks a random moment and
one of three channels and transmits at its spreading factor for the frame's time on air (61.7 ms at SF7, about 1.5 s
at SF12). Two frames on the same channel and SF that overlap are both lost unless one is 6 dB stronger. A lost
candidate frame tries again after a random 1–10 s, up to three times. A node that cannot reach any gateway sends
through a neighbour that can (TS011 relay). When its gateway is out, a node keeps its candidate frames and sends them
when the gateway returns. Only frames that arrive reach the edge.

Every minute each node also books its energy: the panel's share of the day's sun (a half-sine from 06:00 to 18:00,
cut to 10–40% on a cloudy day and shaded by the canopy), minus the sensor, microcontroller and radio. Below 20% of its
4.56 Wh store it scans in ultra-low-power mode; below 5% it stops until it has recovered to 10%.

## Challenges and issues

1. **Keeping every accepted result intact.** A realistic radio changes when candidates reach the edge, and therefore
   the golden numbers and the demo recordings.
2. **Energy needs to know about packets, and comms about energy,** but the energy stage was called with the minute only,
   after the edge.
3. **Recordings are decimated** (every tenth minute plus event minutes), so most heartbeats would never reach a frame.
4. **The energy chart drew nothing:** bars on a log axis have no zero to start from.
5. **The second chart colour failed the palette check** (grey against blue, ΔE 14.4 < 15).
6. **A shell command killed itself again:** a pattern-based `pkill` matched its own command line (the Phase 2
   lesson, repeated).
7. **Delayed frames change the edge's timing:** in `gateway_outage` the frame held by the outage arrives within 30
   minutes of the next one, and the fire is confirmed earlier than with a perfect link.

## Decisions and trade-offs

| Decision | Pros | Cons | Ids |
| --- | --- | --- | --- |
| Radio and energy real only in the Phase 8 scenarios | every earlier result and recording unchanged; legacy mode intact | the default demo still shows perfect links | P8-1 |
| Shadowing off by default, 6 dB in the scenarios | Phase 1 links unchanged | two link pictures to explain | P8-2 |
| Minute-level radio with spill-over into the next minute | simple, vectorised over nodes, fast | frames at a minute boundary are resolved slightly apart | P8-3 |
| Queue candidates, drop heartbeats during an outage | the evidence survives; heartbeats are only status | heartbeat history has a gap | P8-4 |
| Energy stage receives the packets; comms reads the last energy mode from the context | no hidden coupling beyond one context field | a one-minute lag between running out and falling silent | P8-5, P8-6 |
| Carry skipped-minute packets into the next frame | the animation shows every packet; no extra frames | slightly larger frames | P8-6 |
| Lollipops in one hue for the energy chart | correct on a log axis; passes the palette rules | not a conventional bar chart | P8-9 |

## Resolution

- 1: the modules stay stubs by default; all nine earlier recordings were regenerated and compared frame by frame —
  identical (only the model card text changed).
- 2: the energy stage receives `(minute, weather, delivered)`; `ctx.energy_mode` passes the mode to the next minute's
  comms.
- 3: packets of skipped minutes ride in the next written frame with their own minute `t`.
- 4 and 5: lollipop stems from the axis minimum, one series hue (each row is named on the axis).
- 6: list processes first, then kill by process ID (now twice-learned; see the troubleshooting page).
- 7: documented and proposed (use the detection minute each frame carries in the cluster window), `KNOWN_ISSUES.md`.
  Resolved in Phase 9 on approval: the confirmation is now at 15:14, as with a perfect link
  ([phase-9-regimes-learning.md](phase-9-regimes-learning.md)).

## Acceptance results

| # | Test | Result (SIM) |
| --- | --- | --- |
| 1 | M39: 61.7 ms at SF7 and 1,482.8 ms at SF12 for 24 bytes | **pass** — 61.7 ms and 1,482.75 ms |
| 2 | ALOHA success within 3 points of e^(−2G) | **pass** — 82.4 / 61.5 / 37.8% against 81.9 / 60.7 / 36.8% at G = 0.1 / 0.25 / 0.5 |
| 3 | A 0.5 Wh-per-day node with no sun lasts 9 ± 0.5 days | **pass** — stops at 5% after 8.66 days, empty after 9.11 days |

Scenario outcomes, energy numbers and the reproduce commands are in
[../results/validation.md](../results/validation.md) §6.

## What to show

`gateway_outage`, day 31, 14:00–15:15: the gateway crossed out, the badge on node 41 while its frame waits, the burst
at 14:30, the confirmation at 15:14 (14:48 before the Phase 9 arrival-time fix). `cloudy_days`, day 5 at 02:00: amber rings on the nodes scanning in ULP; click one
for its state-of-charge chart. Results: the energy chart — a BME688 node runs on a fraction of the harvest; an MQ-2
heater would drain the store in hours.
