# Phase 1 — World, network and siting

## Goal

Give the simulation a place: a landscape with the features where people start fires, a map of ignition likelihood,
three ways to place 100 nodes, and the radio link from each node to the gateway.

## What was built

- Three **setup modules** that run once before the first tick, each with a stub and the same isolation as tick stages:
  `landscape` (M2 distance fields, M3 likelihood), `siting` (M1 grid and corridor, M4 greedy) and `links` (M38 path
  loss without shadowing).
- A 1400 m Terai-style landscape: a village, two footpaths, a road and a power line.
- Header additions (additive): interfaces, likelihood raster, all three layouts with covered likelihood, per-node links.
- Dashboard: layout toggle with coverage and a preview of layouts not simulated; layers for interfaces, likelihood,
  radio links by SF, detection radius and satellite pixels.
- Scenarios `siting_corridor` and `siting_greedy`.

## How it works

Each interface contributes an exponentially decaying term to λ(x). Greedy siting repeatedly picks the 10 m cell that
adds the most uncovered likelihood within the 50 m detection radius. Path loss follows the forest calibration
(100 dB at 200 m, 120 dB at 400 m), and each node gets the lowest spreading factor that closes the link.

## Challenges and issues

1. **The original map was too small to be interesting.** On a 700 m map, 100 nodes at 70 m covered 100% of it, and every
   node reached the gateway at SF7, so layouts and radio colours would all look the same.
2. **Corridor lines too short for 100 nodes.** The footpaths and village edge could not hold 100 nodes at the nominal
   spacing.
3. **Villages are not forest.** Nodes and fires must not be placed inside the village polygon, but the village still
   raises risk around it.
4. **Determinism of greedy.** Ties between equally good cells could make siting depend on floating-point order.
5. **Nodes out of radio reach.** The greedy layout leaves 35 nodes without a direct link to the gateway.

## Decisions and trade-offs

| Decision | Pros | Cons |
| --- | --- | --- |
| 1400 m landscape with the grid centred; the report's 100 nodes at 70 m unchanged (P1-1) | layouts and SFs now differ meaningfully | earlier smoke fire moved to keep its relative position |
| Illustrative landscape tagged ASM (P1-2) | honest; easy to explain | not a real place |
| Corridor spacing shrinks to L/N when lines are short (P1-5) | exactly N nodes, deterministic | spacing on corridors is 35 m, not 70 m |
| Village cells have λ = 0 and cannot host nodes, but raise λ nearby (P1-3) | realistic | one more rule in the siting code |
| Greedy on a raster with lowest-index tie-break (P1-6) | deterministic, no random stream needed | resolution limited to 10 m |
| Flag unreachable nodes "needs a relay" instead of hiding them (P1-8) | honest; motivates Phase 8 | the greedy map shows grey rings |
| One-hue ordinal ramp for SF, validated for contrast (P1-9) | readable, colour-blind safe | needs a legend |

## Resolution

All resolved in the phase. Relays for unreachable nodes are planned for Phase 8 (comms).

## Acceptance results

| Test | Result (SIM) |
| --- | --- |
| Greedy covers at least as much likelihood as the grid at equal N | yes on the default and a synthetic landscape; greedy also ≥ (1 − 1/e) of a brute-forced optimum |
| Distance fields and M38 reference values | 100 dB at 200 m, 120 dB at 400 m; SF boundaries 746/828/919/1020/1112/1213 m |
| Covered likelihood, 100 nodes, 50 m radius | grid 24%, corridor 49%, greedy 83% |

## What to show

`siting_greedy`: switch layouts with the toggle and read the coverage percentages; turn on *Radio links*.
