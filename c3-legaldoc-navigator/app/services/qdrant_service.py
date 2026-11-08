"""Qdrant vector database client for document chunk embeddings."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
    )


class QdrantVectorService:
    """Store and search document embeddings in Qdrant Cloud."""

    def __init__(self, client: AsyncQdrantClient | None = None) -> None:
        self._client = client or get_qdrant_client()
        self._collection = settings.QDRANT_COLLECTION_NAME

    async def ensure_collection(self) -> None:
        exists = await self._client.collection_exists(self._collection)
        if exists:
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=qm.VectorParams(
                size=settings.VECTOR_DIMENSION,
                distance=qm.Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection: %s", self._collection)

    async def upsert_points(
        self,
        *,
        point_ids: list[UUID],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> None:
        if not point_ids:
            return
        points = [
            qm.PointStruct(
                id=str(point_id),
                vector=vector,
                payload=payload,
            )
            for point_id, vector, payload in zip(point_ids, vectors, payloads, strict=True)
        ]
        await self._client.upsert(collection_name=self._collection, points=points)

    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        document_id: UUID | None = None,
    ) -> list[tuple[UUID, float, dict[str, Any]]]:
        query_filter = None
        if document_id is not None:
            query_filter = qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="document_id",
                        match=qm.MatchValue(value=str(document_id)),
                    )
                ]
            )

        response = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        hits = response.points
        results: list[tuple[UUID, float, dict[str, Any]]] = []
        for hit in hits:
            point_id = hit.id if isinstance(hit.id, UUID) else UUID(str(hit.id))
            payload = dict(hit.payload or {})
            results.append((point_id, float(hit.score), payload))
        return results

    async def delete_by_document_id(self, document_id: UUID) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )

    async def count_by_document_id(self, document_id: UUID) -> int:
        result = await self._client.count(
            collection_name=self._collection,
            count_filter=qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="document_id",
                        match=qm.MatchValue(value=str(document_id)),
                    )
                ]
            ),
            exact=True,
        )
        return int(result.count)
