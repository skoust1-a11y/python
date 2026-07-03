"""Cosine similarity vector search via pgvector + SQLAlchemy."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.orm import DocumentEmbedding
from app.rag.ranking import candidate_pool_size
from app.utils.search_filter import apply_similarity_threshold
from app.services.embedding_service import EmbeddingService


@dataclass
class SearchResult:
    """A single semantic search hit."""

    id: UUID
    document_id: UUID
    chunk_index: int
    chunk_text: str
    metadata: dict[str, Any] | None
    score: float
    clause_id: UUID | None = None
    keywords: list[str] | None = None


@dataclass(frozen=True)
class _RetrievalConfig:
    """Resolved parameters for document-scoped or global vector search."""

    top_k: int
    min_score: float | None
    scoped: bool


class SearchService:
    """Semantic search over document embeddings using cosine similarity.

    Supports two retrieval modes:

    * **Global search** (``document_id is None``): rank across every indexed
      chunk with no metadata filters. Top-k cosine similarity is the primary
      relevance signal; no default similarity cutoff is applied.
    * **Document-scoped search** (``document_id`` provided): restrict the
      query with a ``document_id`` metadata filter, use a lower similarity
      threshold, and fall back to the best available chunks from that document
      when nothing clears the threshold.
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._session = session
        self._embedding_service = embedding_service or EmbeddingService()

    async def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        document_id: UUID | None = None,
        threshold: float | None = None,
    ) -> list[SearchResult]:
        """Embed a query string and run cosine similarity search."""
        query_vector = await self._embedding_service.embed_text(query)
        return await self.search_by_vector(
            query_vector,
            top_k=top_k,
            document_id=document_id,
            threshold=threshold,
        )

    async def search_by_vector(
        self,
        query_vector: list[float],
        *,
        top_k: int | None = None,
        document_id: UUID | None = None,
        threshold: float | None = None,
    ) -> list[SearchResult]:
        """
        Find the most similar chunks using pgvector cosine distance.

        Cosine similarity is computed as ``1 - cosine_distance`` so that
        higher scores indicate closer semantic matches.
        """
        config = await self._resolve_retrieval_config(
            document_id=document_id,
            top_k=top_k,
            threshold=threshold,
        )

        distance = DocumentEmbedding.embedding.cosine_distance(query_vector)
        similarity = (1 - distance).label("similarity")

        stmt = (
            select(DocumentEmbedding, similarity)
            .where(DocumentEmbedding.embedding.isnot(None))
            .order_by(distance)
            .limit(config.top_k)
        )
        if config.scoped:
            stmt = stmt.where(DocumentEmbedding.document_id == document_id)

        result = await self._session.execute(stmt)
        candidates = self._rows_to_results(result.all())

        if config.scoped:
            return apply_similarity_threshold(
                candidates,
                config.min_score or 0.0,
                document_id=document_id,
            )
        return self._finalize_global_results(candidates, config.min_score)

    async def _resolve_retrieval_config(
        self,
        *,
        document_id: UUID | None,
        top_k: int | None,
        threshold: float | None,
    ) -> _RetrievalConfig:
        requested_k = top_k or settings.TOP_K_RETRIEVAL
        k = candidate_pool_size(requested_k)

        if document_id is None:
            return _RetrievalConfig(
                top_k=k,
                min_score=threshold,
                scoped=False,
            )

        k = max(k, candidate_pool_size(settings.SCOPED_TOP_K_RETRIEVAL))
        min_score = min(
            threshold if threshold is not None else settings.SIMILARITY_THRESHOLD,
            settings.SCOPED_SIMILARITY_THRESHOLD,
        )

        chunk_count = await self._session.scalar(
            select(func.count())
            .select_from(DocumentEmbedding)
            .where(
                DocumentEmbedding.document_id == document_id,
                DocumentEmbedding.embedding.isnot(None),
            )
        )
        if chunk_count is not None and int(chunk_count) <= k:
            return _RetrievalConfig(
                top_k=int(chunk_count),
                min_score=0.0,
                scoped=True,
            )

        return _RetrievalConfig(top_k=k, min_score=min_score, scoped=True)

    @staticmethod
    def _rows_to_results(
        rows: list[tuple[DocumentEmbedding, float]],
    ) -> list[SearchResult]:
        return [
            SearchResult(
                id=record.id,
                document_id=record.document_id,
                chunk_index=record.chunk_index,
                chunk_text=record.chunk_text or record.content_preview or "",
                metadata=record.embed_metadata,
                score=float(score),
                clause_id=record.clause_id,
                keywords=record.keywords,
            )
            for record, score in rows
        ]

    @staticmethod
    def _finalize_global_results(
        candidates: list[SearchResult],
        min_score: float | None,
    ) -> list[SearchResult]:
        """
        Global search trusts pgvector top-k ranking.

        An explicit ``threshold`` may post-filter results, but we never return
        an empty set when ranked candidates exist — cross-document matches
        typically score lower than within-document matches.
        """
        if not candidates or min_score is None:
            return candidates

        hits = [candidate for candidate in candidates if candidate.score >= min_score]
        return hits if hits else candidates
