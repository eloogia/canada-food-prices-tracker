#!/usr/bin/env bash
# Reproduce everything: download -> clean -> provinces -> data quality -> SQL -> charts -> (R)
set -euo pipefail
cd "$(dirname "$0")"
python src/download.py
python src/clean.py
python src/provinces.py
python src/data_quality.py
python src/run_sql.py
python src/charts.py
if command -v Rscript >/dev/null 2>&1; then
  Rscript r/quebec_vs_canada.R
else
  echo "Rscript not found: skipping the optional R step."
fi
