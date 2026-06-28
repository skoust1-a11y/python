"""Cosine similarity vector search via pgvector + SQLAlchemy."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.orm import DocumentEmbedding
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


class SearchService:
    """Semantic search over document embeddings using cosine similarity."""

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
        k = top_k or settings.TOP_K_RETRIEVAL
        min_score = threshold if threshold is not None else settings.SIMILARITY_THRESHOLD

        distance = DocumentEmbedding.embedding.cosine_distance(query_vector)
        similarity = (1 - distance).label("similarity")

        stmt = (
            select(DocumentEmbedding, similarity)
            .where(DocumentEmbedding.embedding.isnot(None))
            .order_by(distance)
            .limit(k)
        )
        if document_id is not None:
            stmt = stmt.where(DocumentEmbedding.document_id == document_id)

        result = await self._session.execute(stmt)
        hits: list[SearchResult] = []
        for record, score in result.all():
            similarity_score = float(score)
            if similarity_score < min_score:
                continue
            hits.append(
                SearchResult(
                    id=record.id,
                    document_id=record.document_id,
                    chunk_index=record.chunk_index,
                    chunk_text=record.chunk_text or record.content_preview or "",
                    metadata=record.embed_metadata,
                    score=similarity_score,
                    clause_id=record.clause_id,
                )
            )
        return hits
