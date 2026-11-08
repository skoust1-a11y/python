"""Tests for Langfuse tracing helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.observability.tracing import (
    is_tracing_enabled,
    mask_sources_for_trace,
    observe,
    trace_llm_messages,
    trace_query,
)


def test_is_tracing_enabled_requires_flag_and_keys():
    with patch("app.observability.tracing.settings") as mock_settings:
        mock_settings.ENABLE_LANGFUSE = False
        mock_settings.LANGFUSE_PUBLIC_KEY = "pk"
        mock_settings.LANGFUSE_SECRET_KEY = "sk"
        assert is_tracing_enabled() is False

        mock_settings.ENABLE_LANGFUSE = True
        mock_settings.LANGFUSE_PUBLIC_KEY = ""
        assert is_tracing_enabled() is False

        mock_settings.LANGFUSE_PUBLIC_KEY = "pk"
        mock_settings.LANGFUSE_SECRET_KEY = "sk"
        assert is_tracing_enabled() is True


def test_mask_sources_for_trace_strips_full_text_and_truncates_excerpt():
    sources = [
        {
            "document_name": "Contract A",
            "full_text": "secret full chunk text",
            "excerpt": "x" * 400,
            "score": 0.9,
        }
    ]
    masked = mask_sources_for_trace(sources)
    assert "full_text" not in masked[0]
    assert masked[0]["document_name"] == "Contract A"
    assert masked[0]["excerpt"].endswith("...")
    assert len(masked[0]["excerpt"]) == 303


def test_observe_is_noop_when_tracing_disabled():
    with patch("app.observability.tracing.is_tracing_enabled", return_value=False):

        @observe(name="noop-span")
        def add_one(value: int) -> int:
            return value + 1

        assert add_one(1) == 2


def test_trace_query_yields_none_when_disabled():
    with patch("app.observability.tracing.get_langfuse_client", return_value=None):
        with trace_query(name="test", question="What is force majeure?") as trace:
            assert trace is None


def test_trace_query_creates_observation_when_enabled():
    mock_client = MagicMock()
    mock_observation = MagicMock()
    mock_client.start_as_current_observation.return_value.__enter__.return_value = (
        mock_observation
    )

    with (
        patch("app.observability.tracing.get_langfuse_client", return_value=mock_client),
        patch("app.observability.tracing.flush_traces") as flush_mock,
        patch("langfuse.propagate_attributes") as propagate_mock,
    ):
        propagate_mock.return_value.__enter__.return_value = None
        propagate_mock.return_value.__exit__.return_value = None

        with trace_query(
            name="legal-query",
            question="What is force majeure?",
            session_id="session-1",
            tags=["query"],
        ) as trace:
            assert trace is mock_observation

    mock_client.start_as_current_observation.assert_called_once()
    flush_mock.assert_called_once()


def test_trace_llm_messages_truncates_long_content():
    class FakeMessage:
        def __init__(self, role: str, content: str) -> None:
            self.role = role
            self.content = content

    messages = [FakeMessage("user", "a" * 600)]
    serialized = trace_llm_messages(messages)
    assert serialized[0]["role"] == "user"
    assert serialized[0]["content"].endswith("...")
    assert len(serialized[0]["content"]) == 503
