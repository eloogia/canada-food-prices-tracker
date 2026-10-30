"""Download the full Statistics Canada table 18-10-0245-01 (CSV, English).

Table: Monthly average retail prices for selected products
Page:  https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810024501
Licence: Statistics Canada Open Licence
         https://www.statcan.gc.ca/en/reference/licence

Usage:  python src/download.py          (skips the download if files exist)
        python src/download.py --force  (always re-download)
"""
import argparse
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://www150.statcan.gc.ca/n1/tbl/csv/18100245-eng.zip"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
FILES = ("18100245.csv", "18100245_MetaData.csv")


def main(force: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and all((RAW_DIR / f).exists() for f in FILES):
        print(f"Raw files already in {RAW_DIR} (use --force to refresh).")
        return
    print(f"Downloading {URL} ...")
    resp = requests.get(URL, timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in FILES:
            zf.extract(name, RAW_DIR)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (RAW_DIR / "DOWNLOADED_AT.txt").write_text(f"{URL}\n{stamp}\n")
    size_mb = (RAW_DIR / FILES[0]).stat().st_size / 1e6
    print(f"Saved {FILES[0]} ({size_mb:.1f} MB) and metadata to {RAW_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    main(ap.parse_args().force)
