# CPCB continuous monitoring data for India, 2015–2019 (Princeton archive) — Delhi-NCR PM₂.₅ files

- **Source:** Sharma, D. and Mauzerall, D. (2021). *CPCB continuous monitoring air quality data for India, from
  2015–2019* [Data set]. Princeton University. https://doi.org/10.34770/60j3-yp02 — compiled from the Central
  Pollution Control Board's CCR portal (https://app.cpcbccr.com/ccr/).
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0), as stated by the repository.
- **Files used:**
  - `pm25_ccr_copy/Delhi*` and the Haryana and Uttar Pradesh files of the NCR districts around Delhi;
  - one CSV per station (Delhi) or city, with `Lat`/`Lon` added by the compilers from Google Maps.
- **Retrieval:** `python scripts/fetch_cpcb_princeton.py` (re-running verifies checksums). URLs, SHA-256, sizes and
  retrieval times are in `manifest.json`. Raw files stay in `raw/` (gitignored).
- **Use:** cluster DL of `docs/research/realdata-plan.md` addendum C (REAL, exploratory) and the provenance check.
