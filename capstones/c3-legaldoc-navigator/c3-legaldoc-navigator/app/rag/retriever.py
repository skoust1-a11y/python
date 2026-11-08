"""LlamaIndex retriever backed by semantic vector search."""

from typing import Any
from uuid import UUID

from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from app.core.config import settings
from app.services.search_service import SearchResult, SearchService


def search_result_to_node(result: SearchResult) -> TextNode:
    """Map a vector search hit to a LlamaIndex TextNode."""
    metadata: dict[str, Any] = {
        "document_id": str(result.document_id),
        "chunk_index": result.chunk_index,
        "score": result.score,
        "semantic_score": result.score,
        "source_type": "vector",
        **(result.metadata or {}),
    }
    if result.clause_id is not None:
        metadata["clause_id"] = str(result.clause_id)
    if result.keywords:
        metadata["keywords"] = result.keywords

    return TextNode(
        id_=str(result.id),
        text=result.chunk_text,
        metadata=metadata,
    )


class LegalDocumentRetriever(BaseRetriever):
    """Top-K semantic retriever over indexed legal document chunks.

    Delegates to :class:`~app.services.search_service.SearchService`, which
    implements LlamaIndex-style conditional metadata filtering:

    * ``document_id`` set → document-scoped search with a metadata filter.
    * ``document_id`` omitted → global search across the full vector index.
    """

    def __init__(
        self,
        search_service: SearchService,
        *,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        document_id: UUID | None = None,
    ) -> None:
        self._search = search_service
        self._top_k = top_k or settings.TOP_K_RETRIEVAL
        self._threshold = similarity_threshold
        self._document_id = document_id
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        raise NotImplementedError(
            "Use async retrieval via LegalDocumentRetriever.aretrieve()"
        )

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        query = query_bundle.query_str
        results = await self._search.search(
            query,
            top_k=self._top_k,
            document_id=self._document_id,
            threshold=self._threshold,
        )
        return [
            NodeWithScore(node=search_result_to_node(hit), score=hit.score)
            for hit in results
        ]
