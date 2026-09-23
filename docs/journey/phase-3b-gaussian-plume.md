# Phase 3b — Gaussian plume (optional upgrade)

## Goal

Offer a more physical smoke model behind the same `plume` interface, and show that switching models is a
configuration change.

## What was built

- `fire/gaussian.py`: a ground-reflected Gaussian plume (M11) with Briggs dispersion coefficients by stability class
  (M14), a reduced wind under the canopy (M15) and the travel delay (M16); `calibrate_q()` sets the source strength.
- Scenario `fires_day_gaussian`: identical seed, fires and weather as `fires_day`, only the plume differs.
- The model card now shows each stage's notes (here the calibrated source strength).

## How it works

Concentration falls with a bell-shaped profile across the wind and a width that grows with distance; stability class C
by day and E at night. The source strength is calibrated so a legacy-strength fire gives the same 2.5 su at 50 m
downwind as the legacy model at the reference wind.

## Challenges and issues

1. **Legacy or Gaussian by default?** The Gaussian model is more physical but narrows plumes sharply (about 5.5 m wide
   at 50 m by day), which changes which nodes see smoke, and the golden runs need the legacy model.
2. **Upwind nodes see nothing** in a pure Gaussian plume, unlike the legacy model's 0.25 su floor.
3. **Near-field blow-up**: the formula can give extreme values very close to the source.

## Decisions and trade-offs

| Decision | Pros | Cons |
| --- | --- | --- |
| Legacy stays default; scenarios opt in with `plume: real` (P3b-1) | golden reproducible; easy A/B | the better model is not the default |
| Upwind floor of 10% of the centreline value (P3b-2) | keeps the legacy 0.25 su upwind behaviour | an assumption (ASM) |
| Source scaled to match the legacy calibration (P3b-3) | comparable magnitudes | concentration now depends on wind speed, unlike legacy |
| Model-card notes from each stage's snapshot (P3b-5) | calibrated values visible | an extra header field (additive) |

## Resolution

All resolved; near-field values are tested to stay finite (below 50 su within 10 m). A failing Gaussian stage
degrades to the legacy model and the run continues (tested).

## Acceptance results

| Test | Result (SIM) |
| --- | --- |
| Calibrated 50 m downwind equals the legacy value | 2.5 su |
| Crosswind profile matches the tabulated σ_y | within 0.1% from 0 to 2σ_y |
| Switching real ↔ stub works | identical fires, only the plume differs; failure degrades cleanly |

## What to show

Open `fires_day` and `fires_day_gaussian` one after the other at the same time: same fires, different plume shapes.
