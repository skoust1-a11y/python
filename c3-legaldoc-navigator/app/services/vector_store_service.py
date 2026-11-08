"""Vector storage — PostgreSQL metadata with pgvector or Qdrant backends."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.orm import DocumentEmbedding
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantVectorService


@dataclass
class ChunkToStore:
    """A document chunk ready for vector persistence."""

    chunk_text: str
    chunk_index: int
    embedding: list[float] | None = None
    metadata: dict[str, Any] | None = None
    clause_id: UUID | None = None
    token_count: int | None = None
    keywords: list[str] | None = None


class VectorStoreService:
    """Persist and manage document chunk embeddings."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService | None = None,
        qdrant_service: QdrantVectorService | None = None,
    ) -> None:
        self._session = session
        self._embedding_service = embedding_service or EmbeddingService()
        self._qdrant = qdrant_service or QdrantVectorService()
        self._use_qdrant = settings.VECTOR_BACKEND == "qdrant"

    @property
    def embedding_model(self) -> str:
        return self._embedding_service.model_name

    async def store_chunks(
        self,
        document_id: UUID,
        chunks: list[ChunkToStore],
    ) -> list[DocumentEmbedding]:
        """Store pre-computed embeddings with chunk text and metadata."""
        records: list[DocumentEmbedding] = []
        point_ids: list[UUID] = []
        vectors: list[list[float]] = []
        payloads: list[dict[str, Any]] = []

        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(
                    f"Chunk {chunk.chunk_index} is missing an embedding vector"
                )
            record = DocumentEmbedding(
                document_id=document_id,
                clause_id=chunk.clause_id,
                chunk_index=chunk.chunk_index,
                embedding_model=self.embedding_model,
                embedding=None if self._use_qdrant else chunk.embedding,
                chunk_text=chunk.chunk_text,
                content_preview=chunk.chunk_text[:500] if chunk.chunk_text else None,
                embed_metadata=chunk.metadata,
                token_count=chunk.token_count,
                keywords=chunk.keywords,
            )
            self._session.add(record)
            records.append(record)

        await self._session.flush()

        if self._use_qdrant:
            for record, chunk in zip(records, chunks, strict=True):
                record.vector_store_id = str(record.id)
                point_ids.append(record.id)
                vectors.append(chunk.embedding)  # type: ignore[arg-type]
                payloads.append(self._build_qdrant_payload(record, chunk))
            await self._qdrant.upsert_points(
                point_ids=point_ids,
                vectors=vectors,
                payloads=payloads,
            )

        return records

    async def embed_and_store(
        self,
        document_id: UUID,
        chunks: list[ChunkToStore],
    ) -> list[DocumentEmbedding]:
        """Generate embeddings for chunks and persist them."""
        texts = [chunk.chunk_text for chunk in chunks]
        embeddings = await self._embedding_service.embed_texts(texts)

        enriched = [
            ChunkToStore(
                chunk_text=chunk.chunk_text,
                chunk_index=chunk.chunk_index,
                embedding=embeddings[i],
                metadata=chunk.metadata,
                clause_id=chunk.clause_id,
                token_count=chunk.token_count,
                keywords=chunk.keywords,
            )
            for i, chunk in enumerate(chunks)
        ]
        return await self.store_chunks(document_id, enriched)

    async def delete_by_document_id(self, document_id: UUID) -> int:
        """Remove all embeddings for a document."""
        if self._use_qdrant:
            await self._qdrant.delete_by_document_id(document_id)

        result = await self._session.execute(
            delete(DocumentEmbedding).where(DocumentEmbedding.document_id == document_id)
        )
        return result.rowcount or 0

    async def get_by_document_id(self, document_id: UUID) -> list[DocumentEmbedding]:
        """Fetch all stored chunks for a document ordered by chunk index."""
        result = await self._session.execute(
            select(DocumentEmbedding)
            .where(DocumentEmbedding.document_id == document_id)
            .order_by(DocumentEmbedding.chunk_index)
        )
        return list(result.scalars().all())

    async def count_by_document_id(self, document_id: UUID) -> int:
        """Return the number of stored chunks for a document."""
        result = await self._session.execute(
            select(func.count())
            .select_from(DocumentEmbedding)
            .where(DocumentEmbedding.document_id == document_id)
        )
        return int(result.scalar_one())

    @staticmethod
    def _build_qdrant_payload(
        record: DocumentEmbedding,
        chunk: ChunkToStore,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "document_id": str(record.document_id),
            "chunk_index": record.chunk_index,
            "chunk_text": record.chunk_text or "",
            "metadata": chunk.metadata or {},
        }
        if record.clause_id is not None:
            payload["clause_id"] = str(record.clause_id)
        if record.keywords:
            payload["keywords"] = record.keywords
        return payload
