"""Tests for document search response formatting."""

from uuid import uuid4

from app.search.formatter import format_search_response, to_search_result_item
from app.search.types import DocumentSearchResult, SearchHit
from app.utils.snippet_builder import HighlightSegment


def test_to_search_result_item_maps_snippet_and_highlights() -> None:
    chunk_id = uuid4()
    document_id = uuid4()

    hit = SearchHit(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name="Master Services Agreement",
        chunk_index=12,
        score=0.91,
        raw_score=0.9123,
        snippet="Payment is due within thirty (30) days of invoice.",
        highlights=[
            HighlightSegment(text="Payment is due within ", matched=False),
            HighlightSegment(text="thirty", matched=True),
            HighlightSegment(text=" (30) days of invoice.", matched=False),
        ],
        match_sources=["bm25", "semantic"],
        page_number=7,
        clause_number="4.2",
        clause_title="Payment Terms",
    )

    item = to_search_result_item(hit)

    assert item.document == "Master Services Agreement"
    assert item.content == hit.snippet
    assert len(item.highlights) == 3
    assert item.highlights[1].matched is True
    assert item.metadata.match_sources == ["bm25", "semantic"]


def test_format_search_response_returns_results_not_hits() -> None:
    chunk_id = uuid4()
    document_id = uuid4()

    result = DocumentSearchResult(
        query="payment terms",
        hits=[
            SearchHit(
                chunk_id=chunk_id,
                document_id=document_id,
                document_name="Contract A",
                chunk_index=3,
                score=0.8,
                raw_score=0.82,
                snippet="Net 30 payment terms apply.",
                highlights=[HighlightSegment(text="Net 30 payment terms apply.", matched=False)],
                match_sources=["semantic"],
            )
        ],
        total_candidates=42,
        latency_ms=18.5,
        bm25_hit_count=5,
        semantic_hit_count=7,
    )

    response = format_search_response(result)

    assert response.result_count == 1
    assert len(response.results) == 1
    assert response.results[0].content == "Net 30 payment terms apply."
    assert response.total_candidates == 42
