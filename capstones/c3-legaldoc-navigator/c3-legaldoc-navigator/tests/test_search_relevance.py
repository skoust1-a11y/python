"""Tests for search-specific relevance filtering."""

from uuid import uuid4

from app.search.relevance import (
    filter_bm25_hits,
    filter_semantic_hits,
    is_search_relevant,
    query_terms_appear_in_text,
)
from app.services.bm25_search_service import BM25SearchHit
from app.services.search_service import SearchResult
from app.utils.snippet_builder import HighlightSegment


def _bm25_hit(*, text: str, raw_score: float = 1.5) -> BM25SearchHit:
    return BM25SearchHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_name="Contract",
        chunk_index=0,
        score=0.9,
        raw_score=raw_score,
        snippet=text[:80],
        highlights=[HighlightSegment(text=text[:80], matched=False)],
        chunk_text=text,
    )


def _semantic_hit(*, text: str, score: float) -> SearchResult:
    return SearchResult(
        id=uuid4(),
        document_id=uuid4(),
        chunk_index=0,
        chunk_text=text,
        metadata=None,
        score=score,
    )


def test_query_terms_appear_in_text_requires_lexical_overlap() -> None:
    assert query_terms_appear_in_text("termination notice", "Thirty days written notice.")
    assert not query_terms_appear_in_text("fifaa", "Payment is due within thirty days.")


def test_filter_bm25_hits_drops_unrelated_terms() -> None:
    hits = [
        _bm25_hit(text="Termination requires ninety days written notice."),
        _bm25_hit(text="Indemnification covers third-party claims."),
    ]

    filtered = filter_bm25_hits("fifaa", hits)

    assert filtered == []


def test_filter_semantic_hits_applies_threshold() -> None:
    hits = [
        _semantic_hit(text="Termination clause", score=0.8),
        _semantic_hit(text="Random chunk", score=0.2),
    ]

    filtered = filter_semantic_hits(hits, threshold=0.55)

    assert len(filtered) == 1
    assert filtered[0].score == 0.8


def test_is_search_relevant_rejects_semantic_only_below_threshold() -> None:
    semantic = _semantic_hit(text="Unrelated boilerplate text.", score=0.3)

    assert not is_search_relevant(
        "fifaa",
        semantic.chunk_text,
        exact_phrase=False,
        bm25_hit=None,
        semantic_hit=semantic,
    )
