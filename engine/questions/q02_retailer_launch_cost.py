"""
Q02: Can I afford this retailer launch?

Uses actual launch data from the Cinderhaven dataset. For each retailer, computes
total promotional investment vs. cumulative revenue to derive a payback period.
Verdict fires when the costliest launch has a payback > BREAKEVEN_MONTHS_THRESHOLD.

Thresholds calibrated from Cost of Saying Yes piece.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q02"]

_SQL_REVENUE = """
SELECT
    dr.retailer_name,
    SUM(fo.total_value)                       AS total_revenue,
    MIN(fo.po_date)                           AS first_order,
    MAX(fo.po_date)                           AS last_order,
    EXTRACT(MONTH FROM AGE(MAX(fo.po_date), MIN(fo.po_date))) +
        EXTRACT(YEAR FROM AGE(MAX(fo.po_date), MIN(fo.po_date))) * 12 AS relationship_months
FROM public_marts.fct_retailer_orders fo
JOIN public_marts.dim_retailers dr ON fo.retailer_id = dr.retailer_id
GROUP BY dr.retailer_name
"""

_SQL_PROMO = """
SELECT
    retailer,
    SUM(promo_cost) AS total_promo_cost,
    COUNT(*)        AS promo_count
FROM public_marts.fct_promotions
GROUP BY retailer
"""


def _fmt_months(m: float) -> str:
    return "< 1 month" if m < 1 else f"{m:.0f} months"


class RetailerLaunchCostQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q02",
            question="Can I afford this retailer launch?",
            short_label="Afford the retailer launch?",
            source_piece="Cost of Saying Yes",
            go_deeper_link="/cost-of-saying-yes",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        revenue_rows = {r["retailer_name"]: r for r in query(_SQL_REVENUE)}
        promo_rows = {r["retailer"]: r for r in query(_SQL_PROMO)}

        combined = []
        for name, rev in revenue_rows.items():
            promo = promo_rows.get(name, {})
            total_promo = float(promo.get("total_promo_cost") or 0)
            total_rev = float(rev["total_revenue"] or 0)
            months = float(rev["relationship_months"] or 1)
            monthly_rev = total_rev / max(months, 1)
            payback_months = total_promo / monthly_rev if monthly_rev > 0 else 999

            combined.append({
                "retailer_name": name,
                "total_revenue": total_rev,
                "total_promo": total_promo,
                "relationship_months": months,
                "payback_months": payback_months,
                "roi_multiple": total_rev / total_promo if total_promo > 0 else 0,
            })

        combined.sort(key=lambda x: x["payback_months"], reverse=True)
        worst = combined[0]
        cfg = _CFG

        if worst["payback_months"] > cfg["breakeven_months_threshold"]:
            verdict = (
                f"Your most expensive launch — {worst['retailer_name']} — required "
                f"{_fmt_months(worst['payback_months'])} to break even on promo investment. "
                f"That exceeds the {cfg['breakeven_months_threshold']}-month ceiling. "
                f"Before the next launch, model working capital through month {cfg['working_capital_buffer_months'] + int(worst['payback_months'])}."
            )
            verdict_detail = "breakeven exceeded"
        else:
            best = min(combined, key=lambda x: x["payback_months"])
            verdict = (
                f"All retailer launches break even within {cfg['breakeven_months_threshold']} months. "
                f"Fastest payback: {best['retailer_name']} in {_fmt_months(best['payback_months'])} "
                f"({best['roi_multiple']:.1f}× ROI on promo spend). "
                f"Current launch economics are within range."
            )
            verdict_detail = "all launches affordable"

        chart_data = ChartData(
            type="bar",
            title="Promo investment vs. revenue by retailer",
            data=[
                {
                    "retailer": r["retailer_name"],
                    "roi_multiple": round(r["roi_multiple"], 2),
                    "payback_months": round(r["payback_months"], 1),
                }
                for r in combined[:8]
            ],
            x_key="retailer",
            y_key="roi_multiple",
            unit="multiple",
        )

        return VerdictResponse(
            question_id="q02",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(
                    label="Longest payback",
                    value=_fmt_months(worst["payback_months"]),
                    context=worst["retailer_name"],
                ),
                KeyNumber(
                    label="Threshold",
                    value=f"{cfg['breakeven_months_threshold']} months",
                    context="max acceptable payback",
                ),
                KeyNumber(
                    label="Total promo investment",
                    value=f"${sum(r['total_promo'] for r in combined):,.0f}",
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"Payback = total promo investment ÷ average monthly revenue. "
                f"Fires when any retailer's payback > {cfg['breakeven_months_threshold']} months. "
                f"Thresholds from Cost of Saying Yes piece."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(RetailerLaunchCostQuestion())
