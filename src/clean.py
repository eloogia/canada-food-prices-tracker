"""Clean the raw StatCan table and keep a tidy subset of ~20 food staples.

Input : data/raw/18100245.csv   (run src/download.py first)
Output: data/processed/staples_prices.csv
        one row per (month, geography, product) with the average price in CAD.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "18100245.csv"
OUT = ROOT / "data" / "processed" / "staples_prices.csv"

# Analysis window: Jan 2020 is kept only so 2021 year-over-year changes can
# be computed; the analysis itself is based on January 2021 = 100.
START = "2020-01"

GEOS = ["Canada", "Quebec", "Ontario", "Alberta", "Saskatchewan"]

# Exact product names as published in the table (after stripping the stray
# trailing spaces StatCan has on some names) -> short label, category.
STAPLES = {
    "Eggs, 1 dozen": ("Eggs (12)", "Dairy & eggs"),
    "Milk, 4 litres": ("Milk (4 L)", "Dairy & eggs"),
    "Butter, 454 grams": ("Butter (454 g)", "Dairy & eggs"),
    "Block cheese, 500 grams": ("Block cheese (500 g)", "Dairy & eggs"),
    "Whole chicken, per kilogram": ("Whole chicken (kg)", "Meat"),
    "Chicken breasts, per kilogram": ("Chicken breasts (kg)", "Meat"),
    "Ground beef, per kilogram": ("Ground beef (kg)", "Meat"),
    "Pork loin cuts, per kilogram": ("Pork loin (kg)", "Meat"),
    "Bacon, 500 grams": ("Bacon (500 g)", "Meat"),
    "White bread, 675 grams": ("White bread (675 g)", "Bakery & grains"),
    "White rice, 2 kilograms": ("White rice (2 kg)", "Bakery & grains"),
    "Dry or fresh pasta, 500 grams": ("Pasta (500 g)", "Bakery & grains"),
    "Wheat flour, 2.5 kilograms": ("Wheat flour (2.5 kg)", "Bakery & grains"),
    "White sugar, 2 kilograms": ("White sugar (2 kg)", "Pantry"),
    "Roasted or ground coffee, 340 grams": ("Coffee (340 g)", "Pantry"),
    "Canola oil, 3 litres": ("Canola oil (3 L)", "Pantry"),
    "Potatoes, 4.54 kilograms": ("Potatoes (4.54 kg)", "Produce"),
    "Carrots, 1.36 kilograms": ("Carrots (1.36 kg)", "Produce"),
    "Apples, per kilogram": ("Apples (kg)", "Produce"),
    "Bananas, per kilogram": ("Bananas (kg)", "Produce"),
}


def load_raw(path: Path = RAW) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df["Products"] = df["Products"].str.strip()
    df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
    return df


def tidy(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[
        df["GEO"].isin(GEOS)
        & df["Products"].isin(STAPLES)
        & (df["REF_DATE"] >= START)
    ].copy()

    missing = set(STAPLES) - set(sub["Products"])
    assert not missing, f"Products not found in table (renamed?): {missing}"
    assert (sub["UOM"] == "Dollars").all(), "Unexpected unit of measure"
    assert (sub["SCALAR_FACTOR"] == "units").all(), "Unexpected scalar factor"

    out = pd.DataFrame(
        {
            "ref_date": pd.to_datetime(sub["REF_DATE"] + "-01").dt.strftime("%Y-%m-%d"),
            "geo": sub["GEO"],
            "product": sub["Products"],
            "item": sub["Products"].map(lambda p: STAPLES[p][0]),
            "category": sub["Products"].map(lambda p: STAPLES[p][1]),
            "price_cad": sub["VALUE"],
            "status": sub["STATUS"].fillna(""),
            "vector": sub["VECTOR"],
        }
    )
    out = out.sort_values(["geo", "product", "ref_date"]).reset_index(drop=True)

    # One observation per series and month, no gaps.
    assert not out.duplicated(["ref_date", "geo", "product"]).any()
    n_months = out["ref_date"].nunique()
    per_series = out.groupby(["geo", "product"]).size()
    assert (per_series == n_months).all(), "Some series have gaps"
    return out


def main() -> None:
    out = tidy(load_raw())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(
        f"Wrote {OUT.relative_to(ROOT)}: {len(out):,} rows, "
        f"{out['product'].nunique()} products x {out['geo'].nunique()} geographies, "
        f"{out['ref_date'].min()} to {out['ref_date'].max()}, "
        f"missing prices: {out['price_cad'].isna().sum()}, "
        f"{OUT.stat().st_size / 1e3:.0f} KB"
    )


if __name__ == "__main__":
    main()
