# 3. Glossary

Alphabetical. "M-number" refers to an equation in [`SPEC.md`](../SPEC.md) §5; the
[models page](../architecture/03-models.md) says where each lives in the code.

| Term | Meaning |
| --- | --- |
| **Ablation** | A PRAHARI variant with one mechanism replaced by its stub (P2-QCC, P2-TTC, P2-SCMR, P2-RAQ), run to show what that mechanism contributes. |
| **Anchor** | In the legacy edge form, the new candidate around which a cluster is formed. |
| **ARL (average run length)** | Average time a quiet detector runs before a false alarm. P1's h ≈ 8.8 targets 30 days under textbook assumptions (M23). |
| **ASM, DER, LIT, TGT, VEN** | Provenance tags on every parameter: ASM assumption, DER derived by calculation, LIT literature, TGT design target, VEN vendor datasheet. |
| **Bayes factor (BF)** | How much more likely the data are under "fire" than "no fire". PRAHARI uses an upper bound computed from a p-value (M34). |
| **Calibration days** | The first 14 days of a run, used to build each node's QCC reference set (M26, M46). |
| **Candidate** | A node whose CUSUM crossed its threshold h. Shown as a pulsing ember dot on the map. Not yet an alarm. |
| **cffdrs** | The Canadian Forest Fire Danger Rating System software; its published test outputs verify M7. |
| **Cluster** | Candidate nodes within R of each other in the last 30 minutes (M30). |
| **Common mode** | An event that raises many nodes at once (haze, weather). Excluded from threshold tuning (M28) and rejected by SCMR (M31). |
| **Confirmed / confirmation** | A cluster that passed the edge decision: SCMR and the RAQ rule (legacy: 2 agreeing nodes within R on dry, busy days, 3 on wet, quiet days; M31, M34). |
| **Conformal p-value** | A p-value computed by ranking a new score among past scores; valid without assuming a distribution (M26). |
| **Contract** | A data class that one stage passes to the next (for example `Residuals`, `PValues`); fields may only be added. |
| **CUSUM** | Cumulative-sum detector: G ← max(0, G + score − k); a candidate when G > h (M23, M28). |
| **Degraded** | A module whose real version failed (exception or invalid output) and now runs its stub; shown in the health table. |
| **Edge layer** | Decisions made at the gateway over many nodes (M30–M35). |
| **EWMA** | Exponentially weighted moving average; the slow baseline of M23/M24. |
| **Exceedance** | Share of p-values at or below a level; for a calibrated p-value at 1% it should be about 1% (Phase 5 acceptance 1). |
| **FFMC** | Fine Fuel Moisture Code, a daily index of litter dryness (M7). |
| **Fisher's method** | Combining k p-values via X = −2 Σ ln p, chi-square with 2k degrees of freedom (M32). |
| **Floor (p_min)** | The smallest possible conformal p-value, 1/(n + 1) for a calibration set of size n. |
| **Frame** | One recorded snapshot of the simulation at a tick: weather, node values, events, alerts, health. |
| **Freeze cap** | M24's rule that a frozen slow baseline resumes (with clipped updates) after 180 minutes. |
| **Golden test / golden numbers** | Reproduction of the report's published results in legacy mode (SPEC §9.3). |
| **h** | CUSUM threshold. P1 uses 8.8; PRAHARI tunes it by replay (M28); `h_default` is used before tuning. |
| **Haze** | Regional smoke or pollution raising all nodes together for hours (M20). |
| **Health weight (c)** | A 0–1 weight discounting a suspect node (M29; the stub uses 1). |
| **Incident** (escalation) | A tracked group of clusters in one place, with a level that only rises until it clears after 120 min without candidates (M35). Not the same as an M46 counting incident. |
| **Incident** | Alarms merged within 60 minutes and 2R into one event for counting (M46). |
| **Isolation / Slot** | The wrapper that runs every stage and falls back to its stub, then off, then the last good output, if it fails. |
| **k** | CUSUM allowance subtracted each step: 0.5 on the z scale (P1), 1.5 on the −ln p scale (PRAHARI). |
| **Legacy form** (edge) | The report simulation's edge decision: around each new candidate, count agreeing neighbours, test SCMR against the network, apply the day-type quorum (DECISIONS N-b, P6-2). |
| **Legacy mode** | The model choices that reproduce the report (M9, M12, M17 linear, legacy prior and quorum). |
| **Live mode** | The dashboard streaming frames from the optional FastAPI server instead of a file; mechanism switches then reconfigure the running engine. |
| **LoRaWAN, SF** | Long-range low-power radio network; SF (spreading factor 7–12) trades rate for range (M38–M40). |
| **Maturity** | The growth of QCC calibration sets, which lowers the floor and strengthens evidence over the first weeks. |
| **Model card** | The table in the dashboard listing each module, its equation, tag, state and notes. |
| **MOX sensor** | Metal-oxide gas sensor; cheap, sensitive to smoke and to temperature and humidity (M17). |
| **Node layer** | Per-node processing: TTC, QCC, score, CUSUM (M24–M29). |
| **Nuisance event** | A short spike not caused by fire (vehicle, cooking) (M20). |
| **Off** | A module state that switches the module out entirely (not allowed for weather, growth, sensor, siting). |
| **Offline replay** | Phase 7 harness technique: record each minute's node evidence and candidates once, then feed them through edge variants or re-tuned thresholds without simulating the world again. |
| **Operating dial** | The trade-off between false incidents and time to confirm, traced by re-tuning the node threshold h for several false-candidate targets (1 per 60, 30, 14 and 7 days per node). |
| **Oracle** | `reference/prahari_simulation.py`, the report's original simulation, used to check the engine. |
| **Overdispersion** | More seed-to-seed variation than a Poisson model predicts, because false alarms cluster. |
| **P0, P1, P1t, P2** | Pipelines: fixed threshold; v1 as written; v1 replay-tuned; PRAHARI. |
| **Per-fire wind** | Legacy fire-injection option (`plume.wind: per_fire`): each protocol fire has its own constant random wind, as in the report's simulation. |
| **Preset (experiment)** | A YAML file in `configs/experiments/` naming pipelines, seeds and options for `prahari experiment` (golden, ablation, spacing, seeds20). |
| **Prior / prior odds** | Chance of a fire before looking at sensors, from activity and dryness (M33). |
| **QCC** | Quantile-calibrated conformal p-values (M26). |
| **Quiet pass / fire pass** | The two runs per seed in an experiment: without fires (false alarms) and with scripted fires (detection). |
| **R** | Neighbourhood radius, 1.6 × node spacing (112 m at 70 m spacing). |
| **RAQ** | Risk-adaptive quorum: the Bayes decision that sets how many nodes must agree today (M34). |
| **Real / stub / off** | The three states of every module, chosen in YAML configuration. |
| **Recording** | A gzipped JSON-lines file (`*.prs.jsonl.gz`): header, frames, traces, footer. |
| **Refractory** | 30 minutes after a candidate during which the node cannot raise another. |
| **Replay tuning** | Finding h by rerunning the CUSUM over stored tuning-day scores (M28). |
| **SCMR** | Spatial common-mode rejection: a cluster must be ≥ 3× more active than the network (M31). |
| **Seed** | The master random number; the same seed gives a byte-identical recording. |
| **SIM** | Label on every simulated value; nothing here is field data. |
| **SRP** | The prior module (M33). |
| **Stage** | One replaceable step of the model (for example `qcc`), registered with its real, stub and off versions. |
| **su (sensor units)** | The simulator's unit for sensor output; 2.5 su is a fully grown fire 50 m downwind. |
| **Trace (evidence trace)** | A record explaining a candidate or a decision: p-values, CUSUM, SCMR, Fisher, prior, rule used. |
| **TTC** | Two-timescale conditioning: slow baseline plus fast lagged residual (M24, M25). |
| **Tuning days** | Days 15–28 of a run, used to tune h (M28). |
| **Variant recording** | A recording of the same scenario and seed with one module switched, named `<scenario>__<module>-<state>`; used by the mechanism switches in replay. |
| **Warm start** | Simulating from day 0 but recording from a later day (`record.from_day`), to show a mature network. |
| **z-score** | (reading − baseline) / spread. |
