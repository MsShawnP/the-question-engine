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

Implementation note: fct_scan_data has 1.4M rows. To avoid OOM on the
DB machine (sorting 1.4M values for PERCENTILE_CONT), we group by SKU first
(50 groups of ~28K rows each — AVG only, no sort) and compute all statistics
in Python from the 50-row result. This is macro-MAPE (average of per-SKU
MAPEs) rather than micro-MAPE (global average), which gives a slightly
different number but the same verdict direction.
"""
import statistics
import yaml
from pathlib import Path

from engine.base import BaseQuestion, NoDataError
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q12"]

_SQL_ALL_SKUS = """
WITH sku_errors AS (
    SELECT
        sd.sku,
        AVG(ABS(sd.units_sold - f.avg_weekly_units) / NULLIF(sd.units_sold::numeric, 0)) AS sku_mape,
        AVG(f.avg_weekly_units) AS avg_forecast_units
    FROM public_marts.fct_scan_data sd
    JOIN public_marts.fct_distribution f
        ON f.sku = sd.sku AND f.store_id = sd.store_id
        AND f.is_active = true AND f.avg_weekly_units > 0
    WHERE sd.units_sold > 0
    GROUP BY sd.sku
)
SELECT
    e.sku,
    dp.product_name,
    ROUND(e.sku_mape::numeric * 100, 1)     AS mape_pct,
    ROUND(e.avg_forecast_units::numeric, 1) AS avg_forecast_units
FROM sku_errors e
JOIN public_marts.dim_products dp ON dp.sku = e.sku
ORDER BY sku_mape DESC
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
        all_skus = query(_SQL_ALL_SKUS)
        if not all_skus:
            raise NoDataError("q12: no forecast/actual rows returned")

        mapes = [float(r["mape_pct"]) for r in all_skus]
        mape = round(statistics.mean(mapes), 1)
        median_ape = round(statistics.median(mapes), 1)
        sku_count = len(all_skus)
        cfg = _CFG

        by_sku = all_skus[:10]
        worst_sku = all_skus[0] if all_skus else None
        best_sku = all_skus[-1] if all_skus else None

        if mape > cfg["mape_warning"]:
            verdict = (
                f"Forecast MAPE is {mape:.1f}% — well above the {cfg['mape_warning']:.0f}% broken threshold. "
                f"At this error rate, production and procurement decisions made from the forecast "
                f"will be wrong by a third or more. "
                f"Worst SKU: {worst_sku['product_name']} at {float(worst_sku['mape_pct']):.1f}% MAPE. "
                f"Median error is {median_ape:.1f}% — the problem is systemic, not outlier-driven."
                if median_ape > cfg["mape_warning"] * 0.7
                else
                f"Forecast MAPE is {mape:.1f}% — well above the {cfg['mape_warning']:.0f}% broken threshold. "
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
                    label="Median SKU error",
                    value=f"{median_ape:.1f}%",
                    context="Median of per-SKU MAPEs",
                ),
                KeyNumber(
                    label="Worst SKU",
                    value=worst_sku["product_name"] if worst_sku else "—",
                    context=f"{float(worst_sku['mape_pct']):.1f}% MAPE" if worst_sku else None,
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"MAPE computed per SKU: AVG(|actual - forecast| / actual) across active store-weeks. "
                f"Forecast proxy = fct_distribution.avg_weekly_units. "
                f"Macro-MAPE = average of per-SKU MAPEs across {sku_count} SKUs. "
                f"Decision-grade: < {cfg['mape_decision_grade']:.0f}%. "
                f"Warning: {cfg['mape_decision_grade']:.0f}–{cfg['mape_warning']:.0f}%. "
                f"Broken: > {cfg['mape_warning']:.0f}%."
            ),
            go_deeper_link=self.meta().