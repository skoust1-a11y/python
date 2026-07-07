"""Serialize document search hits for the /search API response."""

from __future__ import annotations

from app.models.schemas import (
    DirectEvidenceItem,
    DirectEvidenceMetadata,
    KeywordSearchResponse,
    SnippetHighlight,
)
from app.search.types import DocumentSearchResult, SearchHit


def to_search_result_item(hit: SearchHit) -> DirectEvidenceItem:
    """Map an internal search hit to the public API result item."""
    return DirectEvidenceItem(
        document=hit.document_name,
        page=hit.page_number,
        chunk=hit.chunk_index,
        score=hit.score,
        content=hit.snippet,
        highlights=[
            SnippetHighlight(text=segment.text, matched=segment.matched)
            for segment in hit.highlights
        ],
        metadata=DirectEvidenceMetadata(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            clause_id=hit.clause_id,
            clause_number=hit.clause_number,
            clause_title=hit.clause_title,
            relevance_type="match",
            match_sources=hit.match_sources,
            raw_score=hit.raw_score,
        ),
    )


def format_search_response(result: DocumentSearchResult) -> KeywordSearchResponse:
    """Map a document search result to the public KeywordSearchResponse."""
    return KeywordSearchResponse(
        query=result.query,
        total_candidates=result.total_candidates,
        result_count=len(result.hits),
        results=[to_search_result_item(hit) for hit in result.hits],
        latency_ms=result.latency_ms,
        bm25_hit_count=result.bm25_hit_count,
        semantic_hit_count=result.semantic_hit_count,
    )
