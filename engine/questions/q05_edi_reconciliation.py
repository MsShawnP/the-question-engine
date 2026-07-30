"""
Q05: Why don't my numbers match my distributor's?

Depends on EDI Reconciliation v2 — STUB until that piece ships.
"""
from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta


class EdiReconciliationQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q05",
            question="Why don't my numbers match my distributor's?",
            short_label="Numbers vs. distributor?",
            source_piece="EDI Reconciliation Tool",
            go_deeper_link="https://reconcile.lailarallc.com",
            scenario="baseline",
            is_stub=True,
        )

    def run(self) -> VerdictResponse:
        raise NotImplementedError("Depends on EDI Reconciliation v2 — stub until that piece ships")


registry.register(EdiReconciliationQuestion())
