import logging

from fastapi import APIRouter, HTTPException

from api.models.schemas import VerdictResponse, QuestionMeta
from engine.base import NoDataError
from engine.registry import registry

logger = logging.getLogger(__name__)

_FRIENDLY_UNAVAILABLE = (
    "We couldn't compute this verdict right now — the data source may be unavailable."
)

router = APIRouter()


@router.get("/questions", response_model=list[QuestionMeta])
def list_questions():
    return [q.meta() for q in registry.all()]


@router.get("/questions/{question_id}", response_model=QuestionMeta)
def get_question(question_id: str):
    q = registry.get(question_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
    return q.meta()


@router.post("/verdict/{question_id}", response_model=VerdictResponse)
def run_verdict(question_id: str):
    q = registry.get(question_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
    if q.meta().is_stub:
        raise HTTPException(status_code=503, detail="This question is not yet implemented")
    try:
        return q.run()
    except NoDataError as exc:
        logger.warning("Verdict %s returned no data: %s", question_id, exc)
        raise HTTPException(status_code=503, detail=_FRIENDLY_UNAVAILABLE)
    except Exception:
        logger.exception("Verdict %s failed", question_id)
        raise HTTPException(status_code=503, detail=_FRIENDLY_UNAVAILABLE)
