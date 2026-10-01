# CPCB Delhi PM₂.₅ through the OpenAQ v3 API — 2025 season (and the 2017 provenance window)

- **Source:** Central Pollution Control Board (CPCB) continuous ambient air quality monitoring stations, accessed
  through OpenAQ (https://openaq.org, API v3, provider "CPCB", id 168).
- **Licence:** **none listed by OpenAQ** for these locations (checked 1 Oct 2026: every CPCB location's `licenses`
  field is empty, and OpenAQ's licence table has no Indian government licence).
  - The developer decided on 1 Oct 2026 to use the data as public Government of India monitoring data (DECISIONS
    P-9). This is stated in the paper's limits.
  - Raw responses are **not redistributed** (`raw/` is gitignored).
  - Credit: CPCB (source) and OpenAQ (platform), as OpenAQ's terms of use require.
- **Selection:** `shortlist.json` (metadata only, committed before any measurement was fetched) lists the CPCB PM₂.₅
  locations within 25 km of 28.6129° N, 77.2295° E, every PM₂.₅ sensor's date range, and the sensor chosen per season.
- **Retrieval:**
  - `python scripts/fetch_openaq_cpcb.py fetch`, and `provenance --sensors …`;
  - the key comes from the `OPENAQ_API_KEY` environment variable and is never stored;
  - pages, SHA-256, sizes and retrieval times are in `manifest.json`.
- **Use:** cluster DL15 and the provenance check of `docs/research/realdata-plan.md` addendum C (REAL, exploratory).
