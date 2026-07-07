"""BM25 retrieval helpers built on LlamaIndex BM25Retriever."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from llama_index.core.schema import TextNode
from llama_index.retrievers.bm25 import BM25Retriever

# Allow single-character tokens (e.g. clause "9") and numeric legal references.
LEGAL_TOKEN_PATTERN = r"(?u)\b\w+\b"
BM25_MAX_TOP_K = 50


@dataclass(frozen=True)
class BM25ChunkRecord:
    id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    chunk_text: str
    clause_id: UUID | None
    page_number: int | None
    clause_number: str | None = None
    clause_title: str | None = None


@dataclass
class BM25CorpusIndex:
    fingerprint: str
    chunks: list[BM25ChunkRecord]
    chunk_by_id: dict[str, BM25ChunkRecord]
    retriever: BM25Retriever | None


def chunks_to_text_nodes(chunks: list[BM25ChunkRecord]) -> list[TextNode]:
    """Convert stored chunk records into LlamaIndex TextNodes for BM25 indexing."""
    nodes: list[TextNode] = []
    for chunk in chunks:
        metadata: dict[str, str | int | None] = {
            "document_id": str(chunk.document_id),
            "document_name": chunk.document_name,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
        }
        if chunk.clause_id is not None:
            metadata["clause_id"] = str(chunk.clause_id)

        nodes.append(
            TextNode(
                text=chunk.chunk_text,
                id_=str(chunk.id),
                metadata=metadata,
            )
        )
    return nodes


def build_bm25_index(
    chunks: list[BM25ChunkRecord],
    *,
    fingerprint: str,
) -> BM25CorpusIndex:
    """Build a cached BM25 corpus index using LlamaIndex BM25Retriever."""
    chunk_by_id = {str(chunk.id): chunk for chunk in chunks}
    nodes = chunks_to_text_nodes(chunks)

    retriever: BM25Retriever | None = None
    if nodes:
        retriever = BM25Retriever.from_defaults(
            nodes=nodes,
            similarity_top_k=min(BM25_MAX_TOP_K, len(nodes)),
            skip_stemming=True,
            token_pattern=LEGAL_TOKEN_PATTERN,
            language="en",
        )

    return BM25CorpusIndex(
        fingerprint=fingerprint,
        chunks=chunks,
        chunk_by_id=chunk_by_id,
        retriever=retriever,
    )


def search_bm25(
    index: BM25CorpusIndex,
    query: str,
    *,
    top_k: int,
) -> list[tuple[BM25ChunkRecord, float]]:
    """Run BM25 retrieval and return chunk records with raw scores."""
    if not index.chunks or not query.strip() or index.retriever is None:
        return []

    limit = min(max(top_k, 1), len(index.chunks))
    index.retriever.similarity_top_k = limit

    ranked: list[tuple[BM25ChunkRecord, float]] = []
    for node_with_score in index.retriever.retrieve(query):
        chunk = index.chunk_by_id.get(node_with_score.node.node_id)
        if chunk is None:
            continue
        score = float(node_with_score.score or 0.0)
        if score > 0:
            ranked.append((chunk, score))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def search_exact_phrase(
    index: BM25CorpusIndex,
    phrase: str,
) -> list[tuple[BM25ChunkRecord, float]]:
    """Return chunks containing the phrase as a literal substring."""
    needle = " ".join(phrase.lower().split())
    if not needle:
        return []

    ranked: list[tuple[BM25ChunkRecord, float]] = []
    for chunk in index.chunks:
        haystack = " ".join(chunk.chunk_text.lower().split())
        if needle in haystack:
            ranked.append((chunk, 1.0))
    return ranked
