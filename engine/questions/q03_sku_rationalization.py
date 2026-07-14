"""
Q03: Which SKUs should die?

Rule: SKUs where avg_weekly_units_per_store < VELOCITY_FLOOR AND
margin_pct < MARGIN_FLOOR qualify for the kill list.
Both conditions required — a slow SKU with great margin gets a watch, not a kill.

Thresholds calibrated from SKU Rationalization Framework.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q03"]

_SQL = """
WITH sku_velocity AS (
    SELECT
        sku,
        AVG(avg_weekly_units)    AS avg_weekly_velocity,
        SUM(total_units)         AS total_units,
        COUNT(DISTINCT store_id) AS active_stores
    FROM public_marts.fct_distribution
    WHERE is_active = true
    GROUP BY sku
)
SELECT
    dp.sku,
    dp.product_name,
    dp.product_line,
    ROUND(dp.margin_pct::numeric, 4)        AS margin_pct,
    dp.wholesale_price,
    dp.cogs_per_unit,
    ROUND(sv.avg_weekly_velocity::numeric, 2) AS avg_weekly_velocity,
    sv.active_stores,
    ROUND(cb.avg_weekly_units_per_store::numeric, 2) AS category_benchmark_velocity,
    ROUND(cb.avg_margin_pct::numeric, 4)    AS category_benchmark_margin
FROM public_marts.dim_products dp
JOIN sku_velocity sv ON dp.sku = sv.sku
JOIN public_marts.dim_category_benchmarks cb ON dp.product_line = cb.product_line
ORDER BY dp.margin_pct ASC, sv.avg_weekly_velocity ASC
"""


class SkuRationalizationQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q03",
            question="Which SKUs should die?",
            short_label="SKUs to kill?",
            source_piece="SKU Rationalization Framework",
            go_deeper_link="https://lailarallc.com/sku-rationalization",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        rows = query(_SQL)
        cfg = _CFG

        kill = [
            r for r in rows
            if float(r["avg_weekly_velocity"]) < cfg["velocity_floor_units_per_week"]
            and float(r["margin_pct"]) < cfg["margin_floor"]
        ]
        watch = [
            r for r in rows
            if r not in kill
            and (
                float(r["avg_weekly_velocity"]) < cfg["velocity_floor_units_per_week"]
                or float(r["margin_pct"]) < cfg["margin_floor"]
            )
        ]

        n_kill = len(kill)
        n_total = len(rows)

        if n_kill == 0:
            verdict = (
                f"No SKUs qualify for the kill list today. "
                f"All {n_total} active SKUs are above the velocity floor "
                f"({cfg['velocity_floor_units_per_week']} units/week/store) "
                f"or the margin floor ({cfg['margin_floor']:.0%}). "
                f"{len(watch)} SKUs are on watch — one poor quarter away from the list."
            )
            verdict_detail = "no kills"
        else:
            worst = kill[0]
            dead_wholesale = sum(float(r["wholesale_price"]) * float(r["avg_weekly_velocity"]) * 52
                                 for r in kill)
            verdict = (
                f"{n_kill} of {n_total} SKUs qualify for immediate discontinuation: "
                f"below {cfg['velocity_floor_units_per_week']} units/week AND below "
                f"{cfg['margin_floor']:.0%} margin. "
                f"Worst offender: {worst['product_name']} — "
                f"{float(worst['avg_weekly_velocity']):.1f} units/week at "
                f"{float(worst['margin_pct']):.0%} margin. "
                f"Cutting these SKUs removes ~${dead_wholesale:,.0f}/year in low-margin revenue "
                f"and clears complexity from production and ops."
            )
            verdict_detail = f"{n_kill} kill candidates"

        chart_data = ChartData(
            type="bar",
            title="SKU velocity vs. category benchmark",
            data=[
                {
                    "sku": r["product_name"],
                    "velocity": float(r["avg_weekly_velocity"]),
                    "benchmark": float(r["category_benchmark_velocity"]),
                    "margin_pct": float(r["margin_pct"]),
                }
                for r in rows[:12]
            ],
            x_key="sku",
            y_key="velocity",
            unit="units/week",
        )

        return VerdictResponse(
            question_id="q03",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(label="Kill candidates", value=str(n_kill), context="both criteria failed"),
                KeyNumber(label="On watch", value=str(len(watch)), context="one criterion failed"),
                KeyNumber(label="Velocity floor", value=f"{cfg['velocity_floor_units_per_week']} units/wk/store"),
            ],
            chart=chart_data,
            rule_explanation=(
                f"Kill = avg_weekly_velocity < {cfg['velocity_floor_units_per_week']} units/week/store "
                f"AND margin_pct < {cfg['margin_floor']:.0%}. "
                f"Both conditions required — slow + profitable = watch list, not kill list. "
                f"Thresholds from SKU Rationalization Framework."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(SkuRationalizationQuestion())
