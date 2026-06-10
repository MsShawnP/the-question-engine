"""
Q10: Am I leaving deduction money on the table?

Rule: if expired deductions (dispute window closed, never disputed) exceed
DISPUTABLE_THRESHOLD of total gross deductions, money is being left on the table.
Secondary signal: if dispute win rate < WIN_RATE_FLOOR, the dispute process is broken.

Thresholds calibrated from Retailer Deduction Recovery piece.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q10"]

_SQL = """
SELECT
    SUM(deduction_amount)                                                          AS total_gross,
    SUM(net_deduction_amount)                                                      AS total_net,
    SUM(recovered_amount)                                                          AS total_recovered,

    SUM(CASE WHEN deduction_status = 'open'     THEN deduction_amount END)         AS open_amount,
    SUM(CASE WHEN deduction_status = 'disputed' THEN deduction_amount END)         AS disputed_amount,
    SUM(CASE WHEN deduction_status = 'expired'  THEN deduction_amount END)         AS expired_amount,

    COUNT(CASE WHEN deduction_status = 'open'     THEN 1 END)                      AS open_count,
    COUNT(CASE WHEN deduction_status = 'disputed' THEN 1 END)                      AS disputed_count,
    COUNT(CASE WHEN deduction_status = 'expired'  THEN 1 END)                      AS expired_count,

    COUNT(CASE WHEN dispute_outcome = 'overturned' THEN 1 END)                     AS wins,
    COUNT(CASE WHEN dispute_outcome = 'sustained'  THEN 1 END)                     AS losses,
    COUNT(CASE WHEN dispute_outcome IS NOT NULL     THEN 1 END)                     AS closed_disputes,

    ROUND(AVG(typical_recovery_rate)::numeric, 4)                                  AS avg_recovery_rate
FROM public_marts.fct_retailer_deductions
"""

_SQL_BY_RETAILER = """
SELECT
    dr.retailer_name,
    SUM(fd.deduction_amount)                                                AS gross_deductions,
    SUM(CASE WHEN fd.deduction_status = 'expired' THEN fd.deduction_amount END) AS expired_amount,
    SUM(fd.recovered_amount)                                                AS recovered
FROM public_marts.fct_retailer_deductions fd
JOIN public_marts.dim_retailers dr ON fd.retailer_id = dr.retailer_id
GROUP BY dr.retailer_name
ORDER BY expired_amount DESC NULLS LAST
LIMIT 8
"""


class DeductionRecoveryQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q10",
            question="Am I leaving deduction money on the table?",
            short_label="Leaving deduction money?",
            source_piece="Retailer Deduction Recovery",
            go_deeper_link="/retailer-deduction-recovery",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        summary = query(_SQL)[0]
        by_retailer = query(_SQL_BY_RETAILER)

        total_gross = float(summary["total_gross"] or 0)
        expired_amount = float(summary["expired_amount"] or 0)
        total_recovered = float(summary["total_recovered"] or 0)
        wins = int(summary["wins"] or 0)
        closed = int(summary["closed_disputes"] or 0)
        open_amount = float(summary["open_amount"] or 0)

        expired_rate = expired_amount / total_gross if total_gross > 0 else 0
        win_rate = wins / closed if closed > 0 else 0
        avg_recovery_rate = float(summary["avg_recovery_rate"] or 0)
        potential_recovery = open_amount * avg_recovery_rate
        cfg = _CFG

        left_on_table = expired_rate > cfg["disputable_threshold"]
        broken_process = win_rate < cfg["win_rate_floor"] and closed > 0

        if left_on_table and broken_process:
            verdict = (
                f"${expired_amount:,.0f} in deductions ({expired_rate:.0%} of total) "
                f"expired without a dispute filed — that window is permanently closed. "
                f"And your dispute win rate is only {win_rate:.0%} — "
                f"well below the {cfg['win_rate_floor']:.0%} floor. "
                f"Two problems: money already lost, and the recovery process is broken."
            )
            verdict_detail = "money left + broken process"
        elif left_on_table:
            verdict = (
                f"${expired_amount:,.0f} in deductions ({expired_rate:.0%} of total) "
                f"expired without action — that money is permanently gone. "
                f"Your dispute win rate ({win_rate:.0%}) is healthy, "
                f"but the filing velocity needs to increase. "
                f"${potential_recovery:,.0f} in open deductions is still actionable."
            )
            verdict_detail = "money left on table"
        elif broken_process:
            verdict = (
                f"You're filing disputes on time, but winning only {win_rate:.0%} — "
                f"below the {cfg['win_rate_floor']:.0%} floor. "
                f"The evidence package or escalation process needs work. "
                f"${total_recovered:,.0f} has been recovered to date; "
                f"${potential_recovery:,.0f} remains open."
            )
            verdict_detail = "dispute process needs work"
        else:
            verdict = (
                f"Deduction recovery is in good shape: {win_rate:.0%} win rate, "
                f"{expired_rate:.0%} expired (below {cfg['disputable_threshold']:.0%} threshold). "
                f"${total_recovered:,.0f} recovered to date. "
                f"${potential_recovery:,.0f} in open deductions is still working through the pipeline."
            )
            verdict_detail = "healthy"

        chart_data = ChartData(
            type="bar",
            title="Expired deductions by retailer (unrecoverable)",
            data=[
                {
                    "retailer": r["retailer_name"],
                    "expired_amount": float(r["expired_amount"] or 0),
                    "gross_deductions": float(r["gross_deductions"]),
                    "recovered": float(r["recovered"] or 0),
                }
                for r in by_retailer
            ],
            x_key="retailer",
            y_key="expired_amount",
            unit="dollars",
        )

        return VerdictResponse(
            question_id="q10",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(
                    label="Expired without dispute",
                    value=f"${expired_amount:,.0f}",
                    context=f"{expired_rate:.0%} of gross deductions",
                ),
                KeyNumber(label="Dispute win rate", value=f"{win_rate:.0%}"),
                KeyNumber(
                    label="Still recoverable",
                    value=f"${potential_recovery:,.0f}",
                    context="open × avg recovery rate",
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"Expired = deduction_status = 'expired' (dispute window closed, never filed). "
                f"Fires when expired share > {cfg['disputable_threshold']:.0%} of gross deductions. "
                f"Secondary: dispute win rate < {cfg['win_rate_floor']:.0%}. "
                f"Win = dispute_outcome = 'overturned'. "
                f"Thresholds from Retailer Deduction Recovery."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(DeductionRecoveryQuestion())
