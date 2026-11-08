"""Document search service — public entry point for the /search endpoint."""

from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.search.pipeline import retrieve_search_hits
from app.search.types import DocumentSearchResult
from app.services.bm25_search_service import BM25SearchService
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService


class DocumentSearchService:
    """Independent hybrid document search (BM25 + semantic), separate from /query."""

    def __init__(
        self,
        session: AsyncSession,
        bm25_service: BM25SearchService,
        search_service: SearchService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._session = session
        self._bm25 = bm25_service
        embedding = embedding_service or EmbeddingService()
        self._semantic = search_service or SearchService(session, embedding)

    async def search(
        self,
        query: str,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        exact_phrase: bool = False,
    ) -> DocumentSearchResult:
        started = time.perf_counter()
        cleaned_query = query.strip()
        if not cleaned_query:
            return DocumentSearchResult(
                query=cleaned_query,
                hits=[],
                total_candidates=0,
                latency_ms=0.0,
                bm25_hit_count=0,
                semantic_hit_count=0,
            )

        limit = top_k or settings.BM25_DEFAULT_TOP_K
        hits, total_candidates, bm25_count, semantic_count = await retrieve_search_hits(
            cleaned_query,
            bm25_service=self._bm25,
            semantic_service=self._semantic,
            document_id=document_id,
            top_k=limit,
            exact_phrase=exact_phrase,
        )

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return DocumentSearchResult(
            query=cleaned_query,
            hits=hits,
            total_candidates=total_candidates,
            latency_ms=latency_ms,
            bm25_hit_count=bm25_count,
            semantic_hit_count=semantic_count,
        )
