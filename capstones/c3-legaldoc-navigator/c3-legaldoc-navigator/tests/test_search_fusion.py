"""Unit tests for BM25 + semantic search fusion."""

from dataclasses import dataclass
from uuid import uuid4

from app.utils.search_fusion import fuse_search_rankings
from app.utils.snippet_builder import HighlightSegment


@dataclass
class _Bm25Hit:
    chunk_id: object
    document_id: object
    document_name: str
    chunk_index: int
    score: float
    raw_score: float
    snippet: str
    highlights: list[HighlightSegment]
    chunk_text: str
    clause_id: object | None = None
    page_number: int | None = None
    clause_number: str | None = None
    clause_title: str | None = None


@dataclass
class _SemanticHit:
    id: object
    document_id: object
    chunk_index: int
    chunk_text: str
    metadata: dict | None
    score: float
    clause_id: object | None = None
    keywords: list[str] | None = None


def _bm25_hit(
    *,
    chunk_id,
    document_id,
    chunk_index: int,
    score: float,
    text: str,
) -> _Bm25Hit:
    return _Bm25Hit(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=f"Doc {chunk_index}",
        chunk_index=chunk_index,
        score=score,
        raw_score=score,
        snippet=text[:120],
        highlights=[HighlightSegment(text=text[:120], matched=False)],
        chunk_text=text,
    )


def _semantic_hit(
    *,
    chunk_id,
    document_id,
    chunk_index: int,
    score: float,
    text: str,
) -> _SemanticHit:
    return _SemanticHit(
        id=chunk_id,
        document_id=document_id,
        chunk_index=chunk_index,
        chunk_text=text,
        metadata={"document_name": f"Doc {chunk_index}"},
        score=score,
    )


def test_fusion_boosts_chunks_present_in_both_rankings() -> None:
    shared_id = uuid4()
    doc_id = uuid4()
    other_bm25_id = uuid4()
    other_semantic_id = uuid4()

    bm25_hits = [
        _bm25_hit(
            chunk_id=other_bm25_id,
            document_id=doc_id,
            chunk_index=1,
            score=0.95,
            text="Keyword-only indemnification clause.",
        ),
        _bm25_hit(
            chunk_id=shared_id,
            document_id=doc_id,
            chunk_index=2,
            score=0.80,
            text="Shared termination and notice obligations.",
        ),
    ]
    semantic_hits = [
        _semantic_hit(
            chunk_id=shared_id,
            document_id=doc_id,
            chunk_index=2,
            score=0.92,
            text="Shared termination and notice obligations.",
        ),
        _semantic_hit(
            chunk_id=other_semantic_id,
            document_id=doc_id,
            chunk_index=3,
            score=0.88,
            text="Semantic match about contract breach remedies.",
        ),
    ]

    fused = fuse_search_rankings(bm25_hits, semantic_hits, top_k=3)

    assert len(fused) == 3
    assert str(fused[0].node.id_) == str(shared_id)


def test_fusion_returns_semantic_only_when_bm25_empty() -> None:
    semantic_id = uuid4()
    doc_id = uuid4()
    semantic_hits = [
        _semantic_hit(
            chunk_id=semantic_id,
            document_id=doc_id,
            chunk_index=0,
            score=0.77,
            text="Late payment penalties and interest accrual.",
        )
    ]

    fused = fuse_search_rankings([], semantic_hits, top_k=5)

    assert len(fused) == 1
    assert str(fused[0].node.id_) == str(semantic_id)


def test_fusion_returns_bm25_only_when_semantic_empty() -> None:
    bm25_id = uuid4()
    doc_id = uuid4()
    bm25_hits = [
        _bm25_hit(
            chunk_id=bm25_id,
            document_id=doc_id,
            chunk_index=0,
            score=0.66,
            text="Force majeure events and notice requirements.",
        )
    ]

    fused = fuse_search_rankings(bm25_hits, [], top_k=5)

    assert len(fused) == 1
    assert str(fused[0].node.id_) == str(bm25_id)
