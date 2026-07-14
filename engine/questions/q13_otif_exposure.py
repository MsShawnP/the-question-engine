"""
Q13: Am I about to get hit with OTIF penalties I can't see?

Reads fct_retailer_shipments for ASN compliance and on-time delivery.
In the Cinderhaven dataset, all deliveries are on-time (is_on_time = true),
but 8.6% of shipments have late ASNs — the blind spot the question targets.

Rule: if asn_late_rate > ASN_LATE_RATE_THRESHOLD, fires with
exposure = late_asn_count × PENALTY_PER_ASN_LATE.

Walmart flags late ASN as an OTIF violation independently of physical delivery:
the ASN must arrive before or with the shipment. OTIF floor = 95% for large
suppliers (< 95% triggers financial penalties).

Routes to: OTIF Blind Spot.
"""
import yaml
from pathlib import Path

from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_CFG = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "thresholds.yaml").read_text()
)["q13"]

_SQL_SUMMARY = """
SELECT
    COUNT(*)                                                                          AS total_shipments,
    SUM(CASE WHEN asn_sent_late THEN 1 ELSE 0 END)                                   AS late_asn_count,
    SUM(CASE WHEN NOT is_on_time THEN 1 ELSE 0 END)                                  AS late_delivery_count,
    ROUND(SUM(CASE WHEN asn_sent_late THEN 1 ELSE 0 END)::numeric / COUNT(*), 4)     AS asn_late_rate,
    ROUND(SUM(CASE WHEN is_on_time THEN 1 ELSE 0 END)::numeric / COUNT(*), 4)        AS on_time_rate
FROM public_marts.fct_retailer_shipments
"""

_SQL_BY_RETAILER = """
SELECT
    dr.retailer_name,
    COUNT(*)                                                                          AS total_shipments,
    SUM(CASE WHEN fs.asn_sent_late THEN 1 ELSE 0 END)                                AS late_asn,
    ROUND(SUM(CASE WHEN fs.asn_sent_late THEN 1 ELSE 0 END)::numeric / COUNT(*), 4)  AS asn_late_rate,
    ROUND(SUM(CASE WHEN fs.is_on_time THEN 1 ELSE 0 END)::numeric / COUNT(*), 4)     AS on_time_rate
FROM public_marts.fct_retailer_shipments fs
JOIN public_marts.dim_retailers dr ON fs.retailer_id = dr.retailer_id
GROUP BY dr.retailer_name
ORDER BY late_asn DESC
"""


class OtifExposureQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q13",
            question="Am I about to get hit with OTIF penalties I can't see?",
            short_label="OTIF penalty exposure?",
            source_piece="OTIF Blind Spot",
            go_deeper_link="https://lailarallc.com/otif-blind-spot",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        summary = query(_SQL_SUMMARY)[0]
        by_retailer = query(_SQL_BY_RETAILER)

        total_shipments = int(summary["total_shipments"] or 0)
        late_asn = int(summary["late_asn_count"] or 0)
        late_delivery = int(summary["late_delivery_count"] or 0)
        asn_late_rate = float(summary["asn_late_rate"] or 0)
        on_time_rate = float(summary["on_time_rate"] or 0)
        cfg = _CFG

        exposure = late_asn * cfg["penalty_per_asn_late"]
        otif_rate = on_time_rate * (1 - asn_late_rate)
        worst_retailer = by_retailer[0] if by_retailer else None

        if asn_late_rate > cfg["asn_late_rate_threshold"]:
            verdict = (
                f"{late_asn:,} of {total_shipments:,} shipments ({asn_late_rate:.1%}) had late ASNs — "
                f"a Walmart OTIF violation even when the physical delivery arrived on time. "
                f"At ${cfg['penalty_per_asn_late']:,} per incident, "
                f"that's ${exposure:,.0f} in exposure at current run rate. "
                f"Worst account: {worst_retailer['retailer_name']} at {float(worst_retailer['asn_late_rate']):.1%} late ASN rate. "
                f"Physical delivery is {on_time_rate:.1%} on time — the ASN process is the only gap."
            )
            verdict_detail = f"{asn_late_rate:.1%} ASN late — ${exposure:,.0f} exposure"
        else:
            verdict = (
                f"OTIF compliance is clean: {asn_late_rate:.1%} ASN late rate "
                f"(below the {cfg['asn_late_rate_threshold']:.0%} threshold) and "
                f"{on_time_rate:.1%} on-time delivery (above the {cfg['otif_floor']:.0%} Walmart floor) "
                f"across {total_shipments:,} shipments. "
                f"No material penalty exposure at current run rate."
            )
            verdict_detail = "OTIF compliant"

        chart_data = ChartData(
            type="bar",
            title="Late ASN rate by retailer",
            data=[
                {
                    "retailer": r["retailer_name"],
                    "asn_late_rate": float(r["asn_late_rate"]),
                    "late_asn": int(r["late_asn"]),
                    "total_shipments": int(r["total_shipments"]),
                }
                for r in by_retailer
            ],
            x_key="retailer",
            y_key="asn_late_rate",
            unit="share",
        )

        return VerdictResponse(
            question_id="q13",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(
                    label="Late ASN shipments",
                    value=f"{late_asn:,} of {total_shipments:,}",
                    context=f"{asn_late_rate:.1%} of all shipments",
                ),
                KeyNumber(
                    label="Estimated OTIF exposure",
                    value=f"${exposure:,.0f}",
                    context=f"${cfg['penalty_per_asn_late']:,} × late ASN count",
                ),
                KeyNumber(
                    label="On-time delivery rate",
                    value=f"{on_time_rate:.1%}",
                    context=f"Walmart floor: {cfg['otif_floor']:.0%}",
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                f"OTIF exposure = late ASN count × ${cfg['penalty_per_asn_late']:,} per incident. "
                f"Fires when asn_sent_late rate > {cfg['asn_late_rate_threshold']:.0%}. "
                f"Walmart OTIF floor for large suppliers: {cfg['otif_floor']:.0%}. "
                f"Late ASN = ASN arrived after ship date (asn_sent_late = true in fct_retailer_shipments). "
                f"Thresholds from OTIF Blind Spot."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(OtifExposureQuestion())
