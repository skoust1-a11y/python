"""Assemble structured API responses from internal query results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.models.schemas import QueryResponse, RelatedDocument, SourceCitation
from app.utils.citation_formatter import format_document_citations
from app.utils.follow_up_generator import (
    extract_follow_up_from_answer,
    generate_follow_up_questions,
)

if TYPE_CHECKING:
    from app.services.query_dispatcher import QueryResult


def build_related_documents(sources: list[SourceCitation]) -> list[RelatedDocument]:
    """Map document-level citations to a compact related-documents list."""
    related: list[RelatedDocument] = []
    seen: set[str] = set()

    for source in sources:
        key = str(source.document_id) if source.document_id else source.document_name.casefold()
        if key in seen:
            continue
        seen.add(key)
        related.append(
            RelatedDocument(
                document_id=source.document_id,
                name=source.document_name,
                relevance=source.score,
            )
        )

    related.sort(key=lambda item: (-item.relevance, item.name.casefold()))
    return related


def _clean_mode_answer(answer: str) -> str:
    cleaned, _ = extract_follow_up_from_answer(answer)
    return cleaned


def build_query_response(
    question: str,
    result: QueryResult | Any,
    include_contexts: bool = False,
) -> QueryResponse:
    """Convert an internal query result into the public structured response."""
    sources = format_document_citations(result.sources)
    responses = result.responses

    follow_up_questions = generate_follow_up_questions(
        question=question,
        answer=responses.analysis,
        sources=sources,
        response_mode="analysis",
    )

    contexts = None
    if include_contexts and result.sources:
        contexts = [
            source.get("full_text") or source.get("excerpt", "")
            for source in result.sources
            if isinstance(source, dict) and (source.get("full_text") or source.get("excerpt"))
        ]

    return QueryResponse(
        strict=_clean_mode_answer(responses.strict),
        explain=_clean_mode_answer(responses.explain),
        analysis=_clean_mode_answer(responses.analysis),
        confidence=result.confidence_score,
        confidence_level=result.confidence_level,
        verification_notice=result.verification_notice,
        sources=sources,
        related_documents=build_related_documents(sources),
        follow_up_questions=follow_up_questions,
        latency_ms=result.latency_ms,
        contexts=contexts,
    )
