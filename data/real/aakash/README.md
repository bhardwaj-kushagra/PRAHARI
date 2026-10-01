# Aakash project (RIHN) — hourly CUPI-G PM₂.₅ and CO, north-west India, September–November 2022–2024

- **Source:** Aakash project, Research Institute for Humanity and Nature (RIHN), Kyoto —
  https://aakash-rihn.org/en/data-set/ (hourly zips `1H_<year>0901_<year>1130.zip`).
- **Network:** 32 Compact and Useful PM₂.₅ Instruments with Gas sensors (CUPI-G, Panasonic/Nagoya University) from
  Punjab to Delhi. Described in Singh et al., *Sci Rep* 13, 13201 (2023), doi:10.1038/s41598-023-39471-1.
- **Licence:** Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
  - Used here for non-commercial research with attribution.
  - **The data and any modified version are not redistributed:** raw files stay in `raw/` (gitignored), and only
    aggregate statistics are published.
  - The provider encourages users to contact the project leader; that contact is the developer's to make.
- **Retrieval:** `python scripts/fetch_aakash.py` (re-running verifies checksums). URLs, SHA-256, sizes and retrieval
  times are in `manifest.json`.
- **Use:** cluster AK of `docs/research/realdata-plan.md` addendum C (REAL, exploratory).
