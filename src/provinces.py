"""Provincial comparison input: the same 20 staples for Canada and every province.

Input : data/raw/18100245.csv   (run src/download.py first)
Output: data/processed/provinces_prices.csv
            one row per (month, geography, product), January 2021 to the latest
            month, only for geographies that pass the completeness rule below.
        outputs/provinces_coverage.csv
            every geography in the table, items available in each window and
            whether it was kept (documents the exclusions).

Completeness rule: a geography is kept only if all 20 staples have a price for
all 12 months of 2021 AND all 12 of the latest 12 months. Otherwise basket
costs would not be comparable (a missing item makes a basket look cheaper).
"""
from pathlib import Path

import pandas as pd

from clean import STAPLES, load_raw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "provinces_prices.csv"
COVERAGE = ROOT / "outputs" / "provinces_coverage.csv"


def months_present(sub: pd.DataFrame, start: str, end: str) -> pd.Series:
    w = sub[sub["REF_DATE"].between(start, end) & sub["VALUE"].notna()]
    return w.groupby(["GEO", "Products"]).size()


def main() -> None:
    df = load_raw()
    sub = df[df["Products"].isin(STAPLES)].copy()
    assert (sub["UOM"] == "Dollars").all(), "Unexpected unit of measure"

    latest = sub.loc[sub["VALUE"].notna(), "REF_DATE"].max()
    window_start = (pd.Period(latest, "M") - 11).strftime("%Y-%m")

    base = months_present(sub, "2021-01", "2021-12")
    recent = months_present(sub, window_start, latest)

    rows = []
    for geo in df["GEO"].unique():  # table order: Canada, provinces east to west, territories
        b = base.get(geo, pd.Series(dtype=int))
        r = recent.get(geo, pd.Series(dtype=int))
        full_b = sorted(p for p in STAPLES if b.get(p, 0) == 12)
        full_r = sorted(p for p in STAPLES if r.get(p, 0) == 12)
        missing = sorted(set(STAPLES) - (set(full_b) & set(full_r)))
        kept = not missing
        if kept:
            reason = ""
        elif not full_b:
            first = sub.loc[(sub["GEO"] == geo) & sub["VALUE"].notna(), "REF_DATE"].min()
            reason = f"no 2021 data (series start {first})"
        else:
            reason = "missing: " + "; ".join(missing)
        rows.append({"geo": geo, "items_full_2021": len(full_b),
                     f"items_full_{window_start}_{latest}": len(full_r),
                     "kept": kept, "reason_excluded": reason})
    cov = pd.DataFrame(rows)
    kept_geos = cov.loc[cov["kept"], "geo"].tolist()
    assert "Canada" in kept_geos, "Canada failed the completeness rule"

    s = sub[sub["GEO"].isin(kept_geos) & (sub["REF_DATE"] >= "2021-01")]
    out = pd.DataFrame({
        "ref_date": pd.to_datetime(s["REF_DATE"] + "-01").dt.strftime("%Y-%m-%d"),
        "geo": s["GEO"],
        "product": s["Products"],
        "item": s["Products"].map(lambda p: STAPLES[p][0]),
        "price_cad": s["VALUE"],
    }).sort_values(["geo", "product", "ref_date"]).reset_index(drop=True)
    assert not out.duplicated(["ref_date", "geo", "product"]).any()
    assert out["price_cad"].notna().all()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    cov.to_csv(COVERAGE, index=False)
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(out):,} rows, {len(kept_geos)} geographies, "
          f"{out['ref_date'].min()} to {out['ref_date'].max()}, {OUT.stat().st_size / 1e3:.0f} KB")
    for _, r in cov[~cov["kept"]].iterrows():
        print(f"  excluded {r.geo}: {r.reason_excluded}")


if __name__ == "__main__":
    main()
