"""
Q14: Which SKUs are slowing down before the buyer notices?

Computes trailing 13-week velocity vs prior 13-week velocity for each SKU
from fct_scan_data. A negative change means the SKU is losing momentum before
the buyer has run their own scan review.

Rule: SKUs where pct_change < DECAY_THRESHOLD (-5%) are in decay.
SKUs where pct_change < CAUTION_THRESHOLD (+5%) are in the caution zone.
When no SKUs are in decay, verdict ranks by slowest momentum.

Routes to: Velocity Decision Tool.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q14"]

_SQL_SUMMARY = """
WITH weekly_sku AS (
    SELECT sku, week_ending, SUM(units_sold) AS total_units
    FROM public_marts.fct_scan_data
    GROUP BY sku, week_ending
),
ranked AS (
    SELECT sku, week_ending, total_units,
        ROW_NUMBER() OVER (PARTITION BY sku ORDER BY week_ending DESC) AS rn
    FROM weekly_sku
),
recent AS (
    SELECT sku, AVG(total_units) AS recent_vel
    FROM ranked WHERE rn <= 13 GROUP BY sku
),
prior AS (
    SELECT sku, AVG(total_units) AS prior_vel
    FROM ranked WHERE rn BETWEEN 14 AND 26 GROUP BY sku
),
trends AS (
    SELECT
        r.sku,
        r.recent_vel,
        p.prior_vel,
        (r.recent_vel - p.prior_vel) / NULLIF(p.prior_vel, 0) AS pct_change
    FROM recent r JOIN prior p ON p.sku = r.sku
)
SELECT
    COUNT(*) AS total_skus,
    COUNT(CASE WHEN pct_change < {decay} THEN 1 END)   AS decaying_skus,
    COUNT(CASE WHEN pct_change >= {decay}
               AND pct_change < {caution} THEN 1 END)  AS caution_skus,
    ROUND(AVG(pct_change)::numeric * 100, 1)           AS avg_pct_change
FROM trends
""".format(
    decay=_CFG["decay_threshold"],
    caution=_CFG["caution_threshold"],
)

_SQL_BY_SKU = """
WITH weekly_sku AS (
    SELECT sku, week_ending, SUM(units_sold) AS total_units
    FROM public_marts.fct_scan_data
    GROUP BY sku, week_ending
),
ranked AS (
    SELECT sku, week_ending, total_units,
        ROW_NUMBER() OVER (PARTITION BY sku ORDER BY week_ending DESC) AS rn
    FROM weekly_sku
),
recent AS (SELECT sku, AVG(total_units) AS recent_vel FROM ranked WHERE rn <= 13 GROUP BY sku),
prior  AS (SELECT sku, AVG(total_units) AS prior_vel  FROM ranked WHERE rn BETWEEN 14 AND 26 GROUP BY sku)
SELECT
    r.sku,
    dp.product_name,
    dp.product_line,
    ROUND(r.recent_vel::numeric, 1) AS recent_13wk,
    ROUND(p.prior_vel::numeric, 1)  AS prior_13wk,
    ROUND((r.recent_vel - p.prior_vel) / NULLIF(p.prior_vel, 0) * 100::numeric, 1) AS pct_change
FROM recent r
JOIN prior p ON p.sku = r.sku
JOIN public_marts.dim_products dp ON dp.sku = r.sku
ORDER BY pct_change ASC
LIMIT 12
"""


class VelocityDecayQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q14",
            question="Which SKUs are slowing down before the buyer notices?",
            short_label="SKU velocity decay?",
            source_piece="Velocity Decision Tool",
            go_deeper_link="https://lailarallc.com/velocity-decision-tool",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        summary = query(_SQL_SUMMARY)[0]
        by_sku = query(_SQL_BY_SKU)

        total_skus = int(summary["total_skus"] or 0)
        decaying = int(summary["decaying_skus"] or 0)
        caution = int(summary["caution_skus"] or 0)
        avg_change = float(summary["avg_pct_change"] or 0)
        cfg = _CFG

        worst = by_sku[0] if by_sku else None

        if decaying > 0:
            verdict = (
                f"{decaying} of {total_skus} SKUs are in active velocity decline "
                f"(13-week vs prior 13-week < {cfg['decay_threshold']:.0%}). "
                f"Worst: {worst['product_name']} — "
                f"{float(worst['recent_13wk']):,.0f} units/week now vs "
                f"{float(worst['prior_13wk']):,.0f} prior ({float(worst['pct_change']):+.1f}%). "
                f"A buyer running scan review in the next 30 days will see this decline first."
            )
            verdict_detail = f"{decaying} SKU(s) in decay"
        elif caution > 0:
            verdict = (
                f"No SKUs are in active decline, but {caution} of {total_skus} "
                f"show weak momentum (< {cfg['caution_threshold']:.0%} growth). "
                f"Slowest: {worst['product_name']} at {float(worst['pct_change']):+.1f}% "
                f"(13 vs prior 13 weeks). "
                f"Portfolio average: {avg_change:+.1f}% — "
                f"these slow movers are the ones the buyer notices first."
            )
            verdict_detail = f"{caution} SKU(s) in caution zone"
        else:
            verdict = (
                f"All {total_skus} SKUs are accelerating: portfolio average {avg_change:+.1f}% "
                f"(13-week vs prior 13-week). "
                f"Slowest momentum: {worst['product_name']} at {float(worst['pct_change']):+.1f}% — "
                f"still growing but the weakest in the portfolio. "
                f"No decay to act on today."
            )
            verdict_detail = "all SKUs accelerating"

        chart_data = ChartData(
            type="bar",
            title="Velocity change: trailing 13 weeks vs prior 13 weeks",
            data=[
                {
                    "sku": r["product_name"],
                    "pct_change": float(r["pct_change"]),
                    "recent_vel": float(r["recent_13wk"]),
                }
                for r in by_sku
            ],
            x_key="sku",
            y_key="pct_change",
            unit="percent",
        )

        return VerdictResponse(
            question_id="q14",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(
                    label="SKUs in decay",
                    value=str(decaying),
                    context=f"< {cfg['decay_threshold']:.0%} velocity change",
                ),
                KeyNumber(
                    label="SKUs in caution",
                    value=str(caution),
                    context=f"< {cfg['caution_threshold']:.0%} growth",
                ),
                KeyNumber(
                    label="Portfolio avg change",
                    value=f"{avg_change:+.1f}%",
                    context="13 wk vs prior 13 wk",
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"Velocity change = (trailing 13-week avg − prior 13-week avg) / prior 13-week avg. "
                f"Computed from fct_scan_data, summed across all stores per SKU. "
                f"Decay threshold: < {cfg['decay_threshold']:.0%}. "
                f"Caution threshold: < {cfg['caution_threshold']:.0%} growth. "
                f"Thresholds from Velocity Decision Tool."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(VelocityDecayQuestion())
