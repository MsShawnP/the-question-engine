"""Diagnose q12 query performance."""
import time
from db.connection import query

sql_count = "SELECT COUNT(*) AS cnt FROM public_marts.fct_scan_data"
sql_sizes = """
SELECT tablename, pg_size_pretty(pg_total_relation_size('public_marts.' || tablename)) AS size
FROM pg_tables WHERE schemaname = 'public_marts' ORDER BY pg_total_relation_size('public_marts.' || tablename) DESC
"""

sql_q12_fast = """
WITH sku_actuals AS (
    SELECT sku, AVG(units_sold) AS avg_actual_units
    FROM public_marts.fct_scan_data WHERE units_sold > 0 GROUP BY sku
),
sku_forecast AS (
    SELECT sku, AVG(avg_weekly_units) AS avg_forecast_units
    FROM public_marts.fct_distribution WHERE is_active = true AND avg_weekly_units > 0 GROUP BY sku
),
errors AS (
    SELECT ABS(a.avg_actual_units - f.avg_forecast_units) / NULLIF(a.avg_actual_units::numeric, 0) AS abs_pct_error
    FROM sku_actuals a JOIN sku_forecast f ON f.sku = a.sku
)
SELECT
    ROUND(AVG(abs_pct_error)::numeric * 100, 1) AS mape_pct,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY abs_pct_error)::numeric * 100, 1) AS median_ape_pct,
    COUNT(*) AS sku_count
FROM errors
"""

t0 = time.time()
r = query(sql_count)
print(f"fct_scan_data rows: {r[0]['cnt']} ({time.time()-t0:.2f}s)")

t0 = time.time()
r = query(sql_sizes)
print("Table sizes:")
for row in r[:5]:
    print(f"  {row['tablename']}: {row['size']}")
print(f"  ({time.time()-t0:.2f}s)")

t0 = time.time()
r = query(sql_q12_fast)
print(f"SKU-level MAPE: {r[0]['mape_pct']}% (median {r[0]['median_ape_pct']}%) — {r[0]['sku_count']} SKUs ({time.time()-t0:.2f}s)")
