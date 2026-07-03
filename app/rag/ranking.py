"""Post-retrieval ranking: deduplicate, merge overlaps, rerank, and trim."""

from __future__ import annotations

import re
from dataclasses import dataclass

from llama_index.core.schema import NodeWithScore, TextNode

from app.core.config import settings
from app.rag.merge import _dedup_key

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)


@dataclass(frozen=True)
class RankingStats:
    """Diagnostics from the retrieval ranking stage."""

    input_count: int
    after_dedup_count: int
    after_merge_count: int
    output_count: int
    duplicates_removed: int
    overlaps_merged: int
    dominant_document_id: str | None = None


def rank_retrieval_results(
    nodes: list[NodeWithScore],
    query: str,
    *,
    top_k: int | None = None,
) -> tuple[list[NodeWithScore], RankingStats]:
    """
    Deduplicate, merge overlapping chunks, rerank, and return the top results.

    Ranking combines semantic similarity with keyword-match and same-document
    boosts, then returns at most ``settings.FINAL_TOP_K`` chunks for the LLM.
    """
    input_count = len(nodes)
    deduped, duplicates_removed = deduplicate_chunks(nodes)
    merged, overlaps_merged = merge_overlapping_chunks(deduped)
    reranked = rerank_chunks(merged, query)
    final_k = _resolve_final_top_k(top_k)
    output = reranked[:final_k]

    dominant_document_id = _dominant_document_id(reranked)

    stats = RankingStats(
        input_count=input_count,
        after_dedup_count=len(deduped),
        after_merge_count=len(merged),
        output_count=len(output),
        duplicates_removed=duplicates_removed,
        overlaps_merged=overlaps_merged,
        dominant_document_id=dominant_document_id,
    )
    return output, stats


def deduplicate_chunks(
    nodes: list[NodeWithScore],
) -> tuple[list[NodeWithScore], int]:
    """Remove exact and near-duplicate chunks, keeping the highest-scored hit."""
    deduped: list[NodeWithScore] = []
    seen_keys: set[str] = set()
    duplicates_removed = 0

    for node in sorted(nodes, key=_semantic_score, reverse=True):
        key = _dedup_key(node)
        if key in seen_keys:
            duplicates_removed += 1
            continue

        if _is_near_duplicate(node, deduped):
            duplicates_removed += 1
            continue

        seen_keys.add(key)
        deduped.append(node)

    return deduped, duplicates_removed


def merge_overlapping_chunks(
    nodes: list[NodeWithScore],
) -> tuple[list[NodeWithScore], int]:
    """Merge adjacent, overlapping chunks from the same document."""
    vector_groups: dict[str, list[NodeWithScore]] = {}
    passthrough: list[NodeWithScore] = []

    for node in nodes:
        metadata = node.node.metadata or {}
        document_id = metadata.get("document_id")
        chunk_index = metadata.get("chunk_index")
        if (
            document_id
            and chunk_index is not None
            and int(chunk_index) >= 0
            and metadata.get("source_type", "vector") == "vector"
        ):
            vector_groups.setdefault(str(document_id), []).append(node)
        else:
            passthrough.append(node)

    merged_vector: list[NodeWithScore] = []
    overlaps_merged = 0

    for group in vector_groups.values():
        group.sort(key=lambda item: int((item.node.metadata or {}).get("chunk_index", 0)))
        current: NodeWithScore | None = None
        for node in group:
            if current is None:
                current = node
                continue
            if _should_merge_chunks(current, node):
                current = _merge_chunk_nodes(current, node)
                overlaps_merged += 1
            else:
                merged_vector.append(current)
                current = node
        if current is not None:
            merged_vector.append(current)

    combined = merged_vector + passthrough
    combined.sort(key=lambda item: item.score or 0.0, reverse=True)
    return combined, overlaps_merged


def rerank_chunks(nodes: list[NodeWithScore], query: str) -> list[NodeWithScore]:
    """Rank chunks by semantic similarity with keyword and same-document boosts."""
    if not nodes:
        return []

    query_terms = extract_query_terms(query)
    dominant_doc = _dominant_document_id(nodes)
    secondary_docs = _secondary_document_ids(nodes, dominant_doc)

    scored: list[tuple[float, NodeWithScore]] = []
    for node in nodes:
        semantic = _semantic_score(node)
        keyword_boost = _keyword_boost(node, query_terms)
        document_boost = _same_document_boost(
            node,
            dominant_doc,
            secondary_docs,
        )
        final_score = round(semantic + keyword_boost + document_boost, 6)
        scored.append((final_score, node))

    scored.sort(key=lambda item: item[0], reverse=True)

    reranked: list[NodeWithScore] = []
    for final_score, node in scored:
        metadata = dict(node.node.metadata or {})
        metadata["ranking_score"] = final_score
        metadata["semantic_score"] = _semantic_score(node)
        reranked.append(
            NodeWithScore(
                node=TextNode(
                    id_=node.node.id_,
                    text=node.node.get_content() or "",
                    metadata=metadata,
                ),
                score=final_score,
            )
        )
    return reranked


def extract_query_terms(query: str) -> list[str]:
    """Extract meaningful lowercase terms for exact-match boosting."""
    terms: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(query):
        term = match.group(0).lower()
        if len(term) < 2 or term in _STOP_WORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def candidate_pool_size(requested_top_k: int | None = None) -> int:
    """How many vector hits to fetch before post-retrieval ranking."""
    base_k = requested_top_k or settings.TOP_K_RETRIEVAL
    return max(base_k * settings.RETRIEVAL_CANDIDATE_MULTIPLIER, settings.FINAL_TOP_K)


