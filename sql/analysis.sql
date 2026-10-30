-- Canada food prices tracker: analysis queries (SQLite 3.25+).
-- Table `prices` is loaded from data/processed/staples_prices.csv by src/run_sql.py:
--   ref_date TEXT 'YYYY-MM-01', geo TEXT, product TEXT (exact StatCan name),
--   item TEXT (short label), category TEXT, price_cad REAL
-- Table `prov_prices` is loaded from data/processed/provinces_prices.csv (src/provinces.py):
--   same columns (no category), Jan 2021 onward, Canada + the provinces that have all
--   20 staples in 2021 and the latest 12 months (see outputs/provinces_coverage.csv).
-- Each block starting with "-- name:" is run and saved to outputs/sql/<name>.csv.
-- Blocks named "setup_*" create views and produce no output file.
--
-- Two ways of measuring change are used on purpose:
--   * point-to-point: January 2021 vs the latest month (simple, but one noisy month at each end)
--   * 12-month averages: calendar-2021 average vs the average of the latest 12 months
--     (smooths out promotions and seasonality; used for rankings and headline numbers)

-- name: setup_views
DROP VIEW IF EXISTS v_latest;
CREATE VIEW v_latest AS
SELECT MAX(ref_date) AS latest,
       date(MAX(ref_date), '-11 months') AS window_start
FROM prices;

DROP VIEW IF EXISTS v_yoy;
CREATE VIEW v_yoy AS
SELECT cur.ref_date, cur.geo, cur.item, cur.category,
       cur.price_cad,
       prev.price_cad AS price_12m_ago,
       ROUND(100.0 * (cur.price_cad / prev.price_cad - 1), 2) AS yoy_pct
FROM prices cur
JOIN prices prev
  ON prev.geo = cur.geo
 AND prev.product = cur.product
 AND prev.ref_date = date(cur.ref_date, '-12 months');

DROP VIEW IF EXISTS v_change_avg;
CREATE VIEW v_change_avg AS
WITH base AS (
    SELECT geo, item, category, AVG(price_cad) AS avg_2021
    FROM prices WHERE ref_date BETWEEN '2021-01-01' AND '2021-12-01'
    GROUP BY geo, item, category
), recent AS (
    SELECT p.geo, p.item, AVG(p.price_cad) AS avg_last12
    FROM prices p, v_latest l
    WHERE p.ref_date BETWEEN l.window_start AND l.latest
    GROUP BY p.geo, p.item
)
SELECT b.geo, b.item, b.category,
       ROUND(b.avg_2021, 2)   AS avg_2021,
       ROUND(r.avg_last12, 2) AS avg_last12,
       ROUND(100.0 * (r.avg_last12 / b.avg_2021 - 1), 1) AS change_pct
FROM base b JOIN recent r USING (geo, item);

DROP VIEW IF EXISTS v_basket;
CREATE VIEW v_basket AS
-- Equal-weight basket: every item counts the same, regardless of how much
-- households spend on it. Index = mean of item price relatives x 100.
WITH base AS (
    SELECT geo, product, AVG(price_cad) AS base_2021
    FROM prices WHERE ref_date BETWEEN '2021-01-01' AND '2021-12-01'
    GROUP BY geo, product
)
SELECT p.ref_date, p.geo,
       COUNT(*) AS n_items,
       ROUND(100.0 * AVG(p.price_cad / b.base_2021), 2) AS basket_index_2021_100
FROM prices p JOIN base b USING (geo, product)
WHERE p.ref_date >= '2021-01-01'
GROUP BY p.ref_date, p.geo;

-- name: q01_latest_yoy
-- Year-over-year % change in the latest month, Quebec vs Canada, per item.
SELECT y.item, y.category,
       MAX(CASE WHEN y.geo = 'Canada' THEN y.price_cad END) AS canada_price,
       MAX(CASE WHEN y.geo = 'Canada' THEN y.yoy_pct END)   AS canada_yoy_pct,
       MAX(CASE WHEN y.geo = 'Quebec' THEN y.price_cad END) AS quebec_price,
       MAX(CASE WHEN y.geo = 'Quebec' THEN y.yoy_pct END)   AS quebec_yoy_pct,
       (SELECT latest FROM v_latest) AS month
