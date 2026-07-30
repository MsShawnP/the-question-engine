"""
Q06: What would a recall cost me?

Depends on Recall Blast Radius piece — STUB until that piece ships.
"""
from engine.base import BaseQuestion
from engine.registry import registry
from api.models.schemas import VerdictResponse, QuestionMeta


class RecallCostQuestion(BaseQuestion):
    def meta(self) -> QuestionMeta:
        return QuestionMeta(
            id="q06",
            question="What would a recall cost me?",
            short_label="What would a recall cost?",
            source_piece="Recall Blast Radius",
            go_deeper_link="https://recall.lailarallc.com",
            scenario="distressed",
            is_stub=True,
        )

    def run(self) -> VerdictResponse:
        raise NotImplementedError("Depends on Recall Blast Radius piece — stub until that piece ships")


registry.register(RecallCostQuestion())
