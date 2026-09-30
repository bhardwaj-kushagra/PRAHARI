#!/usr/bin/env bash
# Fetch the public data of Thompson, Fusina & Jackson (2026), "Evaluation of Ground-Based Smoke Sensors for Wildfire
# Detection and Monitoring in Canada", Fire 9(4):141 — Zenodo record 10.5281/zenodo.18222779 (MIT licence), the
# archive of github.com/nrcan-cfs-fire/Ground-smoke-sensors at tag 2026-01-12. The raw zip is not committed; this
# script restores it byte for byte (checksum verified).
set -euo pipefail
cd "$(dirname "$0")/.."
out=data/real/thompson2026/raw/Ground-smoke-sensors-2026-01-12.zip
sha=87108e2449b9e4524582f5cdb779cea2deb95f5e63ff1c91159cdd586f792b8f
mkdir -p "$(dirname "$out")"
if [ ! -f "$out" ]; then
  curl -fsSL -A "Mozilla/5.0" -o "$out" \
    "https://zenodo.org/api/records/18222779/files/nrcan-cfs-fire/Ground-smoke-sensors-2026-01-12.zip/content"
fi
echo "$sha  $out" | sha256sum -c -
