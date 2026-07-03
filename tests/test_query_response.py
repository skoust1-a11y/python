"""Tests for structured query response assembly."""

from types import SimpleNamespace
from uuid import uuid4

from app.models.schemas import SourceCitation
from app.models.mode_responses import ModeResponses
from app.utils.follow_up_generator import extract_follow_up_from_answer, generate_follow_up_questions
from app.utils.response_builder import build_query_response, build_related_documents


def test_build_related_documents_deduplicates_by_document_id():
    doc_id = uuid4()
    sources = [
        SourceCitation(
            document_id=doc_id,
            document_name="Contract A.pdf",
            score=0.9,
            citation_labels=["[Source 1]"],
        ),
        SourceCitation(
            document_id=doc_id,
            document_name="Contract A.pdf",
            score=0.7,
            citation_labels=["[Source 2]"],
        ),
        SourceCitation(
            document_id=uuid4(),
            document_name="Policy B.pdf",
            score=0.8,
            citation_labels=["[Source 3]"],
        ),
    ]

    related = build_related_documents(sources)

    assert len(related) == 2
    assert related[0].name == "Contract A.pdf"
    assert related[0].relevance == 0.9


def test_extract_follow_up_from_answer_removes_embedded_section():
    answer = (
        "The termination clause allows 30 days notice.\n\n"
        "Follow-up questions:\n"
        "- What are the penalties for early termination?\n"
        "- Who must receive written notice?\n"
    )

    cleaned, questions = extract_follow_up_from_answer(answer)

    assert "Follow-up questions" not in cleaned
    assert len(questions) == 2
    assert questions[0].startswith("What are the penalties")


def test_generate_follow_up_questions_uses_templates_when_not_embedded():
    sources = [
        SourceCitation(
            document_id=uuid4(),
            document_name="MSA.pdf",
            score=0.85,
        )
    ]

    questions = generate_follow_up_questions(
        question="What is the liability cap?",
        answer="The liability cap is $1M.",
        sources=sources,
        response_mode="explain",
    )

    assert len(questions) >= 2
    assert any("MSA.pdf" in question for question in questions)


def test_build_query_response_returns_all_mode_fields():
    doc_id = uuid4()
    result = SimpleNamespace(
        responses=ModeResponses(
            strict="Strict answer.",
            explain="Explain answer.",
            analysis=(
                "Analysis answer.\n\nSuggested follow-up questions:\n"
                "- What triggers termination?"
            ),
        ),
        sources=[
            {
                "document_id": str(doc_id),
                "metadata": {"filename": "Agreement.pdf", "clause_number": "4.2"},
                "score": 0.88,
                "citation_label": "[Source 1]",
                "full_text": "chunk text must not leak",
                "excerpt": "chunk excerpt must not leak",
            }
        ],
        confidence_score=0.88,
        confidence_level="High",
        verification_notice=None,
        latency_ms=4200.5,
    )

    response = build_query_response("What is the notice period?", result)

    assert response.strict == "Strict answer."
    assert response.explain == "Explain answer."
    assert response.analysis == "Analysis answer."
    assert response.confidence == 0.88
    assert response.confidence_level == "High"
    assert response.verification_notice is None
    assert len(response.sources) == 1
    assert response.sources[0].document_name == "Agreement.pdf"
    assert "full_text" not in response.model_dump_json()
    assert "excerpt" not in response.model_dump_json()
    assert len(response.related_documents) == 1
    assert response.related_documents[0].name == "Agreement.pdf"
    assert len(response.follow_up_questions) >= 1
    assert response.latency_ms == 4200.5
