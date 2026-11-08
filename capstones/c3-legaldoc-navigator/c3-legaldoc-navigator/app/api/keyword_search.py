"""Hybrid BM25 + semantic document search API."""

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_document_search_service
from app.models.schemas import KeywordSearchRequest, KeywordSearchResponse
from app.search.formatter import format_search_response
from app.search.service import DocumentSearchService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


@router.post(
    "/search",
    response_model=KeywordSearchResponse,
    summary="Hybrid document search",
    description=(
        "Search indexed legal documents using an independent BM25 + semantic pipeline. "
        "Returns focused excerpts with keyword highlighting — no LLM synthesis. "
        "Unrelated queries with no lexical or semantic matches return zero results."
    ),
)
async def keyword_search(
    body: KeywordSearchRequest,
    search_service: DocumentSearchService = Depends(get_document_search_service),
) -> KeywordSearchResponse:
    """Run hybrid BM25 + semantic search over indexed document chunks."""
    logger.info(
        "Document search received: query_length=%d scoped=%s exact_phrase=%s",
        len(body.query),
        body.document_id is not None,
        body.exact_phrase,
    )

    result = await search_service.search(
        body.query,
        document_id=body.document_id,
        top_k=body.top_k,
        exact_phrase=body.exact_phrase,
    )

    return format_search_response(result)
