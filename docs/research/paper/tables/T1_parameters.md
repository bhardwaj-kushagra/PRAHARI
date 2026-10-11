# T1 parameters

Model parameters and their provenance (inputs, not results). Source: `configs/experiments/golden.yaml` (with `configs/default.yaml`) and the M20b block of `configs/research/r2.yaml`; provenance tags as in the charter.

| Eq. | Meaning | Key | Value | Provenance |
| --- | --- | --- | --- | --- |
| — | nodes | world.n_nodes | 100 | ASM; illustrative landscape; grid layout and spacing as in the report simulation |
| — | grid spacing (m) | world.spacing_m | 70 | ASM; illustrative landscape; grid layout and spacing as in the report simulation |
| M30 | neighbourhood radius R / spacing | world.radius_factor | 1.6 | ASM; illustrative landscape; grid layout and spacing as in the report simulation |
| M19 | noise memory φ | sensor.ar_phi | 0.95 | ASM; SPEC §5.6 M18–M19, matching reference/prahari_simulation.py |
| M19 | noise level σ (su) | sensor.sigma_e | 0.05 | ASM; SPEC §5.6 M18–M19, matching reference/prahari_simulation.py |
| M19 | daytime noise factor | sensor.het_extra | 0.6 | ASM; SPEC §5.6 M18–M19, matching reference/prahari_simulation.py |
| M18 | drift per minute (su) | sensor.drift_step_sd | 0.002 | ASM; SPEC §5.6 M18–M19, matching reference/prahari_simulation.py |
| M18 | heavy-tail degrees of freedom | sensor.tail_df | 3 | ASM; SPEC §5.6 M18–M19, matching reference/prahari_simulation.py |
| M20 | roadside nuisance events per day | nuisance.rate_roadside_per_day | 1 | ASM; SPEC §5.6 M20, matching reference/prahari_simulation.py |
| M20 | other nuisance events per day | nuisance.rate_other_per_day | 0.2 | ASM; SPEC §5.6 M20, matching reference/prahari_simulation.py |
| M20 | haze episodes per 10 days | haze.base_rate_per_10d | 1 | ASM; SPEC §5.6 M18/M20, matching reference/prahari_simulation.py |
| M20 | episode duration (min) | haze.duration_range | [180, 720] | ASM; SPEC §5.6 M18/M20, matching reference/prahari_simulation.py |
| M20 | episode amplitude (su) | haze.amp_range | [0.8, 2.5] | ASM; SPEC §5.6 M18/M20, matching reference/prahari_simulation.py |
| M24 | slow baseline time constant (min) | ttc.slow_tau_min | 720 | LIT M24/M25 and the report simulation (reference/prahari_simulation.py); ASM stub warm-up; LIT detect_on slow = scores() C_slow |
| M24 | freeze threshold | ttc.freeze_z | 3 | LIT M24/M25 and the report simulation (reference/prahari_simulation.py); ASM stub warm-up; LIT detect_on slow = scores() C_slow |
| M26 | conformal time-of-day bins | qcc.bins | 6 | LIT M26 and the report simulation; ASM sliding option; LIT form robust_z = gauss_z() |
| M26 | calibration days | qcc.cal_days | 14 | LIT M26 and the report simulation; ASM sliding option; LIT form robust_z = gauss_z() |
| M28 | CUSUM reference value (−ln p scale) | cusum.k_node | 1.5 | TGT ARL 30 d and r = 1/30 d; LIT M28 and the report simulation; DER h_default (oracle mean tuned h); LIT statistic z, k_z (KS) |
| M28 | default node target r (per node per 30 d) | cusum.target_per_node_30d | 1 | TGT ARL 30 d and r = 1/30 d; LIT M28 and the report simulation; DER h_default (oracle mean tuned h); LIT statistic z, k_z (KS) |
| M28 | common-mode share of nodes | cusum.cm_frac | 0.25 | TGT ARL 30 d and r = 1/30 d; LIT M28 and the report simulation; DER h_default (oracle mean tuned h); LIT statistic z, k_z (KS) |
| M30 | cluster window W (min) | cluster.window_min | 30 | ASM; report simulation (window); LIT M30 and the report simulation (form) |
| M31 | default SCMR ratio ρ (R2–R4: a knob) | scmr.ratio_min | 3 | LIT M31 and the report simulation; ASM lightning relaxation (SPEC M31) |
| M20b | gain sd | m20b.gain_sd | 0.3 | DATA; N5 unattributed events, amplitude CV 0.25–0.34 (real_thompson2026.json) |
| M20b | gain corr len m | m20b.gain_corr_len_m | 200 | ASM; correlation length of the node-gain field |
| M20b | gain corr rho | m20b.gain_corr_rho | 0.7 | ASM; share of the gain spread that is spatially correlated |
| M20b | gain clip | m20b.gain_clip | [0.3, 2.0] | ASM |
| M20b | uneven s range | m20b.uneven_s_range | [0.1, 0.6] | DATA; per-episode spread s_e (CV ≈ 0.1–0.66; Stuttgart median 0.42) |
| M20b | night share | m20b.night_share | 0.7 | DATA; 7 of 10 real unattributed events start 20:00–08:00 |
| M20b | night window | m20b.night_window | [1200, 480] | DER; 20:00–08:00 local (minute of day; run start 00:00) |
| M20b | coverage full prob | m20b.coverage_full_prob | 0.5 | DATA; N5 events involved 50–100% of stations |
| M20b | coverage partial range | m20b.coverage_partial_range | [0.3, 1.0] | DATA |
| M20b | swath edge m | m20b.swath_edge_m | 20 | ASM |
| M20b | outside floor | m20b.outside_floor | 0.1 | ASM |
| M20b | network width m | m20b.network_width_m | 630 | DER; 10 × 70 m grid, 9 spacings |
| M20b | front speed ms | m20b.front_speed_ms | [1, 6] | DATA; N5 onset spreads 5–35 min over km-scale networks (ASM at 70 m) |
| M20b | jitter max range min | m20b.jitter_max_range_min | [0, 60] | DATA; Stuttgart onsets spread 15–140 min (size at 70 m: ASM) |
