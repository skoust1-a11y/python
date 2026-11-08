"""Reciprocal rank fusion for combining ranked retrieval lists."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any

from llama_index.core.schema import NodeWithScore

RRF_K = 60


def node_dedup_key(node: NodeWithScore) -> str:
    """Stable deduplication key for a retrieved chunk node."""
    metadata = node.node.metadata or {}

    clause_id = metadata.get("clause_id")
    if clause_id:
        return f"clause:{clause_id}"

    document_id = metadata.get("document_id")
    chunk_index = metadata.get("chunk_index")
    if document_id is not None and chunk_index is not None and int(chunk_index) >= 0:
        return f"chunk:{document_id}:{chunk_index}"

    entity_id = metadata.get("entity_id")
    source_type = metadata.get("source_type", "vector")
    if entity_id:
        return f"{source_type}:{entity_id}"

    content = (node.node.get_content() or "").strip().lower()[:200]
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return f"content:{digest}"


def reciprocal_rank_fusion(
    ranked_lists: Iterable[list[NodeWithScore]],
    *,
    k: int = RRF_K,
) -> list[NodeWithScore]:
    """Combine multiple ranked lists using reciprocal rank fusion."""
    scores: dict[str, float] = {}
    nodes_by_key: dict[str, NodeWithScore] = {}

    for ranked in ranked_lists:
        for rank, node in enumerate(ranked, start=1):
            key = node_dedup_key(node)
            scores[key] = scores.get(key, 0.0) + (1.0 / (k + rank))
            existing = nodes_by_key.get(key)
            if existing is None or (node.score or 0.0) > (existing.score or 0.0):
                nodes_by_key[key] = node

    ordered_keys = sorted(scores.keys(), key=lambda item: scores[item], reverse=True)
    fused: list[NodeWithScore] = []
    for key in ordered_keys:
        node = nodes_by_key[key]
        fused.append(
            NodeWithScore(
                node=node.node,
                score=round(scores[key], 6),
            )
        )
    return fused