FROM v_yoy y
WHERE y.ref_date = (SELECT latest FROM v_latest)
GROUP BY y.item, y.category
ORDER BY canada_yoy_pct DESC;

-- name: q02_cumulative_point_to_point
-- Cumulative % change, January 2021 -> latest month, every geography and item.
SELECT cur.geo, cur.item,
       base.price_cad AS price_jan2021,
       cur.price_cad  AS price_latest,
       cur.ref_date   AS latest_month,
       ROUND(100.0 * (cur.price_cad / base.price_cad - 1), 1) AS change_pct
FROM prices cur
JOIN prices base
  ON base.geo = cur.geo AND base.product = cur.product AND base.ref_date = '2021-01-01'
WHERE cur.ref_date = (SELECT latest FROM v_latest)
ORDER BY cur.geo, change_pct DESC;

-- name: q03_cumulative_12m_avg
-- Cumulative % change, 2021 average -> average of the latest 12 months.
SELECT geo, item, category, avg_2021, avg_last12, change_pct
FROM v_change_avg
ORDER BY geo, change_pct DESC;

-- name: q04_most_least_inflationary
-- Top 5 and bottom 5 items by 12-month-average change, Canada and Quebec.
WITH ranked AS (
    SELECT geo, item, change_pct,
           RANK() OVER (PARTITION BY geo ORDER BY change_pct DESC) AS rank_high,
           RANK() OVER (PARTITION BY geo ORDER BY change_pct ASC)  AS rank_low
    FROM v_change_avg
    WHERE geo IN ('Canada', 'Quebec')
)
SELECT geo,
       CASE WHEN rank_high <= 5 THEN 'most' ELSE 'least' END AS grp,
       item, change_pct
FROM ranked
WHERE rank_high <= 5 OR rank_low <= 5
ORDER BY geo, change_pct DESC;

-- name: q05_basket_index_monthly
-- Monthly equal-weight basket index (2021 average = 100) by geography,
-- with a 12-month moving average to remove seasonality and promotions.
SELECT ref_date, geo, n_items, basket_index_2021_100,
       CASE WHEN COUNT(*) OVER w = 12
            THEN ROUND(AVG(basket_index_2021_100) OVER w, 2) END AS index_12m_avg
