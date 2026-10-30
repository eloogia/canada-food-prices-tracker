# Small R companion to the Python/SQL pipeline.
# 1) Recomputes the equal-weight basket index from the processed CSV and checks
#    it matches the SQL result (independent cross-check of the method).
# 2) Draws a dumbbell chart: change in average price per item, Quebec vs Canada.
# Run from the repo root:  Rscript r/quebec_vs_canada.R
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(ggplot2)
})

prices <- read_csv("data/processed/staples_prices.csv", show_col_types = FALSE)

# ---- 1. Basket index cross-check -------------------------------------------
base <- prices |>
  filter(ref_date >= as.Date("2021-01-01"), ref_date <= as.Date("2021-12-01")) |>
  group_by(geo, product) |>
  summarise(base_2021 = mean(price_cad), .groups = "drop")

basket_r <- prices |>
  filter(ref_date >= as.Date("2021-01-01")) |>
  inner_join(base, by = c("geo", "product")) |>
  group_by(ref_date, geo) |>
  summarise(index_r = round(100 * mean(price_cad / base_2021), 2), .groups = "drop")

basket_sql <- read_csv("outputs/sql/q05_basket_index_monthly.csv", show_col_types = FALSE)
check <- inner_join(basket_r, basket_sql, by = c("ref_date", "geo"))
max_diff <- max(abs(check$index_r - check$basket_index_2021_100))
cat(sprintf("Basket index R vs SQL: %d month-geo pairs compared, max abs difference = %.4f\n",
            nrow(check), max_diff))
stopifnot(nrow(check) == nrow(basket_sql), max_diff <= 0.01)

# ---- 2. Dumbbell chart -----------------------------------------------------
chg <- read_csv("outputs/sql/q03_cumulative_12m_avg.csv", show_col_types = FALSE) |>
  filter(geo %in% c("Canada", "Quebec")) |>
  select(item, geo, change_pct)

seg <- chg |>
  group_by(item) |>
  summarise(lo = min(change_pct), hi = max(change_pct),
            canada = change_pct[geo == "Canada"], .groups = "drop") |>
  arrange(canada) |>
  mutate(item = factor(item, levels = item))
chg$item <- factor(chg$item, levels = levels(seg$item))

p <- ggplot() +
  geom_segment(data = seg, aes(x = lo, xend = hi, y = item, yend = item),
               colour = "grey70", linewidth = 1.2) +
  geom_point(data = chg, aes(x = change_pct, y = item, colour = geo), size = 2.8) +
  scale_colour_manual(values = c(Canada = "#444444", Quebec = "#1f5fbf"), name = NULL) +
  geom_vline(xintercept = 0, linewidth = 0.3) +
  labs(title = "Change in average price per staple: Quebec vs Canada",
       subtitle = "2021 average vs latest 12 months (%)",
       x = "% change", y = NULL,
       caption = "Source: Statistics Canada, Table 18-10-0245-01. Chart made in R (ggplot2).") +
  theme_minimal(base_size = 11) +
  theme(legend.position = "top", plot.title = element_text(face = "bold"))

ggsave("outputs/r_quebec_vs_canada_dumbbell.png", p, width = 8, height = 6.5, dpi = 120, bg = "white")
cat("Saved outputs/r_quebec_vs_canada_dumbbell.png\n")