def _resolve_final_top_k(requested_top_k: int | None) -> int:
    requested = requested_top_k or settings.TOP_K_RETRIEVAL
    return min(requested, settings.FINAL_TOP_K)


def _semantic_score(node: NodeWithScore) -> float:
    metadata = node.node.metadata or {}
    for key in ("semantic_score", "score"):
        value = metadata.get(key)
        if value is not None:
            return float(value)
    return float(node.score or 0.0)


def _dominant_document_id(nodes: list[NodeWithScore]) -> str | None:
    if not nodes:
        return None
    best = max(nodes, key=_semantic_score)
    metadata = best.node.metadata or {}
    document_id = metadata.get("document_id")
    return str(document_id) if document_id else None


def _secondary_document_ids(
    nodes: list[NodeWithScore],
    dominant_doc: str | None,
) -> set[str]:
    if not dominant_doc:
        return set()

    counts: dict[str, int] = {}
    for node in nodes:
        metadata = node.node.metadata or {}
        document_id = metadata.get("document_id")
        if not document_id:
            continue
        doc_key = str(document_id)
        if doc_key == dominant_doc:
            continue
        counts[doc_key] = counts.get(doc_key, 0) + 1

    return {doc_id for doc_id, count in counts.items() if count >= 2}


def _keyword_boost(node: NodeWithScore, query_terms: list[str]) -> float:
    if not query_terms:
        return 0.0

    text = (node.node.get_content() or "").lower()
    metadata = node.node.metadata or {}
    stored_keywords = metadata.get("keywords") or []
    keyword_set = {str(keyword).lower() for keyword in stored_keywords}

    boost = 0.0
    for term in query_terms:
        if term in text:
            boost += settings.KEYWORD_TEXT_MATCH_BOOST
        if term in keyword_set:
            boost += settings.KEYWORD_METADATA_MATCH_BOOST

    return min(boost, settings.KEYWORD_BOOST_CAP)


def _same_document_boost(
    node: NodeWithScore,
    dominant_doc: str | None,
    secondary_docs: set[str],
) -> float:
    metadata = node.node.metadata or {}
    document_id = metadata.get("document_id")
    if not document_id or not dominant_doc:
        return 0.0

    doc_key = str(document_id)
    if doc_key == dominant_doc:
        return settings.SAME_DOC_PRIMARY_BOOST
    if doc_key in secondary_docs:
        return settings.SAME_DOC_SECONDARY_BOOST
    return 0.0


def _is_near_duplicate(candidate: NodeWithScore, kept: list[NodeWithScore]) -> bool:
    candidate_words = _word_set(candidate.node.get_content() or "")
    if not candidate_words:
        return False

    for existing in kept:
        existing_words = _word_set(existing.node.get_content() or "")
        if not existing_words:
            continue
        if _jaccard(candidate_words, existing_words) >= settings.NEAR_DUPLICATE_JACCARD_THRESHOLD:
            return True
    return False


def _should_merge_chunks(left: NodeWithScore, right: NodeWithScore) -> bool:
    left_meta = left.node.metadata or {}
    right_meta = right.node.metadata or {}
    if str(left_meta.get("document_id")) != str(right_meta.get("document_id")):
        return False

    left_index = int(left_meta.get("chunk_index", -1))
    right_index = int(right_meta.get("chunk_index", -1))
    if right_index - left_index != 1:
        return False

    left_text = left.node.get_content() or ""
    right_text = right.node.get_content() or ""
    overlap = _suffix_prefix_overlap(left_text, right_text)
    if overlap >= settings.OVERLAP_MERGE_MIN_CHARS:
        return True

    shorter = min(len(left_text), len(right_text))
    if shorter == 0:
        return False
    return (overlap / shorter) >= settings.OVERLAP_MERGE_MIN_RATIO


def _merge_chunk_nodes(left: NodeWithScore, right: NodeWithScore) -> NodeWithScore:
    left_text = left.node.get_content() or ""
    right_text = right.node.get_content() or ""
    merged_text = _merge_overlapping_text(left_text, right_text)

    left_meta = dict(left.node.metadata or {})
    right_meta = right.node.metadata or {}
    merged_keywords = sorted(
        {
            *(str(keyword) for keyword in (left_meta.get("keywords") or [])),
            *(str(keyword) for keyword in (right_meta.get("keywords") or [])),
        }
    )

    merged_meta = {
        **left_meta,
        "chunk_index": int(left_meta.get("chunk_index", 0)),
        "chunk_index_end": int(right_meta.get("chunk_index", 0)),
        "merged_chunk_count": int(left_meta.get("merged_chunk_count", 1)) + 1,
        "keywords": merged_keywords or left_meta.get("keywords"),
        "semantic_score": max(_semantic_score(left), _semantic_score(right)),
    }

    return NodeWithScore(
        node=TextNode(
            id_=left.node.id_,
            text=merged_text,
            metadata=merged_meta,
        ),
        score=max(left.score or 0.0, right.score or 0.0),
    )


def _merge_overlapping_text(left: str, right: str) -> str:
    overlap = _suffix_prefix_overlap(left, right)
    if overlap >= settings.OVERLAP_MERGE_MIN_CHARS:
        return left + right[overlap:]
    return f"{left}\n{right}"


def _suffix_prefix_overlap(left: str, right: str) -> int:
    max_size = min(len(left), len(right), 1200)
    min_size = settings.OVERLAP_MERGE_MIN_CHARS
    left_lower = left.lower()
    right_lower = right.lower()
    for size in range(max_size, min_size - 1, -1):
        if left_lower[-size:] == right_lower[:size]:
            return size
    return 0


def _word_set(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_RE.finditer(text)}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)
