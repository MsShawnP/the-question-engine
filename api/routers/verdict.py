from fastapi import APIRouter, HTTPException

from api.models.schemas import VerdictResponse, QuestionMeta
from engine.registry import registry

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
    return q.run()
