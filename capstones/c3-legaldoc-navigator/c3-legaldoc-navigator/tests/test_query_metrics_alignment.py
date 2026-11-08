"""Tests for evidence-aligned relevance metrics on /query responses."""

from types import SimpleNamespace
from uuid import uuid4

from app.models.mode_responses import ModeResponses
from app.prompts.shared import EVIDENCE_NONE_FOUND_RESPONSE
from app.utils.response_builder import build_query_response


def _source(score: float, *, text: str) -> dict:
    return {
        "document_id": str(uuid4()),
        "metadata": {"filename": "Agreement.pdf", "semantic_score": score},
        "score": score,
        "citation_label": "[Source 1]",
        "full_text": text,
        "excerpt": text,
    }


def test_build_query_response_uses_aligned_zero_relevance():
    result = SimpleNamespace(
        responses=ModeResponses(
            strict=EVIDENCE_NONE_FOUND_RESPONSE,
            explain="I could not find sufficient information in the uploaded documents.",
            analysis="",
        ),
        sources=[
            _source(
                0.62,
                text="This Agreement is governed by the laws of Delaware.",
            )
        ],
        relevance=0.0,
        faithfulness=1.0,
        confidence_score=0.4,
        confidence_level="Low",
        verification_notice="verify",
        retrieved_count=1,
        latency_ms=120.0,
    )

    response = build_query_response("Who won the World Cup?", result)

    assert response.relevance == 0.0
    assert response.confidence == 0.4
