"""
Q09: Which channel actually makes money?

Reads mart_channel_contribution — the only table where retailer, distributor,
and DTC pipelines are reconciled on a common cost basis.

Rule: names any channel with negative contribution_margin.
If all channels are positive, verdict ranks them by contribution_margin.

No thresholds needed — any negative channel is an automatic verdict.
"""
from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta, KeyNumber, ChartData
from db.connection import query

_SQL = """
SELECT
    channel,
    gross_revenue,
    total_cogs,
    gross_margin,
    total_deductions,
    total_recovered,
    total_chargebacks,
    total_trade_spend,
    net_revenue,
    contribution_margin,
    ROUND(revenue_share::numeric, 4) AS revenue_share
FROM public_marts.mart_channel_contribution
ORDER BY contribution_margin DESC
"""


class ChannelProfitabilityQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q09",
            question="Which channel actually makes money?",
            short_label="Which channel makes money?",
            source_piece="Channel Profitability Analysis",
            go_deeper_link="/channel-profitability",
            scenario="baseline",
        )

    def run(self) -> VerdictResponse:
        rows = query(_SQL)

        best = rows[0]
        worst = rows[-1]
        negatives = [r for r in rows if float(r["contribution_margin"]) < 0]
        total_contribution = sum(float(r["contribution_margin"]) for r in rows)

        if negatives:
            neg_names = ", ".join(r["channel"] for r in negatives)
            neg_total = sum(float(r["contribution_margin"]) for r in negatives)
            verdict = (
                f"{neg_names} {'is' if len(negatives) == 1 else 'are'} contribution-margin negative — "
                f"${abs(neg_total):,.0f} drag on the business after COGS, deductions, and trade spend. "
                f"Every dollar of revenue from {'this channel' if len(negatives) == 1 else 'these channels'} "
                f"is destroying value. "
                f"{best['channel']} is the one making money: "
                f"${float(best['contribution_margin']):,.0f} contribution margin."
            )
            verdict_detail = f"{len(negatives)} channel(s) negative"
        else:
            verdict = (
                f"All channels are contribution-margin positive. "
                f"{best['channel']} leads with ${float(best['contribution_margin']):,.0f} "
                f"({float(best['revenue_share']):.0%} of revenue). "
                f"{worst['channel']} is weakest at ${float(worst['contribution_margin']):,.0f} — "
                f"positive but worth watching given its cost structure."
            )
            verdict_detail = "all channels positive"

        chart_data = ChartData(
            type="bar",
            title="Contribution margin by channel",
            data=[
                {
                    "channel": r["channel"],
                    "contribution_margin": float(r["contribution_margin"]),
                    "revenue_share": float(r["revenue_share"]),
                }
                for r in rows
            ],
            x_key="channel",
            y_key="contribution_margin",
            unit="dollars",
        )

        return VerdictResponse(
            question_id="q09",
            question=self.meta().question,
            verdict=verdict,
            verdict_detail=verdict_detail,
            key_numbers=[
                KeyNumber(
                    label="Best channel",
                    value=best["channel"],
                    context=f"${float(best['contribution_margin']):,.0f} contribution margin",
                ),
                KeyNumber(
                    label="Weakest channel",
                    value=worst["channel"],
                    context=f"${float(worst['contribution_margin']):,.0f}",
                ),
                KeyNumber(
                    label="Total contribution margin",
                    value=f"${total_contribution:,.0f}",
                ),
            ],
            chart=chart_data,
            rule_explanation=(
                "Source: mart_channel_contribution — the only table where retailer, distributor, "
                "and DTC pipelines are reconciled on a common cost basis. "
                "Contribution margin = net_revenue − COGS − trade_spend. "
                "Any negative contribution_margin is an automatic verdict."
            ),
            go_deeper_link=self.meta().go_deeper_link,
            go_deeper_label=self.meta().source_piece,
            scenario=self.meta().scenario,
            source_piece=self.meta().source_piece,
        )


registry.register(ChannelProfitabilityQuestion())
