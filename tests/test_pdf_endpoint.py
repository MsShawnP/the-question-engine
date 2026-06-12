"""
Tests for GET /api/pdf/{question_id} — pre-rendered one-pager delivery.

No DB required: the endpoint serves static files and reads only question
metadata from the registry.
"""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_pdf_known_question_returns_pdf():
    resp = client.get("/api/pdf/q01")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert "ask-cinderhaven-q01.pdf" in resp.headers.get("content-disposition", "")


def test_pdf_all_non_stub_questions_available():
    from engine.registry import registry

    for q in registry.all():
        meta = q.meta()
        if meta.is_stub:
            continue
        resp = client.get(f"/api/pdf/{meta.id}")
        assert resp.status_code == 200, f"{meta.id} PDF missing"


def test_pdf_unknown_question_404():
    resp = client.get("/api/pdf/q99")
    assert resp.status_code == 404


def test_pdf_stub_question_503():
    resp = client.get("/api/pdf/q05")
    assert resp.status_code == 503
