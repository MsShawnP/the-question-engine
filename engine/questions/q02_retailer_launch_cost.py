"""
Q02: Can I afford this retailer launch?

For each retailer, computes how quickly top-line revenue covers the promotional
investment ("revenue-coverage months" = promo ÷ average monthly revenue). This is a
LIQUIDITY signal, not a profitability one — revenue is not margin. The verdict makes
that distinction explicit and anchors affordability to the modeled launch economics
in the "Cost of Saying Yes" piece, where a launch of this size runs net-cash-negative
in year one once COGS, trade spend, and working capital are counted.

Figures reconcile to CINDERHAVEN_CANONICAL.md (Launch economics: gross Year 1
$499,200 / net cash Year 1 −$36,320).
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

# Modeled launch economics from the "Cost of Saying Yes" piece (CINDERHAVEN_CANONICAL.md).
# These are the source-piece reality check: revenue coverage looks fast, but a launch of
# this size is net-cash-negative in year one.
_MODELED_GROSS_YEAR1 = 499_200
_MODELED_NET_CASH_YEAR1 = -36_320

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
            go_deeper_link="https://lailarallc.com/cost-of-saying-yes",
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
            # Revenue-coverage months: how long top-line revenue takes to cover the
            # promo outlay. A liquidity proxy — NOT a payback/ROI on profit.
            coverage_months = total_promo / monthly_rev if monthly_rev > 0 else 999

            combined.append({
                "retailer_name": name,
                "total_revenue": total_rev,
                "total_promo": total_promo,
                "relationship_months": months,
                "coverage_months": coverage_months,
                "revenue_to_promo": total_rev / total_promo if total_promo > 0 else 0,
            })

        combined.sort(key=lambda x: x["coverage_months"], reverse=True)
        worst = combined[0]  # slowest revenue coverage
        cfg = _CFG
        total_promo_all = sum(r["total_promo"] for r in combined)
        net_cash_str = f"-${abs(_MODELED_NET_CASH_YEAR1):,.0f}"
        modeled = (
            f"the Cost of Saying Yes model shows a launch of this size runs net-cash-negative in "
            f"year one — about {net_cash_str} on ${_MODELED_GROSS_YEAR1:,.0f} of "
            f"gross revenue — once COGS, trade spend, and working capital are counted"
        )

        if worst["coverage_months"] > cfg["breakeven_months_threshold"]:
            verdict = (
                f"Your slowest launch — {worst['retailer_name']} — needs "
                f"{_fmt_months(worst['coverage_months'])} of revenue just to cover its promo outlay, "
                f"beyond the {cfg['breakeven_months_threshold']}-month coverage ceiling. And revenue "
                f"coverage is not profit: {modeled}. Model contribution margin and working capital "
                f"before committing."
            )
            verdict_detail = "slow coverage + thin launch economics"
        else:
            verdict = (
                f"Revenue covers promo spend fast — even the slowest of your retailers "
                f"({worst['retailer_name']}) recovers its promo outlay in "
                f"{_fmt_months(worst['coverage_months'])} of revenue. But revenue coverage is not "
                f"profit: {modeled}. Judge a launch on contribution margin and cash runway, not on "
                f"how fast sales cover the promo check."
            )
            verdict_detail = "revenue covers promo fast — profit is the real test"

        chart_data = ChartData(
            type="bar",
            title="Revenue-to-promo coverage ratio by retailer",
            data=[
                {
                    "retailer": r["retailer_name"],
                    "revenue_to_promo": round(r["revenue_to_promo"], 2),
                    "coverage_months": round(r["coverage_months"], 1),
                }
                for r in combined[:8]
            ],
            x_key="retailer",
            y_key="revenue_to_promo",
            unit="×",
        )

        return VerdictResponse(
            question_id="q02",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(
                    label="Slowest revenue-coverage",
                    value=_fmt_months(worst["coverage_months"]),
                    context=worst["retailer_name"],
                ),
                KeyNumber(
                    label="Modeled Year-1 net cash",
                    value=f"-${abs(_MODELED_NET_CASH_YEAR1):,.0f}",
                    context=f"on ${_MODELED_GROSS_YEAR1:,.0f} gross — Cost of Saying Yes launch model",
                ),
                KeyNumber(
                    label="Total promo investment",
                    value=f"${total_promo_all:,.0f}",
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"Revenue-coverage months = total promo investment ÷ average monthly revenue — a "
                f"liquidity proxy, not profitability. Affordability depends on contribution margin and "
                f"cash runway; the Cost of Saying Yes model puts year-one net cash at "
                f"-${abs(_MODELED_NET_CASH_YEAR1):,.0f} on ${_MODELED_GROSS_YEAR1:,.0f} gross. "
                f"Coverage ceiling: {cfg['breakeven_months_threshold']} months."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(RetailerLaunchCostQuestion())
