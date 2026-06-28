"""RAG query API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_query_service
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    RoutingMetadata,
    SourceCitation,
    StructuredMetadata,
)
from app.services.query_service import QueryService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query legal documents",
    description=(
        "Ask a natural-language question. The system routes the query to RAG, "
        "SQL, or hybrid retrieval and returns a grounded answer with citations."
    ),
    responses={
        400: {"description": "Guardrail violation or invalid query"},
        502: {"description": "LLM or routing provider error"},
    },
)
async def query_documents(
    body: QueryRequest,
    query_service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    """Query legal documents using intelligent routing (RAG, SQL, or Hybrid)."""
    logger.info("Query received: question_length=%d", len(body.question))
    result = await query_service.ask(
        body.question,
        document_id=body.document_id,
        top_k=body.top_k,
        similarity_threshold=body.similarity_threshold,
        provider=body.provider,
    )

    sources = [
        SourceCitation(
            document_id=_parse_uuid(source.get("document_id")),
            chunk_index=source.get("chunk_index"),
            excerpt=source["excerpt"],
            score=source["score"],
            citation_label=source.get("citation_label"),
            source_type=source.get("source_type", "vector"),
            entity_id=_parse_uuid(source.get("entity_id")),
            entity_type=source.get("entity_type"),
            metadata=source.get("metadata"),
        )
        for source in result.sources
    ]

    structured: StructuredMetadata | None = None
    if result.structured_metadata is not None:
        payload = result.structured_metadata
        structured = StructuredMetadata(
            contracts=payload.get("contracts", []),
            clauses=payload.get("clauses", []),
            cases=payload.get("cases", []),
            metadata_records=payload.get("metadata_records", []),
            plan_explanation=payload.get("plan_explanation"),
            total_count=payload.get("total_count", 0),
        )

    return QueryResponse(
        answer=result.answer,
        explanation=result.explanation,
        sources=sources,
        structured_metadata=structured,
        routing=RoutingMetadata(
            route=result.routing.route,
            reason=result.routing.reason,
            confidence=result.routing.confidence,
        ),
        confidence_score=result.confidence_score,
        provider=result.provider,
        retrieved_count=result.retrieved_count,
        vector_count=result.vector_count,
        sql_count=result.sql_count,
    )
