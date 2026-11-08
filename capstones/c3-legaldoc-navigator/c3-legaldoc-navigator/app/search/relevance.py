"""Search-specific relevance filtering (not shared with /query retrieval)."""

from __future__ import annotations

from app.core.config import settings
from app.services.bm25_search_service import BM25SearchHit
from app.services.search_service import SearchResult
from app.utils.bm25_tokenizer import tokenize_query


def search_candidate_pool(final_k: int) -> int:
    """Size the pre-fusion candidate pool for document search."""
    multiplier = max(settings.SEARCH_CANDIDATE_POOL_MULTIPLIER, 1)
    return min(max(final_k * multiplier, final_k), 50)


def query_terms_appear_in_text(query: str, text: str) -> bool:
    """Return True when at least one tokenized query term appears in the text."""
    terms = tokenize_query(query)
    if not terms:
        return False
    lower_text = text.lower()
    return any(term in lower_text for term in terms)


def filter_bm25_hits(query: str, hits: list[BM25SearchHit]) -> list[BM25SearchHit]:
    """Keep BM25 hits that contain query terms and clear the minimum score."""
    filtered: list[BM25SearchHit] = []
    for hit in hits:
        if hit.raw_score < settings.SEARCH_BM25_MIN_RAW_SCORE:
            continue
        if not query_terms_appear_in_text(query, hit.chunk_text):
            continue
        filtered.append(hit)
    return filtered


def filter_semantic_hits(
    hits: list[SearchResult],
    *,
    threshold: float | None = None,
) -> list[SearchResult]:
    """Keep semantic hits that meet the search similarity threshold."""
    min_score = threshold if threshold is not None else settings.SEARCH_SEMANTIC_THRESHOLD
    return [hit for hit in hits if hit.score >= min_score]


def passes_exact_phrase_filter(query: str, text: str) -> bool:
    """Require a literal phrase match (case-insensitive, whitespace-normalized)."""
    needle = " ".join(query.lower().split())
    if not needle:
        return False
    haystack = " ".join(text.lower().split())
    return needle in haystack


def is_search_relevant(
    query: str,
    text: str,
    *,
    exact_phrase: bool,
    bm25_hit: BM25SearchHit | None,
    semantic_hit: SearchResult | None,
) -> bool:
    """
    A fused candidate is relevant when it satisfies the active search mode:

    * exact phrase — literal substring match in chunk text
    * keyword (BM25) — query terms appear in the chunk
    * semantic — similarity score cleared the search threshold
    """
    if exact_phrase:
        return passes_exact_phrase_filter(query, text)

    if bm25_hit is not None and query_terms_appear_in_text(query, text):
        return bm25_hit.raw_score >= settings.SEARCH_BM25_MIN_RAW_SCORE

    if semantic_hit is not None:
        return semantic_hit.score >= settings.SEARCH_SEMANTIC_THRESHOLD

    return False
