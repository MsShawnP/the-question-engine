"""
Unit tests for the rules engine.

No DB required — Q01 rule logic uses mock data.
DB integration tests go in tests/test_integration.py (requires live connection).
"""
import pytest
from unittest.mock import patch
from engine.registry import registry
from api.models.schemas import QuestionMeta


def test_registry_has_fifteen_questions():
    assert len(registry.all()) == 15


def test_all_questions_have_valid_meta():
    for q in registry.all():
        meta = q.meta()
        assert isinstance(meta, QuestionMeta)
        assert meta.id.startswith("q")
        assert len(meta.question) > 5
        assert meta.scenario in ("baseline", "distressed")


def test_stub_questions_raise_not_implemented():
    stubs = [q for q in registry.all() if q.meta().is_stub]
    assert len(stubs) > 0
    for q in stubs:
        with pytest.raises(NotImplementedError):
            q.run()


def test_question_ids_are_unique():
    ids = [q.meta().id for q in registry.all()]
    assert len(ids) == len(set(ids))


def test_q04_is_distressed_scenario():
    from engine.questions.q04_trade_spend import TradeSpendQuestion
    assert TradeSpendQuestion().meta().scenario == "distressed"


def test_q01_rule_fire():
    """Concentrated + high deduction burden → renegotiate verdict."""
    from engine.questions.q01_biggest_customer import BiggestCustomerQuestion

    mock_rows = [
        {"retailer_name": "Big Box Co", "revenue_share": 0.55, "deduction_rate": 0.22,
         "net_margin": 0.78, "gross_revenue": 1_100_000, "total_deductions": 242_000, "net_revenue": 858_000},
        {"retailer_name": "Mid Grocer", "revenue_share": 0.28, "deduction_rate": 0.07,
         "net_margin": 0.93, "gross_revenue": 560_000, "total_deductions": 39_200, "net_revenue": 520_800},
        {"retailer_name": "Small Chain", "revenue_share": 0.17, "deduction_rate": 0.05,
         "net_margin": 0.95, "gross_revenue": 340_000, "total_deductions": 17_000, "net_revenue": 323_000},
    ]
    q = BiggestCustomerQuestion()
    with patch("engine.questions.q01_biggest_customer.query", return_value=mock_rows):
        result = q.run()

    assert "concentrated" in result.verdict_detail
    assert "high deduction" in result.verdict_detail
    assert "Renegotiate" in result.verdict or "renegotiate" in result.verdict


def test_q01_rule_healthy():
    """Low concentration + low deduction rate → healthy verdict."""
    from engine.questions.q01_biggest_customer import BiggestCustomerQuestion

    mock_rows = [
        {"retailer_name": "Account A", "revenue_share": 0.30, "deduction_rate": 0.06,
         "net_margin": 0.94, "gross_revenue": 600_000, "total_deductions": 36_000, "net_revenue": 564_000},
        {"retailer_name": "Account B", "revenue_share": 0.35, "deduction_rate": 0.08,
         "net_margin": 0.92, "gross_revenue": 700_000, "total_deductions": 56_000, "net_revenue": 644_000},
        {"retailer_name": "Account C", "revenue_share": 0.35, "deduction_rate": 0.10,
         "net_margin": 0.90, "gross_revenue": 700_000, "total_deductions": 70_000, "net_revenue": 630_000},
    ]
    q = BiggestCustomerQuestion()
    with patch("engine.questions.q01_biggest_customer.query", return_value=mock_rows):
        result = q.run()

    assert result.verdict_detail == "healthy"


def test_q01_concentrated_but_acceptable():
    """Concentrated but low deduction rate → 'build second account' verdict."""
    from engine.questions.q01_biggest_customer import BiggestCustomerQuestion

    mock_rows = [
        {"retailer_name": "Dominant", "revenue_share": 0.55, "deduction_rate": 0.06,
         "net_margin": 0.94, "gross_revenue": 1_100_000, "total_deductions": 66_000, "net_revenue": 1_034_000},
        {"retailer_name": "Small", "revenue_share": 0.45, "deduction_rate": 0.08,
         "net_margin": 0.92, "gross_revenue": 900_000, "total_deductions": 72_000, "net_revenue": 828_000},
    ]
    q = BiggestCustomerQuestion()
    with patch("engine.questions.q01_biggest_customer.query", return_value=mock_rows):
        result = q.run()

    assert result.verdict_detail == "concentrated but acceptable deductions"
