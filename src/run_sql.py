"""Load the processed CSVs into SQLite and run every query in sql/analysis.sql.

Tables: prices      <- data/processed/staples_prices.csv   (src/clean.py)
        prov_prices <- data/processed/provinces_prices.csv (src/provinces.py)

Creates data/prices.sqlite (git-ignored, rebuilt each run) and writes one CSV
per named query to outputs/sql/.
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    "prices": ROOT / "data" / "processed" / "staples_prices.csv",
    "prov_prices": ROOT / "data" / "processed" / "provinces_prices.csv",
}
DB = ROOT / "data" / "prices.sqlite"
SQL = ROOT / "sql" / "analysis.sql"
OUT = ROOT / "outputs" / "sql"


def split_named_blocks(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"^-- name:\s*(\S+)\s*$", text, flags=re.M)
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def main() -> None:
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    for table, csv in TABLES.items():
        df = pd.read_csv(csv)
        df.to_sql(table, con, index=False)
        con.execute(f"CREATE INDEX ix_{table} ON {table} (geo, product, ref_date)")
        print(f"Loaded {len(df):,} rows into {table} in {DB.relative_to(ROOT)} (SQLite {sqlite3.sqlite_version})")

    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in split_named_blocks(SQL.read_text()):
        if name.startswith("setup"):
            con.executescript(body)
            continue
        res = pd.read_sql_query(body, con)
        res.to_csv(OUT / f"{name}.csv", index=False)
        print(f"  {name}: {len(res)} rows -> outputs/sql/{name}.csv")
    con.close()


if __name__ == "__main__":
    main()
