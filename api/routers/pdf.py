from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from engine.registry import registry

router = APIRouter()

PDF_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "pdfs"


@router.get("/pdf/{question_id}")
def get_pdf(question_id: str):
    """Serve the pre-rendered one-pager for a question.

    PDFs are static artifacts built by `make pdfs` (scripts/render_pdfs.py) —
    nothing is rendered on request.
    """
    q = registry.get(question_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
    if q.meta().is_stub:
        raise HTTPException(status_code=503, detail="This question is not yet implemented")
    pdf_path = PDF_DIR / f"{question_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"No rendered PDF for '{question_id}'")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"ask-cinderhaven-{question_id}.pdf",
    )
