"""
Q08: What does one wrong weight cost?

Computes annual dollar exposure from weight data errors:
  1. Count SKUs with missing/zero case weights (data layer risk)
  2. Find compliance deductions in fct_retailer_deductions (realized cost)
  3. Combine: realized compliance cost + projected exposure from data errors

Thresholds calibrated from Dimension & Weight Integrity piece.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q08"]

_SQL_WEIGHT_ERRORS = """
SELECT
    COUNT(*)                                                                     AS total_skus,
    COUNT(CASE WHEN case_weight_lbs IS NULL OR case_weight_lbs <= 0 THEN 1 END) AS weight_errors,
    COUNT(CASE WHEN unit_weight_lbs IS NULL OR unit_weight_lbs <= 0 THEN 1 END) AS unit_weight_errors,
    AVG(CASE WHEN case_weight_lbs > 0 THEN cogs_per_unit * case_pack_qty END)   AS avg_case_cost
FROM public_marts.dim_products
"""

_SQL_COMPLIANCE_DEDUCTIONS = """
SELECT
    LOWER(deduction_type)          AS deduction_type,
    SUM(deduction_amount)          AS total_amount,
    SUM(net_deduction_amount)      AS net_amount,
    COUNT(*)                       AS count,
    AVG(deduction_amount)          AS avg_per_incident
FROM public_marts.fct_retailer_deductions
WHERE LOWER(deduction_type) LIKE '%compliance%'
   OR LOWER(deduction_type) LIKE '%weight%'
   OR LOWER(deduction_type) LIKE '%dimension%'
   OR LOWER(deduction_type) LIKE '%label%'
GROUP BY LOWER(deduction_type)
ORDER BY total_amount DESC
"""

_SQL_SHIPMENTS = """
SELECT
    COUNT(*)                                                                AS total_shipments,
    GREATEST(CEIL((MAX(ship_date) - MIN(ship_date))::numeric / 7 + 1), 1)   AS data_weeks
FROM public_marts.fct_retailer_shipments
"""


class WeightCostQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q08",
            question="What does one wrong weight cost?",
            short_label="Cost of wrong weight?",
            source_piece="Dimension & Weight Integrity",
            go_deeper_link="/dimension-weight-integrity",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        weight_summary = query(_SQL_WEIGHT_ERRORS)[0]
        compliance_rows = query(_SQL_COMPLIANCE_DEDUCTIONS)
        shipment_row = query(_SQL_SHIPMENTS)[0]

        total_skus = int(weight_summary["total_skus"])
        weight_errors = int(weight_summary["weight_errors"])
        avg_case_cost = float(weight_summary["avg_case_cost"] or 0)
        total_shipments = int(shipment_row["total_shipments"])
        data_weeks = float(shipment_row["data_weeks"] or 0)

        total_compliance = sum(float(r["total_amount"]) for r in compliance_rows)
        # Weight the per-incident average by incident counts (a plain mean of
        # per-type averages over-weights rare deduction types).
        total_incidents = sum(int(r["count"]) for r in compliance_rows)
        avg_per_incident = total_compliance / total_incidents if total_incidents > 0 else 0

        error_rate = weight_errors / total_skus if total_skus > 0 else 0
        # Project annual exposure: shipments per week over the data window,
        # annualized (× 52), × error rate × avg compliance cost per incident.
        weekly_shipments = total_shipments / data_weeks if data_weeks > 0 else 0
        annual_shipments = weekly_shipments * _CFG["error_multiplier_annual"]
        projected_annual = error_rate * annual_shipments * avg_per_incident

        if total_compliance > 0:
            verdict = (
                f"Realized compliance deductions tied to weight/dimension/label issues: "
                f"${total_compliance:,.0f} — averaging ${avg_per_incident:,.0f} per incident. "
                f"{weight_errors} of {total_skus} SKUs ({error_rate:.0%}) have missing or zero "
                f"case weight data, creating ongoing exposure. "
                f"Projected annual risk at current error rate: ${projected_annual:,.0f}."
            )
            verdict_detail = f"${total_compliance:,.0f} realized, ${projected_annual:,.0f} projected"
        else:
            verdict = (
                f"{weight_errors} of {total_skus} SKUs ({error_rate:.0%}) have weight data gaps. "
                f"No compliance deductions found matching weight/dimension issues — but this data "
                f"risk is active. At ${avg_case_cost:,.0f} average case cost and "
                f"{total_shipments} historical shipments, one systemic error would be costly."
            )
            verdict_detail = f"{weight_errors} SKUs at risk"

        chart_data = ChartData(
            type="bar",
            title="Compliance deductions by type",
            data=(
                [
                    {
                        "type": r["deduction_type"].replace("_", " ").title(),
                        "total_amount": float(r["total_amount"]),
                        "count": int(r["count"]),
                    }
                    for r in compliance_rows
                ]
                if compliance_rows
                else [{"type": "No compliance deductions found", "total_amount": 0, "count": 0}]
            ),
            x_key="type",
            y_key="total_amount",
            unit="dollars",
        )

        return VerdictResponse(
            question_id="q08",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(label="Realized compliance deductions", value=f"${total_compliance:,.0f}"),
                KeyNumber(
                    label="SKUs with weight data gaps",
                    value=f"{weight_errors} of {total_skus}",
                    context=f"{error_rate:.0%} error rate",
                ),
                KeyNumber(label="Projected annual exposure", value=f"${projected_annual:,.0f}"),
            ],
            chart=chart_data,
            rule_explanation=(
                "Compliance deductions = deduction_type containing 'c