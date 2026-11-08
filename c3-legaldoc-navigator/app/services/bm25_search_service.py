"""BM25 keyword search over indexed document chunks."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.orm import Clause, Document, DocumentEmbedding
from app.rag.bm25_retrieval import (
    BM25ChunkRecord,
    BM25CorpusIndex,
    build_bm25_index,
    search_bm25,
    search_exact_phrase,
)
from app.utils.bm25_tokenizer import parse_search_query, tokenize_query
from app.utils.citation_formatter import extract_location_from_metadata
from app.utils.chunk_text_formatter import clean_chunk_text
from app.utils.snippet_builder import HighlightSegment, build_snippet

_TEXT_AVAILABLE = or_(
    and_(
        DocumentEmbedding.chunk_text.isnot(None),
        DocumentEmbedding.chunk_text != "",
    ),
    and_(
        DocumentEmbedding.content_preview.isnot(None),
        DocumentEmbedding.content_preview != "",
    ),
)


@dataclass(frozen=True)
class BM25SearchHit:
    """A single BM25-ranked chunk match."""

    chunk_id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    score: float
    raw_score: float
    snippet: str
    highlights: list[HighlightSegment]
    clause_id: UUID | None = None
    page_number: int | None = None
    clause_number: str | None = None
    clause_title: str | None = None
    chunk_text: str = ""


@dataclass(frozen=True)
class BM25SearchResult:
    """Aggregated BM25 search output."""

    query: str
    hits: list[BM25SearchHit]
    total_candidates: int
    latency_ms: float


class BM25SearchService:
    """Sparse BM25 retrieval over indexed document chunk text."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._cache: OrderedDict[str, BM25CorpusIndex] = OrderedDict()

    async def search(
        self,
        query: str,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        exact_phrase: bool = False,
    ) -> BM25SearchResult:
        started = time.perf_counter()
        cleaned_query = query.strip()
        if not cleaned_query:
            return BM25SearchResult(
                query=cleaned_query,
                hits=[],
                total_candidates=0,
                latency_ms=0.0,
            )

        parsed_query, auto_exact_phrase = parse_search_query(cleaned_query)
        use_exact_phrase = exact_phrase or auto_exact_phrase
        search_text = parsed_query

        query_terms = tokenize_query(search_text)
        if not query_terms and not use_exact_phrase:
            return BM25SearchResult(
                query=cleaned_query,
                hits=[],
                total_candidates=0,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )

        index = await self._get_index(document_id=document_id)
        if not index.chunks:
            return BM25SearchResult(
                query=cleaned_query,
                hits=[],
                total_candidates=0,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )

        limit = top_k or settings.BM25_DEFAULT_TOP_K
        if use_exact_phrase:
            ranked = search_exact_phrase(index, search_text)
        else:
            ranked = search_bm25(index, search_text, top_k=limit)

        hits = _build_hits(ranked[:limit], search_text)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return BM25SearchResult(
            query=cleaned_query,
            hits=hits,
            total_candidates=len(index.chunks),
            latency_ms=latency_ms,
        )

    async def _get_index(self, *, document_id: UUID | None) -> BM25CorpusIndex:
        cache_key = str(document_id) if document_id else "__global__"
        fingerprint = await self._corpus_fingerprint(document_id=document_id)
        cached = self._cache.get(cache_key)
        if cached is not None and cached.fingerprint == fingerprint:
            self._cache.move_to_end(cache_key)
            return cached

        chunks = await self._load_chunks(document_id=document_id)
        index = build_bm25_index(chunks, fingerprint=fingerprint)
        self._cache[cache_key] = index
        self._cache.move_to_end(cache_key)
        while len(self._cache) > settings.BM25_CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)
        return index

    async def _corpus_fingerprint(self, *, document_id: UUID | None) -> str:
        stmt = (
            select(
                func.count(DocumentEmbedding.id),
                func.max(DocumentEmbedding.updated_at),
            )
            .join(Document, DocumentEmbedding.document_id == Document.id)
            .where(
                Document.status == "indexed",
                _TEXT_AVAILABLE,
            )
        )
        if document_id is not None:
            stmt = stmt.where(DocumentEmbedding.document_id == document_id)

        result = await self._session.execute(stmt)
        count, updated_at = result.one()
        timestamp = updated_at.isoformat() if isinstance(updated_at, datetime) else "none"
        scope = str(document_id) if document_id else "global"
        return f"{scope}:{int(count or 0)}:{timestamp}"

    async def _load_chunks(self, *, document_id: UUID | None) -> list[BM25ChunkRecord]:
        stmt = (
            select(DocumentEmbedding, Document.filename, Document.title, Clause)
            .join(Document, DocumentEmbedding.document_id == Document.id)
            .outerjoin(Clause, DocumentEmbedding.clause_id == Clause.id)
            .where(
                Document.status == "indexed",
                _TEXT_AVAILABLE,
            )
            .order_by(DocumentEmbedding.document_id, DocumentEmbedding.chunk_index)
        )
        if document_id is not None:
            stmt = stmt.where(DocumentEmbedding.document_id == document_id)

        rows = (await self._session.execute(stmt)).all()
        chunks: list[BM25ChunkRecord] = []
        for record, filename, title, clause in rows:
            raw_text = record.chunk_text or record.content_preview or ""
            text = clean_chunk_text(raw_text)
            if not text:
                continue
            location = extract_location_from_metadata(record.embed_metadata)
            clause_number = location.clause_number if location else None
            clause_title = location.clause_title if location else None
            page_number = location.page_number if location else _extract_page_number(
                record.embed_metadata
            )
            if clause is not None:
                clause_number = clause_number or clause.clause_number
                clause_title = clause_title or clause.title
                if page_number is None:
                    page_number = clause.page_number
            chunks.append(
                BM25ChunkRecord(
                    id=record.id,
                    document_id=record.document_id,
                    document_name=title or filename,
                    chunk_index=record.chunk_index,
                    chunk_text=text,
                    clause_id=record.clause_id,
                    page_number=page_number,
                    clause_number=clause_number,
                    clause_title=clause_title,
                )
            )
        return chunks


def _build_hits(
    ranked: list[tuple[BM25ChunkRecord, float]],
    query: str,
) -> list[BM25SearchHit]:
    if not ranked:
        return []

    max_score = max(score for _, score in ranked)
    hits: list[BM25SearchHit] = []
    for chunk, raw_score in ranked:
        normalized = round(raw_score / max_score, 4) if max_score > 0 else 0.0
        snippet, highlights = build_snippet(
            chunk.chunk_text,
            query,
            max_chars=settings.BM25_SNIPPET_MAX_CHARS,
        )
        hits.append(
            BM25SearchHit(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                chunk_index=chunk.chunk_index,
                score=normalized,
                raw_score=round(raw_score, 4),
                snippet=snippet,
                highlights=highlights,
                clause_id=chunk.clause_id,
                page_number=chunk.page_number,
                clause_number=chunk.clause_number,
                clause_title=chunk.clause_title,
                chunk_text=chunk.chunk_text,
            )
        )
    return hits


def _extract_page_number(metadata: dict[str, Any] | None) -> int | None:
    if not metadata:
        return None
    value = metadata.get("page_number")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
