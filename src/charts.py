"""Charts for the README, built from the SQL outputs and the processed CSV."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SQL_OUT = ROOT / "outputs" / "sql"
OUT = ROOT / "outputs"
SOURCE = "Source: Statistics Canada, Table 18-10-0245-01 (average retail prices). Equal-weight basket of 20 staples."
COLORS = {"Canada": "#444444", "Quebec": "#1f5fbf", "Ontario": "#8c8c8c",
          "Alberta": "#d98c1f", "Saskatchewan": "#3a9a5b"}

plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "font.size": 10})


def basket_chart() -> None:
    b = pd.read_csv(SQL_OUT / "q05_basket_index_monthly.csv", parse_dates=["ref_date"])
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for geo in ["Canada", "Quebec"]:
        g = b[b.geo == geo]
        ax.plot(g.ref_date, g.basket_index_2021_100, color=COLORS[geo], alpha=0.25, lw=1)
        ax.plot(g.ref_date, g.index_12m_avg, color=COLORS[geo], lw=2.4, label=f"{geo} (12-month average)")
    ax.axhline(100, color="black", lw=0.8)
    ax.axvline(pd.Timestamp("2024-01-01"), color="red", ls=":", lw=1)
    ax.text(pd.Timestamp("2024-01-15"), ax.get_ylim()[0] + 1, "Jan 2024: more retailers\nadded to the sample",
            color="red", fontsize=8, va="bottom")
    ax.set_title("Food staples basket index, Quebec vs Canada (2021 average = 100)", loc="left", fontweight="bold")
    ax.set_ylabel("Index")
    ax.legend(loc="upper left", frameon=False)
    fig.text(0.01, 0.01, SOURCE + " Thin lines = monthly values.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "basket_index_quebec_vs_canada.png")
    plt.close(fig)


def top_increases_chart() -> None:
    c = pd.read_csv(SQL_OUT / "q03_cumulative_12m_avg.csv")
    ca = c[c.geo == "Canada"].set_index("item").change_pct
    qc = c[c.geo == "Quebec"].set_index("item").change_pct
    top = ca.sort_values(ascending=False).head(10).index[::-1]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    y = range(len(top))
    ax.barh([i + 0.2 for i in y], ca[top], height=0.4, color=COLORS["Canada"], label="Canada")
    ax.barh([i - 0.2 for i in y], qc[top], height=0.4, color=COLORS["Quebec"], label="Quebec")
    for i, item in enumerate(top):
        ax.text(ca[item] + 0.8, i + 0.2, f"{ca[item]:.0f}%", va="center", fontsize=8)
        ax.text(qc[item] + 0.8, i - 0.2, f"{qc[item]:.0f}%", va="center", fontsize=8, color=COLORS["Quebec"])
    ax.set_yticks(list(y), top)
    ax.set_xlabel("% change in average price, 2021 average vs latest 12 months")
    ax.set_title("Top 10 price increases among 20 staples (ranked by Canada)", loc="left", fontweight="bold")
    ax.legend(loc="lower right", frameon=False)
    fig.text(0.01, 0.01, SOURCE.replace(" Equal-weight basket of 20 staples.", ""), fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "top10_increases.png")
    plt.close(fig)


def item_lines_chart() -> None:
    p = pd.read_csv(ROOT / "data" / "processed" / "staples_prices.csv", parse_dates=["ref_date"])
    p = p[p.ref_date >= "2021-01-01"]
    items = ["Coffee (340 g)", "Ground beef (kg)", "Eggs (12)", "Milk (4 L)", "Canola oil (3 L)", "Potatoes (4.54 kg)"]
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharex=True)
    for ax, item in zip(axes.flat, items):
        for geo in ["Canada", "Quebec"]:
            g = p[(p.item == item) & (p.geo == geo)].set_index("ref_date").price_cad
            ax.plot(g.index, g.rolling(3).mean(), color=COLORS[geo], lw=1.8, label=geo)
        ax.set_title(item, fontsize=10, fontweight="bold")
        ax.set_ylabel("$ (3-month avg)")
        ax.tick_params(axis="x", rotation=45)
    axes.flat[0].legend(frameon=False)
    fig.suptitle("Average retail price, selected staples, Quebec vs Canada", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.01, SOURCE.replace(" Equal-weight basket of 20 staples.", "") + " 3-month moving average.",
             fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(OUT / "item_lines.png")
    plt.close(fig)


def provinces_chart() -> None:
    d = pd.read_csv(SQL_OUT / "q10_provinces_basket.csv").sort_values("change_vs_2021_pct")
    period = f"{pd.Timestamp(d.from_month.iloc[0]):%b %Y}–{pd.Timestamp(d.to_month.iloc[0]):%b %Y}"
    canada_cost = d.loc[d.geo == "Canada", "basket_cost_cad"].iloc[0]
    canada_chg = d.loc[d.geo == "Canada", "change_vs_2021_pct"].iloc[0]
    colors = ["#c0392b" if g == "Canada" else "#7f9fc4" for g in d.geo]
    y = range(len(d))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5), sharey=True,
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    a1.barh(y, d.change_vs_2021_pct, color=colors)
    a1.axvline(canada_chg, color="#c0392b", lw=0.8, ls="--")
    for i, v in enumerate(d.change_vs_2021_pct):
        a1.text(v + 0.3, i, f"+{v:.1f}%", va="center", fontsize=8)
    a1.set_yticks(list(y), d.geo)
    for lbl in a1.get_yticklabels():
        if lbl.get_text() == "Canada":
            lbl.set_fontweight("bold")
    a1.set_xlim(0, d.change_vs_2021_pct.max() * 1.15)
    a1.set_xlabel("Basket index change vs 2021 average (%)")
    a1.set_title("How much it rose since 2021", loc="left", fontweight="bold", fontsize=10)
    a2.barh(y, d.basket_cost_cad, color=colors)
    a2.axvline(canada_cost, color="#c0392b", lw=0.8, ls="--")
    for i, (g, v, pct) in enumerate(zip(d.geo, d.basket_cost_cad, d.cost_vs_canada_pct)):
        label = f"${v:.2f}" if g == "Canada" else f"${v:.2f} ({pct:+.1f}%)"
        a2.text(v + 1, i, label, va="center", fontsize=8)
    a2.set_xlim(0, d.basket_cost_cad.max() * 1.3)
    a2.set_xlabel("Basket cost, one of each of the 20 items ($), vs Canada")
    a2.set_title("What it costs now", loc="left", fontweight="bold", fontsize=10)
    fig.suptitle(f"20-staple basket by province, latest 12 months ({period}). Canada in red",
                 x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.01, SOURCE + "\nExcluded: Newfoundland and Labrador (no 4 L milk series) and the territories"
             " (data only from Sep 2025).", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(OUT / "provinces_basket.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    basket_chart()
    top_increases_chart()
    item_lines_chart()
    provinces_chart()
    print("Charts written to outputs/: basket_index_quebec_vs_canada.png, top10_increases.png, "
          "item_lines.png, provinces_basket.png")


if __name__ == "__main__":
    main()
