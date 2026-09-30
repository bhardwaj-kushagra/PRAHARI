# Thompson et al. (2026) — N5 ground smoke sensors, Canada (public data, REAL)

- **Paper:** D. K. Thompson, G. Fusina, P. Jackson, "Evaluation of Ground-Based Smoke Sensors for Wildfire Detection
  and Monitoring in Canada", *Fire* 9(4):141, 2026.
- **Data:** Zenodo record [10.5281/zenodo.18222779](https://doi.org/10.5281/zenodo.18222779), concept DOI
  10.5281/zenodo.18202275. It archives `github.com/nrcan-cfs-fire/Ground-smoke-sensors` at tag `2026-01-12`.
- **Licence:** MIT (Copyright 2026 Canadian Forest Service – Fire Research). The licence text is in the archive
  (`LICENSE`).
- **Retrieved:** 2026-09-30 by `scripts/fetch_thompson2026.sh`. SHA-256 of the zip:
  `87108e2449b9e4524582f5cdb779cea2deb95f5e63ff1c91159cdd586f792b8f`.
- **Storage:** the raw zip is kept unmodified under `raw/` and not committed (`.gitignore`); the fetch script restores
  it and checks the checksum.

## What is used

**`WR.csv`:** 262,675 rows from 40 N5 sensors, 1–30 April 2024.

- Columns: `UnixTime`, `stationID`, `T`, `RH`, `P`, `PM1P0`, `PM2P5`, `PM4P0`, `PM10P0`, and the vendor scores
  `discrepancy_particle` and `discrepancy_gas`.
- Readings every 5 minutes (median spacing 294–307 s).
- The sensors sit in site clusters: WR (Wainwright, AB; 10), BC (Quebec, 49.2° N 68.2° W; 10), VC (Valcartier, QC;
  about 9), RC (Rock Creek, BC; 6), MR (3), KM (2).
- `discrepancy_gas` is zero almost everywhere, so the analysis uses PM₂.₅.

**Other files:**

- **`Sensor_Locs.csv`:** station coordinates and names.
- **`WainwrightApr2024.csv`:** 16 Wainwright fires (wildfires and prescribed burns) with ignition times (UTC−7), areas
  and first N5 warning and alert.
- **`all_alerts.csv`:** N5 warning and alert logs at Wainwright.

The manuscript approximates N5's warnings as PM₂.₅ above 30 µg/m³ and its alerts as above 200 µg/m³ (vendor
algorithms).

**Not in this release:** the June 2023 Valcartier regional-smoke episode that the paper discusses. Only its fire list
(`Valcartier2023.csv`) is included.

## Rules (paper-branch charter, rule 7)

- The raw data are never edited; every derivation is a script in `engine/prahari/research/realdata.py`.
- Values used to set simulation parameters are tagged `DATA` and are never used to validate those same parameters.
- The analysis is exploratory, and its plan is fixed in `docs/research/realdata-plan.md` before it runs.
