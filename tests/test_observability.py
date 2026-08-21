"""Unit tests for Langfuse observability, traceability, and evaluation metrics."""

from unittest.mock import MagicMock

from app.config.settings import Settings, get_settings, reset_settings
from app.models.analysis import FinalRecommendation
from app.models.common import DataSourceMetadata, Evidence
from app.workflow.observability import create_langfuse_handler, record_workflow_evaluations
from app.workflow.state import InvestmentState, SelectedStock, UserRequest


def test_create_langfuse_handler_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    reset_settings()
    settings = get_settings()
    assert not settings.is_langfuse_enabled
    state = InvestmentState(request=UserRequest(text="Analyze AAPL"))
    handler = create_langfuse_handler(state)
    assert handler is None


def test_create_langfuse_handler_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    reset_settings()

    state = InvestmentState(
        request=UserRequest(text="Analyze AAPL", analysis_type="stock_analysis"),
        selected_stock=SelectedStock(symbol="AAPL"),
    )
    handler = create_langfuse_handler(state)
    reset_settings()
    assert handler is not None
    assert "investment-board" in handler.tags
    assert "stock_analysis" in handler.tags
    assert "AAPL" in handler.tags


def test_record_workflow_evaluations() -> None:
    mock_handler = MagicMock()
    mock_handler.get_trace_id.return_value = "trace-123"
    mock_langfuse = MagicMock()
    mock_handler.langfuse = mock_langfuse

    initial_state = InvestmentState()
    final_state = InvestmentState(
        final_recommendation=FinalRecommendation(
            summary="Buy",
            recommendation="Strong buy",
            confidence=0.85,
        ),
        evidence=[
            Evidence(
                source=DataSourceMetadata(
                    provider="market_data",
                    source="yahoo",
                    timestamp="2026-08-21T00:00:00Z",
                ),
                field="price",
                value=150.0,
            )
        ],
    )

    record_workflow_evaluations(mock_handler, initial_state, final_state)

    assert mock_langfuse.score.called
    score_names = [call.kwargs.get("name") for call in mock_langfuse.score.call_args_list]
    assert "synthesis_confidence" in score_names
    assert "evidence_grounding" in score_names
    assert "conflict_resolution" in score_names
    mock_handler.flush.assert_called_once()
