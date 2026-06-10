"""
Q12: Can I trust my own forecast?

Computes MAPE (Mean Absolute Percentage Error) by comparing
fct_distribution.avg_weekly_units (the standing forecast per SKU-store)
against fct_scan_data.units_sold (actuals).

Rule: MAPE > MAPE_WARNING (30%) = broken / don't plan from it.
      MAPE 20–30% = needs improvement.
      MAPE < 20% = decision-grade.

Secondary: median APE surfaces whether errors are systematic or
driven by a long tail of outlier weeks.

Routes to: Production Demand Forecast.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q12"]

_SQL_SUMMARY = """
WITH forecast AS (
    SELECT sku, store_id, avg_weekly_units AS forecast_units
    FROM public_marts.fct_distribution
    WHERE is_active = true AND avg_weekly_units > 0
),
errors AS (
    SELECT
        sd.sku,
        ABS(sd.units_sold - f.forecast_units) / NULLIF(sd.units_sold::numeric, 0) AS abs_pct_error
    FROM public_marts.fct_scan_data sd
    JOIN forecast f ON f.sku = sd.sku AND f.store_id = sd.store_id
    WHERE sd.units_sold > 0
)
SELECT
    ROUND(AVG(abs_pct_error)::numeric * 100, 1)                                              AS mape_pct,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY abs_pct_error)::numeric * 100, 1)     AS median_ape_pct,
    COUNT(DISTINCT sku)                                                                      AS sku_count,
    COUNT(*)                                                                                 AS data_points
FROM errors
"""

_SQL_BY_SKU = """
WITH forecast AS (
    SELECT sku, store_id, avg_weekly_units AS forecast_units
    FROM public_marts.fct_distribution
    WHERE is_active = true AND avg_weekly_units > 0
),
errors AS (
    SELECT
        sd.sku,
        ABS(sd.units_sold - f.forecast_units) / NULLIF(sd.units_sold::numeric, 0) AS abs_pct_error
    FROM public_marts.fct_scan_data sd
    JOIN forecast f ON f.sku = sd.sku AND f.store_id = sd.store_id
    WHERE sd.units_sold > 0
)
SELECT
    e.sku,
    dp.product_name,
    ROUND(AVG(e.abs_pct_error)::numeric * 100, 1) AS mape_pct,
    ROUND(AVG(d.avg_weekly_units)::numeric, 1)    AS avg_forecast_units
FROM errors e
JOIN public_marts.dim_products dp ON dp.sku = e.sku
JOIN public_marts.fct_distribution d ON d.sku = e.sku AND d.is_active = true
GROUP BY e.sku, dp.product_name
ORDER BY mape_pct DESC
LIMIT 10
"""


class ForecastAccuracyQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q12",
            question="Can I trust my own forecast?",
            short_label="Forecast trustworthy?",
            source_piece="Production Demand Forecast",
            go_deeper_link="/production-demand-forecast",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        summary = query(_SQL_SUMMARY)[0]
        by_sku = query(_SQL_BY_SKU)

        mape = float(summary["mape_pct"] or 0)
        median_ape = float(summary["median_ape_pct"] or 0)
        sku_count = int(summary["sku_count"] or 0)
        cfg = _CFG

        worst_sku = by_sku[0] if by_sku else None
        best_sku = by_sku[-1] if by_sku else None

        if mape > cfg["mape_warning"]:
            verdict = (
                f"Forecast MAPE is {mape:.1f}% — well above the {cfg['mape_warning']:.0f}% broken threshold. "
                f"At this error rate, production and procurement decisions made from the forecast "
                f"will be wrong by a third or more. "
                f"Worst SKU: {worst_sku['product_name']} at {float(worst_sku['mape_pct']):.1f}% MAPE. "
                f"Median error is {median_ape:.1f}% — the problem is systemic, not outlier-driven."
                if median_ape > cfg["mape_warning"] * 0.7
                else
                f"At this error rate, production and procurement decisions made from the forecast "
                f"will be wrong by a third or more. "
                f"Worst SKU: {worst_sku['product_name']} at {float(worst_sku['mape_pct']):.1f}% MAPE. "
                f"Median error is {median_ape:.1f}% — a long tail of high-error weeks is skewing the average."
            )
            verdict_detail = f"{mape:.1f}% MAPE — forecast broken"
        elif mape > cfg["mape_decision_grade"]:
            verdict = (
                f"Forecast MAPE is {mape:.1f}% — between the {cfg['mape_decision_grade']:.0f}% decision-grade "
                f"floor and {cfg['mape_warning']:.0f}% broken ceiling. "
                f"Aggregate demand is usable, but SKU-level planning carries real risk. "
                f"Worst SKU: {worst_sku['product_name']} at {float(worst_sku['mape_pct']):.1f}% MAPE. "
                f"Median error is {median_ape:.1f}%."
            )
            verdict_detail = f"{mape:.1f}% MAPE — needs improvement"
        else:
            verdict = (
                f"Forecast MAPE is {mape:.1f}% — decision-grade (below {cfg['mape_decision_grade']:.0f}% threshold). "
                f"Both aggregate and SKU-level demand signals are reliable enough for production planning. "
                f"Best SKU: {best_sku['product_name']} at {float(best_sku['mape_pct']):.1f}% MAPE across {sku_count} active SKUs."
            )
            verdict_detail = f"{mape:.1f}% MAPE — decision-grade"

        chart_data = ChartData(
            type="bar",
            title="Forecast MAPE by SKU (worst to best)",
            data=[
                {
                    "sku": r["product_name"],
                    "mape_pct": float(r["mape_pct"]),
                }
                for r in by_sku
            ],
            x_key="sku",
            y_key="mape_pct",
            unit="percent",
        )

        return VerdictResponse(
            question_id="q12",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(label="Forecast MAPE", value=f"{mape:.1f}%"),
                KeyNumber(
                    label="Median error",
                    value=f"{median_ape:.1f}%",
                    context="50th percentile store-week error",
                ),
                KeyNumber(
                    label="Worst SKU",
                    value=worst_sku["product_name"] if worst_sku else "—",
                    context=f"{float(worst_sku['mape_pct']):.1f}% MAPE" if worst_sku else None,
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"MAPE = mean(|actual - forecast| / actual) across all active SKU-store-weeks with units_sold > 0. "
                f"Forecast proxy = fct_distribution.avg_weekly_units (standing velocity per SKU-store). "
                f"Decision-grade: < {cfg['mape_decision_grade']:.0f}%. "
                f"Warning: {cfg['mape_decision_grade']:.0f}–{cfg['mape_warning']:.0f}%. "
                f"Broken: > {cfg['mape_warning']:.0f}%. "
                f"Thresholds from Production Demand Forecast."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(ForecastAccuracyQuestion())
