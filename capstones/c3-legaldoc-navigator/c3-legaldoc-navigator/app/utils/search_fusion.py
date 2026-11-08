"""BM25 + semantic search fusion via reciprocal rank fusion."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from llama_index.core.schema import NodeWithScore, TextNode

from app.utils.rank_fusion import reciprocal_rank_fusion


class BM25HitLike(Protocol):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    score: float
    raw_score: float
    chunk_text: str
    clause_id: UUID | None
    page_number: int | None
    clause_number: str | None
    clause_title: str | None


class SemanticHitLike(Protocol):
    id: UUID
    document_id: UUID
    chunk_index: int
    chunk_text: str
    metadata: dict[str, Any] | None
    score: float
    clause_id: UUID | None
    keywords: list[str] | None


def _semantic_hit_to_node(result: SemanticHitLike) -> TextNode:
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


def bm25_hit_to_node(hit: BM25HitLike) -> NodeWithScore:
    """Map a BM25 hit to a LlamaIndex node for rank fusion."""
    metadata: dict[str, Any] = {
        "document_id": str(hit.document_id),
        "document_name": hit.document_name,
        "chunk_index": hit.chunk_index,
        "page_number": hit.page_number,
        "clause_number": hit.clause_number,
        "clause_title": hit.clause_title,
        "source_type": "bm25",
        "bm25_score": hit.score,
        "bm25_raw_score": hit.raw_score,
        "semantic_score": hit.score,
    }
    if hit.clause_id is not None:
        metadata["clause_id"] = str(hit.clause_id)

    return NodeWithScore(
        node=TextNode(
            id_=str(hit.chunk_id),
            text=hit.chunk_text,
            metadata=metadata,
        ),
        score=hit.score,
    )


def semantic_hit_to_node(hit: SemanticHitLike) -> NodeWithScore:
    """Map a vector search hit to a LlamaIndex node for rank fusion."""
    return NodeWithScore(node=_semantic_hit_to_node(hit), score=hit.score)


def fuse_search_rankings(
    bm25_hits: list[BM25HitLike],
    semantic_hits: list[SemanticHitLike],
    *,
    top_k: int,
) -> list[NodeWithScore]:
    """Fuse BM25 and semantic ranked lists with reciprocal rank fusion."""
    ranked_lists: list[list[NodeWithScore]] = []

    if bm25_hits:
        ranked_lists.append([bm25_hit_to_node(hit) for hit in bm25_hits])
    if semantic_hits:
        ranked_lists.append([semantic_hit_to_node(hit) for hit in semantic_hits])

    if not ranked_lists:
        return []
    if len(ranked_lists) == 1:
        return ranked_lists[0][:top_k]

    fused = reciprocal_rank_fusion(ranked_lists)
    return fused[:top_k]


def chunk_ids_from_bm25(hits: list[BM25HitLike]) -> set[UUID]:
    return {hit.chunk_id for hit in hits}


def chunk_ids_from_semantic(hits: list[SemanticHitLike]) -> set[UUID]:
    return {hit.id for hit in hits}


def document_name_from_node(node: TextNode) -> str:
    metadata = node.metadata or {}
    for key in ("document_name", "filename", "title"):
        value = metadata.get(key)
        if value:
            return str(value)
    document_id = metadata.get("document_id")
    if document_id:
        return f"Document {document_id}"
    return "Unknown document"
