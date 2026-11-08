"""Assemble structured API responses from internal query results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.utils.answer_metrics import (
    compute_confidence_from_evidence,
    compute_faithfulness,
    compute_relevance,
)
from app.models.schemas import (
    AnalysisEvaluationResponse,
    ClaimEvaluationResponse,
    QueryResponse,
    RelatedDocument,
    SourceCitation,
)
from app.utils.citation_formatter import format_document_citations
from app.utils.follow_up_generator import (
    extract_follow_up_from_answer,
    generate_follow_up_questions,
)

if TYPE_CHECKING:
    from app.models.analysis_evaluation import AnalysisEvaluation
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


def _to_evaluation_response(
    evaluation: AnalysisEvaluation | None,
) -> AnalysisEvaluationResponse | None:
    if evaluation is None:
        return None
    return AnalysisEvaluationResponse(
        claims=[
            ClaimEvaluationResponse(
                claim=claim.claim,
                status=claim.status,
                supporting_sources=claim.supporting_sources,
                notes=claim.notes,
            )
            for claim in evaluation.claims
        ],
        missing_evidence=evaluation.missing_evidence,
        missing_information=evaluation.missing_information,
        assumptions=evaluation.assumptions,
        inferences=evaluation.inferences,
        calculations=evaluation.calculations,
        ambiguities=evaluation.ambiguities,
        hallucination_detected=evaluation.hallucination_detected,
        summary=evaluation.summary,
        metrics_explanation=evaluation.metrics_explanation,
        faithfulness=evaluation.faithfulness,
        relevance=evaluation.relevance,
        confidence=evaluation.confidence,
    )


def _resolve_metrics(
    result: QueryResult | Any,
    *,
    sources: list[SourceCitation],
    explain_answer: str,
) -> tuple[float, float, float]:
    """Derive faithfulness, relevance, and confidence from query-service scores or fallbacks."""
    evaluation = result.responses.analysis_evaluation
    source_dicts = result.sources if isinstance(result.sources, list) else []

    if hasattr(result, "relevance") and hasattr(result, "faithfulness"):
        faithfulness = float(result.faithfulness)
        relevance = float(result.relevance)
        confidence = float(getattr(result, "confidence_score", 0.0))
        return faithfulness, relevance, confidence

    if evaluation is not None:
        return evaluation.faithfulness, evaluation.relevance, evaluation.confidence

    faithfulness = compute_faithfulness(evaluation)
    relevance = compute_relevance(source_dicts)
    confidence = compute_confidence_from_evidence(
        evaluation=evaluation,
        sources=source_dicts,
        explain_answer=explain_answer,
        retrieved_count=getattr(result, "retrieved_count", 0),
        top_k=5,
    )
    return faithfulness, relevance, confidence


def build_query_response(
    question: str,
    result: QueryResult | Any,
    include_contexts: bool = False,
) -> QueryResponse:
    """Convert an internal query result into the public structured response."""
    sources = format_document_citations(result.sources)
    responses = result.responses
    explain_answer = _clean_mode_answer(responses.explain)

    faithfulness, relevance, confidence = _resolve_metrics(
        result,
        sources=sources,
        explain_answer=explain_answer,
    )

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
        explain=explain_answer,
        analysis=_clean_mode_answer(responses.analysis),
        confidence=confidence if confidence > 0 else result.confidence_score,
        faithfulness=faithfulness,
        relevance=relevance,
        analysis_evaluation=_to_evaluation_response(responses.analysis_evaluation),
        confidence_level=result.confidence_level,
        verification_notice=result.verification_notice,
        sources=sources,
        related_documents=build_related_documents(sources),
        follow_up_questions=follow_up_questions,
        latency_ms=result.latency_ms,
        contexts=contexts,
    )
