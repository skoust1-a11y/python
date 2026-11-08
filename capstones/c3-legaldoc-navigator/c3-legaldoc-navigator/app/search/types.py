"""Data types for the document search pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.utils.snippet_builder import HighlightSegment


@dataclass(frozen=True)
class SearchHit:
    """A single ranked search result with a focused excerpt."""

    chunk_id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    score: float
    raw_score: float
    snippet: str
    highlights: list[HighlightSegment]
    match_sources: list[str]
    clause_id: UUID | None = None
    page_number: int | None = None
    clause_number: str | None = None
    clause_title: str | None = None


@dataclass(frozen=True)
class DocumentSearchResult:
    """Aggregated output from the document search pipeline."""

    query: str
    hits: list[SearchHit]
    total_candidates: int
    latency_ms: float
    bm25_hit_count: int
    semantic_hit_count: int
