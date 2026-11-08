"""Tests for the independent document search service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.search.service import DocumentSearchService
from app.services.bm25_search_service import BM25SearchHit, BM25SearchResult
from app.services.search_service import SearchResult
from app.utils.snippet_builder import HighlightSegment


def _bm25_hit(*, chunk_id, document_id, text: str, score: float = 0.8) -> BM25SearchHit:
    snippet = text[:120]
    return BM25SearchHit(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name="Contract A",
        chunk_index=0,
        score=score,
        raw_score=score,
        snippet=snippet,
        highlights=[HighlightSegment(text=snippet, matched=True)],
        chunk_text=text,
    )


def _semantic_hit(*, chunk_id, document_id, text: str, score: float = 0.4) -> SearchResult:
    return SearchResult(
        id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        chunk_text=text,
        metadata={"document_name": "Contract A"},
        score=score,
    )


@pytest.mark.asyncio
async def test_search_returns_snippet_not_full_chunk() -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    long_text = (
        "Termination requires ninety days written notice to the other party. " * 20
    )

    bm25_service = MagicMock()
    bm25_service.search = AsyncMock(
        return_value=BM25SearchResult(
            query="termination notice",
            hits=[_bm25_hit(chunk_id=chunk_id, document_id=document_id, text=long_text)],
            total_candidates=1,
            latency_ms=1.0,
        )
    )

    semantic_service = MagicMock()
    semantic_service.search = AsyncMock(return_value=[])

    service = DocumentSearchService(
        session=MagicMock(),
        bm25_service=bm25_service,
        search_service=semantic_service,
    )

    result = await service.search("termination notice", top_k=5)

    assert len(result.hits) == 1
    assert len(result.hits[0].snippet) < len(long_text)
    assert "termination" in result.hits[0].snippet.lower()
    assert result.hits[0].highlights


@pytest.mark.asyncio
async def test_search_returns_empty_for_unrelated_query() -> None:
    chunk_id = uuid4()
    document_id = uuid4()

    bm25_service = MagicMock()
    bm25_service.search = AsyncMock(
        return_value=BM25SearchResult(
            query="fifaa",
            hits=[
                _bm25_hit(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text="Payment is due within thirty days of invoice.",
                    score=0.1,
                )
            ],
            total_candidates=10,
            latency_ms=1.0,
        )
    )

    semantic_service = MagicMock()
    semantic_service.search = AsyncMock(
        return_value=[
            _semantic_hit(
                chunk_id=chunk_id,
                document_id=document_id,
                text="Payment is due within thirty days of invoice.",
                score=0.2,
            )
        ]
    )

    service = DocumentSearchService(
        session=MagicMock(),
        bm25_service=bm25_service,
        search_service=semantic_service,
    )

    result = await service.search("fifaa", top_k=5)

    assert result.hits == []
