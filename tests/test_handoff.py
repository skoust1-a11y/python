"""Unit tests for human handoff escalation workflow."""

from uuid import uuid4

import pytest

from app.handoff.evaluator import evaluate_escalation_triggers
from app.handoff.summary import generate_handoff_summary
from app.models.schemas import ConversationTurn, HandoffRequest, SourceCitation


SAMPLE_SOURCES = [
    {
        "document_id": str(uuid4()),
        "chunk_index": 0,
        "excerpt": "The governing law shall be Delaware.",
        "score": 0.85,
        "citation_label": "[Source 1]",
        "source_type": "vector",
    }
]


class TestEscalationEvaluator:
    def test_escalates_on_low_confidence(self) -> None:
        result = evaluate_escalation_triggers(
            question="What is the governing law?",
            answer="Delaware law applies [Source 1].",
            confidence_score=0.55,
            sources=SAMPLE_SOURCES,
        )
        assert result.should_escalate
        assert any("confidence_score below threshold" in reason for reason in result.reasons)

    def test_escalates_on_missing_citations(self) -> None:
        result = evaluate_escalation_triggers(
            question="What is the governing law?",
            answer="Delaware law applies to this agreement.",
            confidence_score=0.9,
            sources=SAMPLE_SOURCES,
        )
        assert result.should_escalate
        assert "no supporting citations" in result.reasons

    def test_escalates_on_empty_sources(self) -> None:
        result = evaluate_escalation_triggers(
            question="What is the governing law?",
            answer="Delaware law applies.",
            confidence_score=0.9,
            sources=[],
        )
        assert result.should_escalate
        assert "no supporting citations" in result.reasons

    def test_escalates_on_high_risk_query(self) -> None:
        result = evaluate_escalation_triggers(
            question="Should I sue my employer for breach of contract?",
            answer="The contract includes a Delaware governing law clause [Source 1].",
            confidence_score=0.9,
            sources=SAMPLE_SOURCES,
        )
        assert result.should_escalate
        assert "high-risk legal advice requested" in result.reasons

    def test_does_not_escalate_when_healthy(self) -> None:
        result = evaluate_escalation_triggers(
            question="What is the governing law?",
            answer="Delaware law governs the agreement [Source 1].",
            confidence_score=0.9,
            sources=SAMPLE_SOURCES,
        )
        assert not result.should_escalate
        assert result.reasons == []

    def test_allows_insufficient_info_without_citations(self) -> None:
        result = evaluate_escalation_triggers(
            question="What is the governing law?",
            answer="I could not find relevant information in the indexed documents.",
            confidence_score=0.9,
            sources=[],
        )
        assert not result.should_escalate


class TestHandoffSummary:
    def test_generates_structured_summary(self) -> None:
        summary = generate_handoff_summary(
            question="Should I terminate the contract?",
            answer="The termination clause requires 30 days notice [Source 1].",
            confidence_score=0.55,
            escalation_reasons=["confidence_score below threshold (0.5500 < 0.7)"],
            sources=SAMPLE_SOURCES,
            conversation_history=[
                {"role": "user", "message": "Should I terminate the contract?"},
            ],
            retrieved_documents=[
                {
                    "id": str(uuid4()),
                    "filename": "contract.txt",
                    "title": "Master Services Agreement",
                }
            ],
        )
        assert "Human Handoff Escalation Summary" in summary
        assert "Should I terminate the contract?" in summary
        assert "confidence_score below threshold" in summary
        assert "Master Services Agreement" in summary


class TestHandoffRequestSchema:
    def test_accepts_full_payload(self) -> None:
        payload = HandoffRequest(
            question="Should I sue?",
            answer="You may want to review the dispute clause [Source 1].",
            confidence_score=0.6,
            sources=[
                SourceCitation(
                    excerpt="Disputes are resolved by arbitration.",
                    score=0.8,
                    citation_label="[Source 1]",
                )
            ],
            conversation_history=[
                ConversationTurn(role="user", message="Should I sue?"),
            ],
            session_id=uuid4(),
        )
        assert payload.question == "Should I sue?"
        assert len(payload.sources) == 1
