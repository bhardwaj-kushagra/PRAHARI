# Test fixtures

## `cffdrs_fwi_01.csv`

Reference outputs of the official Canadian Forest Fire Danger Rating System R package **cffdrs**
(`fwi(test_fwi)`, default start-up codes FFMC 85, DMC 6, DC 15), copied unchanged from
`https://github.com/cffdrs/cffdrs_r/blob/master/tests/testthat/data/fwi_01.csv` on 2026-09-23.
cffdrs is distributed under GPL-2; this file contains only the package's published numeric test outputs.

Columns: `LONG, LAT, YR, MON, DAY, TEMP` (°C, noon), `RH` (%), `WS` (km/h), `PREC` (mm, 24 h), then the FWI
System codes. Values are rounded to 4 significant figures. PRAHARI-SIM uses the `FFMC` column to verify M7
(SPEC §5.2): the daily chain must match within 0.1.
