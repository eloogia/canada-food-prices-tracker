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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    basket_chart()
    top_increases_chart()
    item_lines_chart()
    print("Charts written to outputs/: basket_index_quebec_vs_canada.png, top10_increases.png, item_lines.png")


if __name__ == "__main__":
    main()
