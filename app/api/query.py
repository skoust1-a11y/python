"""RAG query API endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_query_service
from app.models.schemas import QueryRequest, QueryResponse
from app.services.query_service import QueryService
from app.utils.response_builder import build_query_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query legal documents",
    description=(
        "Ask a natural-language question. The system routes the query to RAG, "
        "SQL, or hybrid retrieval and returns a structured answer with citations, "
        "related documents, and follow-up questions."
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

    return build_query_response(body.question, result, include_contexts=body.include_contexts)
