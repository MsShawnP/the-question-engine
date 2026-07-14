"""
Q11: What did the orders I couldn't fill actually cost me?

Measures implied revenue lost to on-shelf stockouts: active SKU-store
authorizations where scan velocity was zero for a given week (product
was supposed to be on shelf but wasn't selling).

Rule: if total implied stockout cost > STOCKOUT_COST_THRESHOLD, verdict fires
naming the total figure and the single worst offending SKU.

Computation avoids a CROSS JOIN: uses fct_distribution.weeks_with_sales
(weeks with actual scans) vs total weeks in scan_data range.

Routes to: The 150 Cases You Didn't Ship.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion, NoDataError
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q11"]

_SQL_SUMMARY = """
WITH scan_range AS (
    SELECT CEIL((MAX(week_ending) - MIN(week_ending))::numeric / 7 + 1) AS total_weeks
    FROM public_marts.fct_scan_data
),
per_store AS (
    SELECT
        d.sku,
        d.store_id,
        (sr.total_weeks - d.weeks_with_sales)                                           AS zero_weeks,
        d.avg_weekly_units * (sr.total_weeks - d.weeks_with_sales) * dp.wholesale_price AS implied_lost
    FROM public_marts.fct_distribution d
    CROSS JOIN scan_range sr
    JOIN public_marts.dim_products dp ON dp.sku = d.sku
    WHERE d.is_active = true
      AND d.weeks_with_sales < sr.total_weeks
)
SELECT
    ROUND(SUM(implied_lost)::numeric, 0) AS total_implied_lost,
    SUM(zero_weeks)                      AS total_zero_weeks,
    COUNT(DISTINCT sku)                  AS sku_count,
    COUNT(DISTINCT store_id)             AS active_stores
FROM per_store
"""

_SQL_BY_SKU = """
WITH scan_range AS (
    SELECT CEIL((MAX(week_ending) - MIN(week_ending))::numeric / 7 + 1) AS total_weeks
    FROM public_marts.fct_scan_data
),
per_store AS (
    SELECT
        d.sku,
        (sr.total_weeks - d.weeks_with_sales)                                           AS zero_weeks,
        d.avg_weekly_units * (sr.total_weeks - d.weeks_with_sales) * dp.wholesale_price AS implied_lost
    FROM public_marts.fct_distribution d
    CROSS JOIN scan_range sr
    JOIN public_marts.dim_products dp ON dp.sku = d.sku
    WHERE d.is_active = true
      AND d.weeks_with_sales < sr.total_weeks
)
SELECT
    p.sku,
    dp.product_name,
    dp.product_line,
    SUM(p.zero_weeks)                      AS zero_weeks,
    ROUND(SUM(p.implied_lost)::numeric, 0) AS implied_lost
FROM per_store p
JOIN public_marts.dim_products dp ON dp.sku = p.sku
GROUP BY p.sku, dp.product_name, dp.product_line
ORDER BY implied_lost DESC
LIMIT 8
"""


class StockoutCostQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q11",
            question="What did the orders I couldn't fill actually cost me?",
            short_label="Stockout cost?",
            source_piece="The 150 Cases You Didn't Ship",
            go_deeper_link="https://lailarallc.com/the-150-cases-you-didnt-ship",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        summary_rows = query(_SQL_SUMMARY)
        by_sku = query(_SQL_BY_SKU)
        if not summary_rows or not by_sku:
            raise NoDataError("q11: no stockout data returned")
        summary = summary_rows[0]

        total_lost = float(summary["total_implied_lost"] or 0)
        zero_weeks = int(summary["total_zero_weeks"] or 0)
        active_stores = int(summary["active_stores"] or 0)
        cfg = _CFG

        worst = by_sku[0] if by_sku else None
        worst_lost = float(worst["implied_lost"]) if worst else 0

        if total_lost > cfg["stockout_cost_threshold"]:
            verdict = (
                f"${total_lost:,.0f} in implied revenue was left on the shelf — "
                f"active SKU-store authorizations with zero scan velocity across {zero_weeks:,} store-weeks. "
                f"Worst offender: {worst['product_name']} at ${worst_lost:,.0f} implied lost "
                f"({int(worst['zero_weeks']):,} zero-velocity weeks). "
                f"Every zero-scan week at an authorized store is a stockout you paid to be in."
            )
            verdict_detail = f"${total_lost:,.0f} implied stockout cost"
        else:
            verdict = (
                f"Stockout exposure is within range: ${total_lost:,.0f} in implied lost revenue "
                f"across {zero_weeks:,} zero-velocity store-weeks at {active_stores} authorized locations. "
                f"Below the ${cfg['stockout_cost_threshold']:,.0f} threshold. "
                f"Worst SKU: {worst['product_name']} at ${worst_lost:,.0f}."
            )
            verdict_detail = "within range"

        chart_data = ChartData(
            type="bar",
            title="Implied stockout cost by SKU",
            data=[
                {
                    "sku": r["product_name"],
                    "implied_lost": float(r["implied_lost"]),
                    "zero_weeks": int(r["zero_weeks"]),
                }
                for r in by_sku
            ],
            x_key="sku",
            y_key="implied_lost",
            unit="dollars",
        )

        return VerdictResponse(
            question_id="q11",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(
                    label="Implied stockout cost",
                    value=f"${total_lost:,.0f}",
                    context="authorized stores, zero velocity",
                ),
                KeyNumber(
                    label="Zero-velocity store-weeks",
                    value=f"{zero_weeks:,}",
                    context="active SKU × store × week with no scan",
                ),
                KeyNumber(
                    label="Worst SKU",
                    value=worst["product_name"] if worst else "—",
                    context=f"${worst_lost:,.0f} implied" if worst else None,
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"Stockout = active fct_distribution record (is_active=true) with zero units_sold "
                f"in fct_scan_data for that store-week. "
                f"Implied cost = zero_weeks × avg_weekly_units_when_selling × wholesale_price. "
                f"Fires when total implied cost > ${cfg['stockout_cost_threshold']:,.0f}. "
                f"Routes to The 150 Cases You Didn't Ship."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(StockoutCostQuestion())
