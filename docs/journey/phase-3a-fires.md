# Phase 3a — Fires and plumes (legacy)

## Goal

Start fires where people are, make them grow, carry their smoke downwind to the nodes, and show it on the map, using
the report's legacy models so the golden numbers stay reproducible.

## What was built

- `ignition` real: scripted fires plus Poisson ignition attempts drawn from the likelihood map with a day/night
  activity profile, each kept with the sustained-ignition probability p_s(FFMC) (M8).
- The legacy growth (M9) and plume (M12, M13, M16) models remain the default stubs, tested against their acceptance
  values.
- Recordings carry a coarse plume grid (10 m, float16) every 5 ticks while fires burn, and the fire signal at each
  node.
- Dashboard: smoke overlay on a log scale, nodes that glow with the smoke they receive, fire markers with wind arrows.
- Scenario `fires_day`.

## How it works

Ignition attempts are simulated by *thinning*: candidates are drawn uniformly at a rate that bounds the true rate,
then accepted with probability proportional to the local likelihood and the time-of-day activity. Accepted fires grow
over tens of minutes; each node's smoke depends on distance, wind direction relative to the fire, and a travel delay.

## Challenges and issues

1. **Scaling the ignition rate.** The expected number of fires per day depends on activity, likelihood and fuel
   dryness together.
2. **Which smoke model is "real"?** The SPEC makes the legacy form of a model its default so the report can be
   reproduced; the upgrades (M10, M11) are optional.
3. **Showing smoke without bloating recordings** or breaking the run if the display grid fails.
4. **Colours**: smoke, likelihood, radio links and node states all need distinct, readable colours.
5. **Test flakiness** for the day/night ignition pattern with small counts.

## Decisions and trade-offs

| Decision | Pros | Cons |
| --- | --- | --- |
| Legacy growth and plume stay the default stubs (P3a-1) | golden numbers reproducible | the "real" upgrade is opt-in |
| λ₀ scaled so the expected count is met at a reference FFMC of 90 (P3a-3) | an intuitive `expected_fires` setting | the realised count varies with actual dryness (documented) |
| Plume grid is display-only, float16, every 5 ticks, failures dropped silently (P3a-5) | small files, never breaks a run | coarse, 5-minute resolution |
| One slate hue for smoke on a log scale (P3a-6) | distinct from likelihood, links and node states | needs a legend |
| Day/night test uses a binomial bound rather than a fixed ratio | stable test | a slightly weaker assertion |

## Resolution

All resolved in the phase.

## Acceptance results

| Test | Result (SIM) |
| --- | --- |
| 50 m straight downwind, full growth | 2.5 su |
| 50 m straight upwind | 0.25 su |
| Arrival delay = distance / wind speed | exact to the tick for three distance and speed pairs |
| M8 and Poisson ignitions | p_s(84) = 0.5; counts within Poisson bounds; none in the village; clustered near interfaces |

## What to show

`fires_day`: turn on *Smoke*; watch plumes follow the wind and nodes glow as smoke reaches them.