FROM v_basket
WINDOW w AS (PARTITION BY geo ORDER BY ref_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
ORDER BY geo, ref_date;

-- name: q06_basket_annual
-- Annual average of the basket index and its year-over-year change.
WITH yearly AS (
    SELECT geo, substr(ref_date, 1, 4) AS year,
           COUNT(*) AS months,
           AVG(basket_index_2021_100) AS idx
    FROM v_basket
    GROUP BY geo, year
)
SELECT geo, year, months, ROUND(idx, 1) AS basket_index_avg,
       ROUND(100.0 * (idx / LAG(idx) OVER (PARTITION BY geo ORDER BY year) - 1), 1) AS yoy_pct
FROM yearly
ORDER BY geo, year;

-- name: q07_basket_summary
-- Headline: basket level in the latest 12 months vs 2021, by geography.
SELECT b.geo,
       ROUND(AVG(b.basket_index_2021_100), 1) AS index_last12_avg,
       ROUND(AVG(b.basket_index_2021_100) - 100, 1) AS change_vs_2021_pct,
       MIN(b.ref_date) AS from_month, MAX(b.ref_date) AS to_month
FROM v_basket b, v_latest l
WHERE b.ref_date BETWEEN l.window_start AND l.latest
GROUP BY b.geo
ORDER BY change_vs_2021_pct DESC;

-- name: q08_quebec_vs_canada_level
-- Price level: Quebec average price as % of the Canada average price,
-- 2021 vs the latest 12 months (100 = same as Canada).
SELECT q.item,
       ROUND(100.0 * q.avg_2021 / c.avg_2021, 1)     AS qc_pct_of_canada_2021,
       ROUND(100.0 * q.avg_last12 / c.avg_last12, 1) AS qc_pct_of_canada_last12,
       q.change_pct AS qc_change_pct,
       c.change_pct AS canada_change_pct
FROM v_change_avg q
JOIN v_change_avg c ON c.item = q.item AND c.geo = 'Canada'
WHERE q.geo = 'Quebec'
ORDER BY qc_pct_of_canada_last12 DESC;

-- name: q09_yoy_by_year_canada
-- Average year-over-year % change by calendar year, Canada, per item.
SELECT item,
       ROUND(AVG(CASE WHEN substr(ref_date,1,4) = '2021' THEN yoy_pct END), 1) AS y2021,
       ROUND(AVG(CASE WHEN substr(ref_date,1,4) = '2022' THEN yoy_pct END), 1) AS y2022,
       ROUND(AVG(CASE WHEN substr(ref_date,1,4) = '2023' THEN yoy_pct END), 1) AS y2023,
       ROUND(AVG(CASE WHEN substr(ref_date,1,4) = '2024' THEN yoy_pct END), 1) AS y2024,
       ROUND(AVG(CASE WHEN substr(ref_date,1,4) = '2025' THEN yoy_pct END), 1) AS y2025,
       ROUND(AVG(CASE WHEN substr(ref_date,1,4) = '2026' THEN yoy_pct END), 1) AS y2026_ytd
FROM v_yoy
WHERE geo = 'Canada'
GROUP BY item
ORDER BY y2022 DESC;

-- name: q10_provinces_basket
-- Provincial comparison of the same 20-staple basket, latest 12 months.
--   basket_cost_cad   = sum of the 20 items' latest-12-month average prices
--                       (one unit of each item: not a household grocery bill)
--   cost_vs_canada_pct = basket cost relative to Canada's
--   change_vs_2021_pct = equal-weight basket index (mean of item ratios
--                        latest-12-month avg / 2021 avg) minus 100. Same method as q07:
--                        averaging the monthly index over 12 months gives exactly this.
WITH win AS (
    SELECT MAX(ref_date) AS latest, date(MAX(ref_date), '-11 months') AS window_start
    FROM prov_prices
), item AS (
    SELECT p.geo, p.product,
           AVG(CASE WHEN p.ref_date BETWEEN '2021-01-01' AND '2021-12-01' THEN p.price_cad END) AS avg_2021,
           AVG(CASE WHEN p.ref_date BETWEEN w.window_start AND w.latest THEN p.price_cad END) AS avg_last12
    FROM prov_prices p, win w
    GROUP BY p.geo, p.product
), geo AS (
    SELECT geo, COUNT(*) AS n_items,
           SUM(avg_last12) AS cost,
           100.0 * AVG(avg_last12 / avg_2021) - 100 AS chg
    FROM item
    GROUP BY geo
    HAVING COUNT(avg_2021) = 20 AND COUNT(avg_last12) = 20
)
SELECT g.geo, g.n_items,
       ROUND(g.cost, 2) AS basket_cost_cad,
       ROUND(100.0 * (g.cost / c.cost - 1), 1) AS cost_vs_canada_pct,
       ROUND(g.chg, 1) AS change_vs_2021_pct,
       RANK() OVER (ORDER BY g.chg) AS rank_change_low_to_high,
       RANK() OVER (ORDER BY g.cost) AS rank_cost_low_to_high,
       (SELECT window_start FROM win) AS from_month,
       (SELECT latest FROM win) AS to_month
FROM geo g
JOIN geo c ON c.geo = 'Canada'
ORDER BY g.chg;
