# 7. The complete guide to PRAHARI-SIM

One page that explains the whole simulator: what it models, how a simulated minute is computed, what every part of
the dashboard shows and means, what each recorded scenario demonstrates, how the experiments are judged, and how to
run and change things. It is written as a reference to come back to, so each part stands on its own and links to
the page with the full detail.

Everything the simulator produces is **simulation output**. Numbers quoted here are marked **SIM** and come from the
committed recordings and `results/` files at release 1.0 (tag `v1.0.0`); they change only if the engine or its
configuration changes.

**Contents**

1. [Names: FIRENET, PRAHARI, PRAHARI-SIM](#1-names-firenet-prahari-prahari-sim)
2. [The system being simulated](#2-the-system-being-simulated)
3. [One simulated minute, step by step](#3-one-simulated-minute-step-by-step)
4. [The simulated world, part by part](#4-the-simulated-world-part-by-part)
5. [The detection pipelines compared](#5-the-detection-pipelines-compared)
6. [The dashboard, element by element](#6-the-dashboard-element-by-element)
7. [The recorded scenarios](#7-the-recorded-scenarios)
8. [Regime Cards: other countries](#8-regime-cards-other-countries)
9. [Experiments and results](#9-experiments-and-results)
10. [Running and changing the simulator](#10-running-and-changing-the-simulator)
11. [How the project keeps itself honest](#11-how-the-project-keeps-itself-honest)
12. [The repository, branches and documents](#12-the-repository-branches-and-documents)
13. [Known limits and open items](#13-known-limits-and-open-items)

---

## 1. Names: FIRENET, PRAHARI, PRAHARI-SIM

| Name | What it refers to |
| --- | --- |
| **FIRENET** | **F**ire **I**dentification and **Re**sponse **N**etwork for **E**arly **T**racking: the wildfire early-warning system as a whole (sensor nodes in the forest, radio, gateway and alerting). Built by the team **AgniWare**. |
| **PRAHARI** | The detection method inside FIRENET: the statistics at each node and at the gateway that decide when gas readings are evidence of a fire. *Prahari* means "sentinel" or "guard" in Hindi. |
| **PRAHARI-SIM** | This repository: a simulator that generates a virtual forest, fires and sensor readings minute by minute, runs PRAHARI and older methods on them, records everything, and a dashboard that replays the recordings in a browser. |

The public website `https://dashboard.firenet.live` is the same dashboard, built from the `site-live` branch
(section 12).

## 2. The system being simulated

```text
   forest (1.4 km square)                                   gateway / edge                     people
 ┌───────────────────────────────┐   LoRaWAN radio   ┌──────────────────────────────┐   alert   ┌──────────┐
 │  100 solar gas-sensing nodes  │ ───────────────►  │ cluster → SCMR → Fisher →    │ ───────►  │ rangers, │
 │  70 m apart, each runs the    │  candidate frames │ prior → quorum / Bayes →     │           │ forest   │
 │  node layer (TTC→QCC→CUSUM)   │  + hourly beats   │ escalation ladder            │           │ office   │
 └───────────────────────────────┘                   └──────────────────────────────┘           └──────────┘
```

- **Nodes.** Each node has a metal-oxide (MOX) gas sensor that responds to wood smoke, but also to temperature,
  humidity, drift, passing vehicles, cooking fires and regional haze. The node does not send raw readings all day; it
  runs the **node layer** and sends a frame only when its own evidence of a local rise crosses a threshold (a
  *candidate*), plus an hourly heartbeat.
- **Gateway (the edge).** The **edge layer** collects candidates, groups nearby ones, throws out patterns that look
  like haze (everywhere at once) rather than fire (local), combines the nodes' evidence, weighs it against how likely
  a fire is today, and walks an incident up a ladder: WATCH → CANDIDATE → CONFIRMED → ESCALATED.
- **The central difficulty is false alarms, not sensing.** With 100 nodes, one false alarm per node per month would
  be about three a day for the whole network. Most of PRAHARI's machinery exists to keep that rate low without losing
  real fires. [02-background.md](02-background.md) explains the science in full.

## 3. One simulated minute, step by step

The engine advances one simulated minute per *tick*. Before the first tick, three **setup stages** run once:
the landscape (distance fields and ignition-likelihood map), node siting (the layouts), and the radio links. Then,
for every minute:

| Step | Stages, in order | What happens |
| --- | --- | --- |
| 1. The world | weather → fuel moisture (FFMC) → ignition → fire growth → smoke plume; nuisance events; regional haze → sensor reading → sensor faults | The forest's state for this minute, ending in one reading per node. |
| 2. Baselines | P0, P1, P1t | The older detection methods run on exactly the same readings. |
| 3. Node layer | TTC → QCC → score → CUSUM | Each node's evidence; nodes whose evidence crosses the threshold become candidates. |
| 4. Edge layer | radio → prior → clustering → SCMR → Fisher → likelihood ratio → quorum → escalation; then energy and satellite | Candidates travel to the gateway and are judged; batteries charge and drain; satellite overpasses are checked. |
| 5. Recording | events, evidence traces, node display states, frame | A frame is written (every k-th minute, plus any minute with an event or alert). |

Every stage has a `real` implementation (the full model), a `stub` (a simple stand-in that always works) and, where
allowed, `off`. Which one runs comes from the configuration. If a real stage throws an error or returns invalid output
(NaN, wrong shape), it is swapped for its stub for the rest of the run and marked *degraded*; the run continues. All
randomness comes from one master seed, split into a separate stream per module, so the same seed always gives the
same recording byte for byte. Detail: [../architecture/02-engine.md](../architecture/02-engine.md).

## 4. The simulated world, part by part

The model numbers (M1–M46) are the equations in [`../SPEC.md`](../SPEC.md) §5. This section says what each part
represents in plain words; [../architecture/03-models.md](../architecture/03-models.md) says where each lives in the
code and [02-background.md](02-background.md) explains the science behind it.

### 4.1 Landscape and where the nodes go (M1–M4, setup)

- **The landscape** is a 1400 m square modelled on the Terai foothills: a village, two footpaths, a road and a power
  line. These are the *interfaces* where people start most fires.
- **Ignition likelihood (M2, M3)** is highest next to the interfaces and fades with distance (each interface has a
  weight and a decay distance). It is a relative map, not a probability of fire today.
- **Layouts (M1, M4).** Three ways to place the same 100 nodes: a regular **grid** 70 m apart, a **corridor** along
  the interfaces, and a **greedy** layout that picks node positions one at a time to cover as much ignition
  likelihood as possible within the 50 m detection radius. Covered likelihood on the default landscape: grid 24%,
  corridor 49%, greedy 83% (SIM).
- **Radio links (M38).** Path loss from each node to the gateway sets its LoRa *spreading factor* (SF7 is fast and
  short-range, SF12 slow and long-range). Some greedy-layout nodes have no direct link and need a relay.

### 4.2 Weather and fuel (M5–M8)

- **Temperature (M5)** follows a daily cycle with random day-to-day noise; **humidity (M6)** comes from the dew point
  (Magnus formula); **wind** speed is drawn from a lognormal around a prevailing direction; **rain** falls on some days.
- **FFMC (M7)** is the Canadian Fine Fuel Moisture Code, updated daily at noon from weather and rain. High FFMC
  (around 85–96) means dry, easily lit litter. The implementation agrees with the official `cffdrs` package to within
  0.005 over 48 test days.
- **Day type.** Each day is classed *dry/busy* or *wet/quiet*. This sets the edge's prior odds of a fire and the
  required number of agreeing nodes (section 4.6).
- **M8** turns FFMC into the probability that an ignition takes hold.

### 4.3 Fires and smoke (M3, M8–M16)

- **Ignitions** are scripted (a fire at a set place and time, used by the demo scenarios) or random (a Poisson
  process on the ignition-likelihood map, scaled by time of day). In the lightning scenarios a storm drops several
  strikes over a disc (M3 lightning term).
- **Growth (M9)** ramps each fire's source strength up over time (the legacy model).
- **Smoke (M12, M13, M16)** spreads from each fire downwind in the legacy exponential-directional plume, with a
  transport delay so distant nodes see smoke later. An optional **Gaussian plume** (M11, M14, M15: Briggs dispersion
  and sub-canopy wind) gives narrower, more physical plumes; only `fires_day_gaussian` uses it.
- Smoke is measured in **su** (smoke units), the unit of the sensor's fire response.

### 4.4 What a sensor reports (M17–M21)

A node's reading (M18) is the sum of several parts, which is why a fixed threshold fails:

| Part | What it represents |
| --- | --- |
| Baseline and drift | Each sensor's own offset, which wanders slowly over days. |
| Daily cycle | MOX sensors respond to temperature and humidity, so the reading swings every day with no smoke at all. |
| Noise (M19) | Minute-to-minute noise that is correlated in time (AR(1)), larger when conditions change, with occasional heavy spikes. |
| Nuisance events (M20) | Short local spikes: a vehicle on the road, cooking smoke near the village. |
| Regional haze (M20) | A slow rise that affects **every** node at once, from crop burning or distant smoke. Shown as shaded bands in the Signals tab. |
| Fire smoke (M17) | The sensor's response to smoke from a real fire nearby. |
| Faults (M21) | Stuck readings, sudden offsets, spikes or dropouts (missing data). Only `sensor_fault` switches these on. |

### 4.5 PRAHARI's node layer (M24–M29)

Each node turns its reading into evidence in four steps:

1. **TTC, two-timescale conditioning (M24, M25).** A slow baseline (an EWMA with a 180-minute freeze cap, so a
   long fire cannot drag the baseline up) tracks the daily rhythm and drift. The **fast residual** is the reading
   minus a lagged 60–180-minute mean: it isolates sudden rises and ignores slow ones.
2. **QCC, quantile-calibrated conformal p-values (M26).** The residual is ranked against the node's own quiet
   history for the same 4-hour time-of-day bin. The p-value says "how unusual is this for this node at this time of
   day". Because it is a rank, on quiet data about 1% of p-values fall below 0.01 by construction. The smallest
   possible p-value (the *floor*) is 1/(n+1) for n calibration values.
3. **Score (M27).** −ln p, summed over channels and weighted by the node's health (one channel, weight 1 by default).
4. **CUSUM (M28).** Evidence accumulates minute by minute (k = 1.5) and resets towards zero when quiet. When the sum
   G crosses the threshold **h**, the node raises a **candidate**. h is not a textbook value: it is *tuned by replay*
   on the node's own quiet days so each node raises about one false candidate per 30 days, leaving out periods when
   the whole network rose together (common mode).
5. **Health weight (M29, advanced).** A node whose data are stale, stuck (no variance) or out of line with its
   neighbours gets a weight below 1; below 0.1 it **abstains**, meaning its evidence no longer counts. On by default
   only in `sensor_fault`.

A network needs **calibration days** before this works: the demo recordings use 14 days to collect each node's quiet
history and 14 days to tune h, then show the days after (a *warm start*).

### 4.6 PRAHARI's edge layer (M30–M36)

| Step | Model | What it does |
| --- | --- | --- |
| Clustering | M30 | Groups candidates within R = 1.6 × spacing (112 m at 70 m) over a 30-minute window. |
| SCMR, spatial common-mode rejection | M31 | Compares how active the cluster's neighbourhood is with how active the whole network is. A fire is local, haze is everywhere: the ratio must be at least 3 (1.5 while a lightning storm is flagged, an untested assumption). A cluster that fails is held at WATCH. |
| Fisher combination | M32 | Combines the members' evidence into one p-value for the cluster (each candidate counts as p ≈ 6.9 × 10⁻⁴, from one candidate per node per 30 days over a 30-minute window). |
| Prior | M33 | How likely a fire is right now: prior odds 10⁻⁴ on a dry/busy day, 10⁻⁶ on a wet/quiet day (legacy form); an integral form uses the ignition map and FFMC instead. |
| Likelihood ratio | M34, M36 | How much the evidence should move the odds. By default a conservative bound (Sellke–Bayarri–Berger); with a model fitted on controlled burns (M36), a learned ratio. |
| RAQ, risk-adaptive quorum | M34 | How many agreeing nodes are needed: 2 on a dry/busy day, 3 on a wet/quiet day (legacy form). A Bayes form compares posterior odds with a threshold instead. |
| Escalation | M35 | The incident ladder: WATCH → CANDIDATE → CONFIRMED → ESCALATED. A **confirmed** incident is the system's fire alarm. |

Every edge decision writes an **evidence trace**: the cluster, the SCMR ratio, the Fisher p-value, the prior, the
posterior and a one-line explanation. The dashboard's "Why this alarm" panel is drawn directly from these traces.

### 4.7 Radio, power and satellites (M37–M43)

- **Radio (M39, M40).** Time on air per spreading factor; collisions when two frames overlap (ALOHA, with the 6 dB
  capture effect); retries; relay hops (TS011) for nodes without a direct link; store-and-forward when the gateway is
  down. Off (a perfect link) by default; on in `gateway_outage` and `cloudy_days`.
- **Energy (M41–M43).** Each node's daily energy use depends on its sensor mode and radio airtime; a small solar panel
  harvests energy in a half-sine each day (less on cloudy days); a supercapacitor stores it. Below 20% charge a node
  drops to ultra-low-power (ULP) scanning, below 5% it stops, and it restarts at 10%. Off (infinite energy) by default.
- **Satellite (M37).** Polar-orbiting satellites pass at fixed local times. A fire is seen only if it is larger than
  500 m² at the overpass, and even then is missed 20% of the time; the alert arrives after a MODIS or VIIRS
  processing delay. The stub is a fixed delay after ignition. Real in the Phase 9 scenarios.

### 4.8 Judging results (M44–M46)

- **Incidents (M46).** Alarms close together in space and time are merged into one incident, so one fire does not
  count as five alarms. An incident with no fire within 150 m is a **false incident**.
- **Detection.** A fire counts as detected if a confirmation within 150 m arrives within 3 hours of ignition.
- **Intervals.** Detection rates carry a Wilson interval (M44); false-incident rates an exact Poisson interval (M45).
- **Protocol.** Per seed: 14 calibration days, 14 tuning days, 30 test days. A *quiet pass* (no fires) measures
  false incidents; a *fire pass* (injected fires) measures detection.

## 5. The detection pipelines compared

All pipelines run on the same readings in the same run, so the comparison is fair by construction.

| Pipeline | Short name | How it decides |
| --- | --- | --- |
| **P0** | fixed threshold | Alarm when a reading exceeds its first-day mean + 3 standard deviations (M22). Grey triangles on the map. |
| **P1** | v1 as written | A slow EWMA baseline, a z-score CUSUM with a textbook threshold (k = 0.5, h = 8.8), and two nodes within R must agree (M23). Grey rings on the map. |
| **P1t** | v1, replay-tuned | P1 with its threshold tuned on replayed quiet data, as PRAHARI's is (M23 + M28). |
| **P2** | PRAHARI | The full node layer and edge layer (M24–M35). Coloured node glyphs and confirmed incidents on the map. |
| P2 minus X | ablations | P2 with one mechanism (QCC, TTC, SCMR or RAQ) removed, to show what each one contributes. |

## 6. The dashboard, element by element

The dashboard replays recordings in the browser with no server. Layout: a header across the top, the map on the left
(60%), a side panel with tabs on the right (40%), the time controls and footer along the bottom. On screens narrower
than 1000 px the parts stack vertically.

### 6.1 Header strip

| Element | Meaning |
| --- | --- |
| **PRAHARI-SIM** (on the public site: **FIRENET** with PRAHARI-SIM beneath) | Name. |
| **SIMULATION** badge (yellow) | Permanent reminder that every value is simulated. It never disappears. |
| Scenario | The name of the loaded scenario (section 7). |
| Layout | The active node layout and the share of ignition likelihood it covers within 50 m. |
| Clock | Simulated day and time (Day 1 is the first simulated day). |
| Day type | *dry / busy* or *wet / quiet* today (section 4.2). |
| Prior odds | The edge's prior odds of a fire right now (M33), for example 1e-4. |
| Required quorum | How many agreeing nodes the edge needs today (RAQ, M34). |
| Weather | Temperature, relative humidity and FFMC at this minute. |

### 6.2 The command map

**Layout buttons: Grid · Corridor · Greedy.** Each shows its covered likelihood. The layout the recording actually
simulated is tagged *simulated*; clicking another one previews its node positions as hollow circles over the map
without re-running anything.

**Layer switches** (each can be turned on and off; the small key beside each explains its symbols):

| Layer | What it draws |
| --- | --- |
| Interfaces | Footpaths (dashed), road (solid grey), power line (dot-dash), village (outlined polygon). |
| Ignition likelihood | A warm-white glow, brighter where fires are more likely to start (M3, relative scale). |
| Smoke | The smoke field from active fires, slate-coloured on a log scale from 0.05 to 2.5 su. The legend says which plume model is active (legacy M12 or Gaussian M11). |
| Baselines | Recent P0 alarms (grey triangles) and P1 alarms (grey dashed rings) from the last 30 minutes: what the old methods would be shouting now. |
| Radio links | Each node's link to the gateway, coloured by spreading factor; a dashed line means no direct link. |
| Detection radius | A 50 m disc around each node: the area where a small fire's smoke is reliably detected. |
| Satellite pixels | The 375 m grid of a VIIRS satellite pixel over the forest: one pixel covers about 29 node cells. |
| Packets (radio recordings only) | Recent uplinks fading with age: delivered in pine, collided in amber dashes; candidate frames are thicker than heartbeats. A badge counts frames waiting at a node. |
| Stored energy (energy recordings only) | A ring around each node filled to its state of charge, coloured by power mode (standard, ULP, stopped). |

**Glyphs on the map:**

| Glyph | Meaning |
| --- | --- |
| Small pine (green) dot | A normal node. |
| Amber ring | *Elevated*: the node's p-value is below 0.01 right now. Something unusual, not yet evidence. |
| Pulsing ember (orange) dot | *Candidate*: the node's CUSUM crossed h in the last 30 minutes. |
| Ember dot with a halo | *Confirmed*: the node belongs to an incident the edge confirmed in the last 2 hours. |
| Grey × | *Fault*: health weight below 0.1; the sensor abstains. |
| Hollow grey ring | *Low power*: the node's store is below 5% (energy recordings). |
| Square (g1) | The gateway. Crossed out when it is out of service (`gateway_outage`). |
| Soft glow around a node | Smoke signal reaching that node; brighter means more smoke. |
| Orange diamond with an arrow | An active fire; the arrow points where the wind carries its smoke. |
| Wind dial (top right) | Current wind direction and speed. |
| Scale bar (bottom) | 0 to 1400 m. |

Click a node to select it: it gets a dashed outline, and the Node and Signals tabs follow it.

### 6.3 Race timeline (under the map)

Shown when the recording contains a fire. Along one axis: the **ignition**, the **first node candidate**, **PRAHARI
confirmed** (within 150 m), the satellite **overpass** that sees the fire (missed overpasses as crosses), and the
**satellite alert** (M37), each with its time since ignition. The headline states who alerted first and by how much.
When the recording's satellite side is only the stub (a fixed delay), the timeline says so and claims no race. A fire
selector appears when a recording has several fires.

### 6.4 Time controls and footer

| Element | Meaning |
| --- | --- |
| ◀ ▶ | Step one recorded frame back or forward (also ← →). |
| Play / Pause | Start or stop playback (also Space). |
| ×1 ×10 ×60 ×600 | Playback speed: ×60 plays one simulated minute per real second; ×1 is real time; ×600 is ten minutes per second. |
| Clock | Day, time and minutes since the start (t). |
| Scrub bar | Drag to any moment. The marks above it are events: ignitions (ember), alerts (white), satellite alerts (amber), candidates (pine), module degradations (grey). |
| Footer | SIMULATION · seed · simulated days (and the first recorded day for warm starts) · scenario · number of frames · recording file · "every value shown is simulator output (SIM)". An incomplete recording is flagged here. |

### 6.5 Side panel: picking a recording

| Element | Meaning |
| --- | --- |
| Regime | Filters the recording list by Regime Card (India, USA, Canada, Australia, or all); the loaded recording's card is summarised (radio plan, alert format, lightning). |
| Recording | Every bundled recording (section 7). Loading one keeps the other settings. |
| Open file… | Open any `.prs.jsonl.gz` recording from disk. Dropping a file on the page does the same. |
| Live engine ▸ | Only on `main` with the optional server running: start a run on the local engine and watch it stream in. Hidden on the public site. |

### 6.6 Tab: Health & model card

One row per module: **Module**, **Config** (what the configuration asked for), **Now** (its state at this minute:
`real`, `stub`, `off`, or `degraded` if it failed and fell back), **Model** (a plain description, its equations, version,
the source of its parameters and any notes, such as the tuned h), **Tag** (the source class: LIT, VEN, DER, ASM, TGT;
section 11) and **Errors** (errors by the end of the run). On a phone each row becomes a card.

### 6.7 Tab: Signals

- **Weather and fuel moisture:** temperature, humidity, wind and FFMC over the whole recording, with haze episodes as
  shaded bands and the regional haze level H(t).
- **The selected node's reading** over the recording.
- **Eight nodes** as small multiples on shared scales, to compare how the same weather and haze affect different
  sensors. Click one to select that node.

### 6.8 Tab: Node

**Readout** (values at the current frame): state, position, reading and residual (su), CUSUM G against h, the
calibration count n with its p-value floor, and the health weight; the uplink (gateway and spreading factor, a relay
node, or "no link closes"), distance to the gateway, path loss and received power; and in Phase 8 recordings the
state of charge, power mode and frames waiting.

**Node evidence charts** (the whole recording, stacked on one time axis):

| Chart | What to look for |
| --- | --- |
| Reading and slow baseline (M18, M24) | The baseline follows the daily rhythm; a fire makes the reading leave it quickly. |
| Detection residual (M25) | Flat around zero on quiet days; a fire shows as a sharp rise. |
| QCC p-value, log scale (M26) | Drops towards its floor (dashed) when the residual is unusual for this node and time of day. |
| Node CUSUM G and threshold h (M28) | G climbs while evidence lasts; crossing h (dashed) makes a candidate (ember dot). |
| Health weight (M29) | 1 for a healthy node; falling below 0.1 means it abstains. |
| Stored energy (M43, energy recordings) | State of charge with the ULP (20%) and stop (5%) levels. |

### 6.9 Tab: Alerts

- **Mechanisms.** Five switches: TTC, QCC, SCMR, RAQ, SRP. Each shows whether that mechanism is real in this
  recording. Where a pre-recorded variant exists (for example `wet_morning_haze__scmr-stub`), clicking a switch loads
  the same run with that mechanism off, at the same moment. Below them, **So far** counts false alarms and fires
  confirmed within 3 hours up to the current time.
- **Why this alarm.** For the selected (or latest) alert:
  - the **escalation ladder** with the incident's current rung lit;
  - **Spatial common mode (M31):** a log bar of the local-to-network activity ratio against the threshold 3, with the
    local and network percentages;
  - **Combined evidence (M32):** each member node's p-value and the cluster's Fisher p;
  - **Prior (M33):** the day type, prior odds and the quorum they imply;
  - **Decision (M34):** the likelihood-ratio bound × prior = posterior odds, as a log bar against the threshold;
  - a one-sentence **explanation** generated from the trace.

  Every number in this panel is read from the recorded evidence trace.
- **Alerts so far.** Every alert up to now; click one to explain it.

### 6.10 Tab: Results

Charts from `results/summary.json`, the experiment output (section 9); nothing is typed in by hand:

| Chart | What it shows |
| --- | --- |
| False incidents per month | P0, P1, P1t and P2 on a log axis with 95% intervals (M45), one tick per seed, and the report's intervals for comparison. |
| Fires confirmed within 3 h | Detection per pipeline with 95% intervals (M44). |
| Ablation | P2 with one mechanism removed at a time, with each variant's confirmation rate. |
| Operating dial | False incidents against median time to confirm: the trade-off between speed and false alarms. |
| Node spacing | Fires confirmed, and fires seen by only one node, within 3 h at 70, 100 and 150 m spacing. |
| Node layer | Calibration checks: share of quiet p-values below 0.01 (target 0.8–2.0%) and false candidates per node per 30 days (target 0.5–1.5). |
| Energy | Wh per day for each sensor mode (log axis) against the solar harvest on clear and cloudy days. |
| Learning curve (M36) | Confirmation rate and time to confirm against the number of controlled burns K the likelihood ratio was fitted on; the conservative bound as a dashed reference. |
| Maturity (M26) | How the p-value floor and the time to the first candidate improve with days of calibration data. |

Every chart footer names its seeds and simulated days.

### 6.11 Presenter mode and the guided tour

Presenter mode plays a nine-step storyboard (`dashboard/public/storyboard.json`): each step opens a recording at a
bookmarked moment, sets speed, layers and tab, and shows a caption strip under the header with the line to say.

| Key | Action |
| --- | --- |
| 1–9 | Jump to storyboard step 1–9. |
| Space | Play or pause. |
| ← → | Step one frame. |
| S / R | Switch SCMR / RAQ on the recordings that have variants, keeping the clock. |
| F | Full screen. |
| Esc | Hide the caption (and deselect a node). |

`?presenter=1` in the address opens step 1 directly. On the public site a **Guided tour** button starts the same
storyboard, and Previous / Next / ✕ buttons in the caption replace the keys on phones and tablets. The nine steps are
listed in [06-demo-walkthrough.md](06-demo-walkthrough.md).

### 6.12 Colour language

- **Pine (green), amber, ember (orange)** are reserved for node states: normal, elevated, candidate or confirmed.
- **Grey** is for the old baselines and for reference lines (baseline, floor, h), dashed with end labels.
- **Yellow** is the SIMULATION badge only.
- Chart series use one blue; smoke is slate; ignition likelihood is warm white; spreading factor is a single-hue
  ramp. The palette was checked for contrast and colour-vision deficiency.

## 7. The recorded scenarios

Twenty recordings are bundled (`recordings/*.prs.jsonl.gz`). All use seed 11. *Warm start* means the run simulates
every day from day 1 (so nodes calibrate and tune) but records only the last days.

| Recording | Days (recorded) | What it demonstrates | Where to look |
| --- | --- | --- | --- |
| `smoke` | 1 | Framework check: real weather, clean stub signals, one scripted fire. | Map, smoke layer. |
| `siting_corridor`, `siting_greedy` | 1 | The corridor and greedy layouts on the default landscape, with a fire beside a footpath. | Layout buttons, Interfaces and Ignition likelihood layers. |
| `signals_3day` | 3 | Daily cycles, nuisance spikes and a haze episode, with no fire. | Signals tab; Baselines layer on day 2. |
| `fires_day` | 1 | Random ignitions near paths and the village plus a scripted fire; plumes follow the wind. | Smoke layer, wind arrows. |
| `fires_day_gaussian` | 1 | The same fires with the Gaussian plume (M11): narrower plumes. | Compare with `fires_day`. |
| `node_3day` | 3 | Node evidence from a cold start: haze on day 2, a fire on day 3. | Node tab. |
| `node_mature` | 31 (from day 29) | A mature network: haze on day 30, a fire on day 31 at 13:00 near the north-east footpath. | Node tab on nodes 31 or 41; Alerts tab. |
| `node_mature__scmr-stub` | 31 (from day 29) | The same run with SCMR off: the haze raises false alarms. | Mechanisms counter. |
| `wet_morning_haze` | 30 (day 30) | Haze on a wet, quiet day (quorum 3): SCMR holds the haze clusters at WATCH. Storyboard steps 3–4. | Map (amber nodes), Mechanisms counter. |
| `wet_morning_haze__scmr-stub` | 30 (day 30) | The same with SCMR off: false alarms climb. Storyboard step 4, key S. | Counter. |
| `wet_morning_haze__raq-stub` | 30 (day 30) | The same with RAQ off: a fixed quorum of 2 whatever the day. Key R. | Counter. |
| `gateway_outage` | 31 (from day 29) | The gateway is down 12:30–14:30 on day 31 during a fire: frames wait at the node and the edge still confirms. | Packets layer, queue badges, crossed-out gateway. |
| `cloudy_days` | 6 | Three cloudy days: charge falls, weak nodes switch to ULP scanning, then recover. | Stored-energy layer, Node tab. |
| `satellite_race` | 32 (from day 29) | A 14:00 fire on day 31 against the next satellite overpass (India card). Storyboard steps 1, 5–7. | Race timeline. |
| `sensor_fault` | 31 (from day 29) | Stuck, dropped-out and offset sensors abstain; the fire is still confirmed (India card). | Fault glyphs; Node tab health weight on node 55. |
| `lightning_storm` | 31 (from day 29) | A storm starts several fires at once; separate clusters; SCMR relaxed during the storm (Canada card). | Map, Alerts. |
| `lightning_storm__no-relax` | 31 (from day 29) | The same storm with SCMR kept at 3. | Compare the alerts. |
| `power_line_corridor` | 31 (from day 29) | Nodes along a distribution line; a fire beside it on a hot, windy afternoon (USA card, corridor layout). | Map, race timeline. |
| `bushfire_afternoon` | 31 (from day 29) | A fire on a hot, windy afternoon in dry eucalypt forest (Australia card). | Map, race timeline. |

A recording named `name__module-stub` is the same scenario and seed with one module switched to its stub; the
mechanism switches and the S and R keys use these. There is no separate `siting_grid` recording: the grid layout is
the default, used by `smoke` and most others.

## 8. Regime Cards: other countries

A Regime Card (`configs/regimes/*.yaml`) changes the setting without changing the method: weather, how strongly each
interface attracts ignitions, haze intensity, the radio plan and the alert format. All values beyond the India card's
literature sources are illustrative (ASM).

| Card | Setting | Radio plan | Alert format | Lightning | Notable differences |
| --- | --- | --- | --- | --- | --- |
| India | Terai and dry deciduous forest, pre-monsoon | IN865 (3 channels) | FSI KML | no | Villages weigh most; crop-burning haze × 3. |
| USA | Western wildland–urban interface | US915 (8 channels) | NIFC | no | Roads and power lines weigh most; hot and dry. |
| Canada | Boreal summer | US915 (8 channels) | CWFIS | yes | Fewer human ignitions; lightning storms start several fires. |
| Australia | Dry eucalypt summer | AU915 (8 channels) | Australian warnings | yes | Very hot (mean 32 °C), low dew point, windier. |

## 9. Experiments and results

### 9.1 The experiment presets

`prahari experiment --preset <name>` runs many seeds in parallel and writes JSON to `results/`:

| Preset | What it measures | Output |
| --- | --- | --- |
| `golden` | P0, P1, P1t and P2 over seeds 11, 22, 33, 44, 55 (100 nodes at 70 m, legacy models), the edge ablations, node-layer calibration, the operating dial | `golden.json`, `summary.json` |
| `ablation` | P2 minus QCC and P2 minus TTC in the report simulation's own forms | `ablation.json` (joins `summary.json`) |
| `spacing` | P2 at 70, 100 and 150 m spacing, seeds 11, 22, 33 | `spacing.json` |
| `seeds20` | P0–P2 over seeds 11–30, to measure the spread between seeds | `seeds20.json` |
| `learning` | The M36 learning curve and the M26 maturity curve | `learning.json`, `learning_model_k100.json` |

`prahari energy` writes the energy comparison to `results/energy.json`.

### 9.2 Headline results (golden preset, 5 seeds, SIM)

| Pipeline | False incidents per month (95% CI) | Fires confirmed within 3 h |
| --- | --- | --- |
| P0 fixed threshold | 340.6 (324.6–357.2) | 97.8% |
| P1 v1 as written | 136.2 (126.2–146.8) | 98.1% |
| P1t v1 replay-tuned | 14.4 (11.3–18.1) | 61.1% |
| **P2 PRAHARI** | **3.4 (2.0–5.4)** | **71.3%** |
| P2 minus QCC | 8.8 | 67.3% |
| P2 minus TTC | 8.4 | 59.9% |
| P2 minus SCMR | 5.0 | 71.6% |
| P2 minus RAQ | 5.4 | 77.2% |

How to read it:
- PRAHARI raises about 100 times fewer false incidents than a fixed threshold, and removing any one mechanism raises
  them again.
- The old methods detect nearly every fire because they alarm at almost everything.
- P2's median time from ignition to confirmation is 62 minutes (SIM).

Other results (SIM):
- **Energy:** a BME688 in standard mode uses about 0.42 Wh a day; an MQ-2's heater uses about 22.9 Wh a day, which
  would empty the 4.6 Wh store in about five hours. A clear day harvests about 1.5 Wh.
- **Learning curve:** with the conservative bound the edge confirms 49% of fires at 3 false incidents a month; fitted
  on 10 controlled burns, 68%; on 100, 71%.
- **Race:** in `satellite_race` PRAHARI confirms the fire about 8 hours before the satellite alert (with an
  illustrative overpass model).

### 9.3 Where the results miss the report

The simulator was checked against the project report's original simulation (`reference/prahari_simulation.py`).
- **Where they agree.** The detection code gives identical outputs on identical inputs. Over 20 seeds, the false-alarm
  rates of every pipeline agree statistically.
- **Where they miss.** PRAHARI's detection rate is lower than the report's: 71–73% against about 82%. Every model
  difference that was looked for has been ruled out; the evidence points to sampling in the calibration windows.
- **Where it is recorded.** Nothing was tuned to hide the gap. It is documented in
  [../results/validation.md](../results/validation.md) and `KNOWN_ISSUES.md`.

## 10. Running and changing the simulator

Full setup, prerequisites and every command: [04-setup.md](04-setup.md). The most used commands:

```bash
pip install -e "engine[dev,server]"                    # install the engine (Python)
prahari run --config configs/scenarios/node_mature.yaml --out recordings/node_mature.prs.jsonl.gz
prahari experiment --preset golden --jobs 4            # experiments → results/
cd dashboard && npm install && npm run dev             # dashboard at http://localhost:5173
scripts/demo.sh                                        # presenter-mode demo from the static build
scripts/check_all.sh --quick                           # the release check
```

**Where things live.**

| To change… | Edit |
| --- | --- |
| Which implementation a module uses | `modules:` in `configs/default.yaml` or a scenario file (`real`, `stub`, `off`) |
| A model parameter | `params:` in `configs/default.yaml`. Every block carries a `source` tag (section 11); unknown keys and untagged parameters are refused. |
| A scenario | `configs/scenarios/<name>.yaml`: it inherits the defaults and overrides only what differs (days, seed, layout, scripted fires, haze, module states, `record.from_day`). |
| A country setting | `configs/regimes/<card>.yaml` |
| The storyboard captions and bookmarks | `dashboard/public/storyboard.json` (no rebuild needed for the demo build) |

**A new scenario, step by step.**
1. Copy the closest file in `configs/scenarios/`.
2. Give it a new `description`.
3. Change what differs.
4. Run `prahari run --config … --out recordings/<name>.prs.jsonl.gz`.
5. Restart `npm run dev` (it copies the recordings in), and pick the new file.

**A new real module.** Write it beside its stub, register it under the same name, cite its equations in comments,
put its parameters in the configuration with source tags, and add unit tests with reference values. The pattern is in
[../architecture/02-engine.md](../architecture/02-engine.md) ("Adding a real module").

**Live mode (optional, `main` only).** Run `uvicorn server.app:app`. Then in the dashboard: Live engine ▸ Scenarios ▸
Start. The run streams frames as it computes them. Replay never needs this.

## 11. How the project keeps itself honest

- **SIMULATION everywhere.** The badge is on every view, every chart footer names its seeds and simulated days, and
  every number in the documents is marked SIM.
- **Source tags.** Every parameter says where it comes from:
  - **LIT**: published literature;
  - **VEN**: a vendor datasheet;
  - **DER**: derived from other values;
  - **ASM**: a stated assumption;
  - **TGT**: a design target.
- **No hand-typed results.** Charts read the result files; nothing is tuned to improve a chart without a record in
  `DECISIONS.md`.
- **Stubs and degradation.** A failing model falls back to its stub and is marked degraded instead of crashing the run.
- **Determinism.** The same seed gives the same recording byte for byte; `scripts/check_all.sh` regenerates every
  recording and compares them.
- **Misses are reported.** Where a result misses its target the gap and its diagnosis are published
  ([../results/validation.md](../results/validation.md)).

## 12. The repository, branches and documents

```text
engine/prahari/    the simulator (Python): core framework, world, env, fire, sensors, detect, comms, energy,
                   satellite, record, eval
engine/tests/      unit, integration and golden tests
configs/           default.yaml, scenarios/, regimes/, experiments/
recordings/        the 20 bundled recordings (.prs.jsonl.gz)
results/           experiment outputs (JSON) read by the Results tab
dashboard/         the React + TypeScript dashboard
server/            the optional live server (FastAPI)
reference/         the report's original simulation and the check scripts
scripts/           demo launchers and the release check
docs/              this documentation
```

**Branches.**
- **`main`:** the simulator. Science, experiments and results happen here.
- **`site-dev`:** the draft of the public website. It adds the FIRENET/AgniWare bar, the guided tour and the mobile
  layout, and hides the live engine. Its own notes are in `docs/site/` on that branch.
- **`site-live`:** what `dashboard.firenet.live` serves. It changes only by a pull request from `site-dev`.

Science updates reach the site by merging `main` into `site-dev`. The release 1.0 tag is `v1.0.0`.

**Documents.**
- **Logs of record:** `PROGRESS.md` (what each session did), `DECISIONS.md` (every choice with its reason),
  `KNOWN_ISSUES.md` (parked modules and backlog).
- **This folder:** [../README.md](../README.md) is the map.
- **The build story, phase by phase:** [../journey/README.md](../journey/README.md).
- **Unfamiliar terms:** [03-glossary.md](03-glossary.md).

## 13. Known limits and open items

- **Detection below the report.** P2's detection rate is below the report's interval in legacy mode; this is treated
  as sampling (section 9.3).
- **M28 common-mode exclusion.** It can miss a second network-wide rise that comes straight after a long one (seed
  22).
- **Small sensor offsets.** An offset of about 1.5 su is not caught by the M29 neighbour check; larger offsets, stuck
  sensors and dropouts are.
- **Stuck sensors.** A stuck sensor can raise one candidate before it abstains (about an hour, SIM).
- **Illustrative, not measured.** The landscape, the non-India Regime Cards, the satellite overpass times and the
  lightning relaxation of SCMR are assumptions.

Each item, with its diagnosis and proposed fix, is in `KNOWN_ISSUES.md`.
