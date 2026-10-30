"""Load the processed CSV into SQLite and run every query in sql/analysis.sql.

Creates data/prices.sqlite (git-ignored, rebuilt each run) and writes one CSV
per named query to outputs/sql/.
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "processed" / "staples_prices.csv"
DB = ROOT / "data" / "prices.sqlite"
SQL = ROOT / "sql" / "analysis.sql"
OUT = ROOT / "outputs" / "sql"


def split_named_blocks(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"^-- name:\s*(\S+)\s*$", text, flags=re.M)
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def main() -> None:
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    df = pd.read_csv(CSV)
    df.to_sql("prices", con, index=False)
    con.execute("CREATE INDEX ix_prices ON prices (geo, product, ref_date)")
    print(f"Loaded {len(df):,} rows into {DB.relative_to(ROOT)} (SQLite {sqlite3.sqlite_version})")

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
