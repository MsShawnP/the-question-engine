"""
Q01: Should I fire my biggest customer?

Rule: if largest retailer by revenue holds > CONCENTRATION_THRESHOLD of total revenue
AND their deduction burden > DEDUCTION_BURDEN_THRESHOLD (i.e., they claw back an
abnormally high fraction of invoiced revenue), verdict is "renegotiate before walking."

Thresholds calibrated from Retailer Scorecard piece.
"Margin" here is revenue retained after net deductions — the cleanest proxy available
without per-retailer COGS allocation.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion, NoDataError
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q01"]

_SQL = """
WITH retailer_rev AS (
    SELECT
        dr.retailer_id,
        dr.retailer_name,
        SUM(fo.total_value) AS gross_revenue
    FROM public_marts.fct_retailer_orders fo
    JOIN public_marts.dim_retailers dr ON fo.retailer_id = dr.retailer_id
    GROUP BY dr.retailer_id, dr.retailer_name
),
retailer_ded AS (
    SELECT retailer_id, SUM(net_deduction_amount) AS total_deductions
    FROM public_marts.fct_retailer_deductions
    GROUP BY retailer_id
),
combined AS (
    SELECT
        rr.retailer_name,
        rr.gross_revenue,
        COALESCE(rd.total_deductions, 0) AS total_deductions,
        rr.gross_revenue - COALESCE(rd.total_deductions, 0) AS net_revenue
    FROM retailer_rev rr
    LEFT JOIN retailer_ded rd ON rr.retailer_id = rd.retailer_id
),
totals AS (SELECT SUM(gross_revenue) AS total FROM combined)
SELECT
    c.retailer_name,
    c.gross_revenue,
    ROUND((c.gross_revenue / t.total)::numeric, 4)                        AS revenue_share,
    ROUND((c.total_deductions / NULLIF(c.gross_revenue, 0))::numeric, 4)  AS deduction_rate,
    ROUND((c.net_revenue / NULLIF(c.gross_revenue, 0))::numeric, 4)       AS net_margin,
    c.total_deductions,
    c.net_revenue
FROM combined c, totals t
ORDER BY c.gross_revenue DESC
"""


class BiggestCustomerQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q01",
            question="Should I fire my biggest customer?",
            short_label="Fire your biggest account?",
            source_piece="Retailer Scorecard & Renegotiation Simulator",
            go_deeper_link="/retailer-scorecard",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        rows = query(_SQL)
        if not rows:
            raise NoDataError("q01: no retailer revenue rows returned")

        top = rows[0]
        concentration = float(top["revenue_share"])
        deduction_rate = float(top["deduction_rate"])
        avg_deduction_rate = sum(float(r["deduction_rate"]) for r in rows) / len(rows)

        cfg = _CFG
        concentrated = concentration > cfg["revenue_concentration_threshold"]
        high_burden = deduction_rate > cfg["deduction_burden_threshold"]

        if concentrated and high_burden:
            verdict = (
                f"{top['retailer_name']} is {concentration:.0%} of your revenue "
                f"but claws back {deduction_rate:.0%} of every invoice through deductions — "
                f"nearly {deduction_rate / avg_deduction_rate:.1f}× the portfolio average. "
                f"Renegotiate terms before walking; three of the five cost-to-serve levers are fixable."
            )
            verdict_detail = "concentrated + high deduction burden"
        elif concentrated:
            verdict = (
                f"{top['retailer_name']} is {concentration:.0%} of your revenue "
                f"with a manageable {deduction_rate:.0%} deduction rate. "
                f"Concentration is the risk — build a second account to at least "
                f"{cfg['target_second_account_share']:.0%} before the next negotiation."
            )
            verdict_detail = "concentrated but acceptable deductions"
        elif high_burden:
            verdict = (
                f"{top['retailer_name']} has a high deduction rate ({deduction_rate:.0%}) "
                f"but is only {concentration:.0%} of revenue — manageable risk. "
                f"Still worth a deduction audit before the next contract renewal."
            )
            verdict_detail = "high deductions but not concentrated"
        else:
            verdict = (
                f"Your largest account is {concentration:.0%} of revenue "
                f"with a {deduction_rate:.0%} deduction rate — both within normal range. "
                f"Nothing to act on today."
            )
            verdict_detail = "healthy"

        chart_data = ChartData(
            type="bar",
            title="Revenue share by retailer",
            data=[
                {
                    "retailer": r["retailer_name"],
                    "revenue_share": float(r["revenue_share"]),
                    "deduction_rate": float(r["deduction_rate"]),
                }
                for r in rows[:8]
            ],
            x_key="retailer",
            y_key="revenue_share",
            unit="share",
        )

        return VerdictResponse(
            question_id="q01",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(
                    label="Biggest account revenue share",
                    value=f"{concentration:.0%}",
                ),
                KeyNumber(
                    label="Biggest account deduction rate",
                    value=f"{deduction_rate:.0%}",
                    context="% of invoiced revenue clawed back",
                ),
                KeyNumber(
                    label="Portfolio avg deduction rate",
                    value=f"{avg_deduction_rate:.0%}",
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"Fires when revenue concentration > {cfg['revenue_concentration_threshold']:.0%} "
                f"AND deduction rate > {cfg['deduction_burden_threshold']:.0%}. "
                f"Deduction rate = net deductions ÷ gross revenue per retailer. "
                f"Thresholds from Retailer Scorecard cost-to-serve model."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(BiggestCustomerQuestion())
