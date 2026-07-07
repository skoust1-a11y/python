"""Document search retrieval pipeline — BM25 + semantic fusion without /query deps."""

from __future__ import annotations

import asyncio
from uuid import UUID

from llama_index.core.schema import NodeWithScore

from app.core.config import settings
from app.search.relevance import (
    filter_bm25_hits,
    filter_semantic_hits,
    is_search_relevant,
    search_candidate_pool,
)
from app.search.types import SearchHit
from app.services.bm25_search_service import BM25SearchHit, BM25SearchResult, BM25SearchService
from app.services.search_service import SearchResult, SearchService
from app.utils.bm25_tokenizer import parse_search_query, tokenize_query
from app.utils.search_fusion import (
    chunk_ids_from_bm25,
    chunk_ids_from_semantic,
    document_name_from_node,
    fuse_search_rankings,
)
from app.utils.snippet_builder import build_snippet


async def retrieve_search_hits(
    query: str,
    *,
    bm25_service: BM25SearchService,
    semantic_service: SearchService,
    document_id: UUID | None,
    top_k: int,
    exact_phrase: bool,
) -> tuple[list[SearchHit], int, int, int]:
    """
    Run the independent search pipeline and return ranked, filtered hits.

    Returns ``(hits, total_candidates, bm25_count, semantic_count)``.
    """
    parsed_query, auto_exact_phrase = parse_search_query(query)
    use_exact_phrase = exact_phrase or auto_exact_phrase
    search_text = parsed_query

    pool_k = search_candidate_pool(top_k)
    use_semantic = not use_exact_phrase
    use_bm25 = bool(tokenize_query(search_text)) or use_exact_phrase

    bm25_task = (
        bm25_service.search(
            search_text,
            document_id=document_id,
            top_k=pool_k,
            exact_phrase=use_exact_phrase,
        )
        if use_bm25
        else _empty_bm25_result(search_text)
    )
    semantic_task = (
        semantic_service.search(
            search_text,
            top_k=pool_k,
            document_id=document_id,
            threshold=settings.SEARCH_SEMANTIC_THRESHOLD,
        )
        if use_semantic
        else _empty_semantic_result()
    )

    bm25_result, semantic_hits = await asyncio.gather(bm25_task, semantic_task)

    if use_exact_phrase:
        bm25_hits = bm25_result.hits
        semantic_hits = []
    else:
        bm25_hits = filter_bm25_hits(search_text, bm25_result.hits)
        semantic_hits = filter_semantic_hits(semantic_hits)

    fused_nodes = fuse_search_rankings(bm25_hits, semantic_hits, top_k=pool_k)

    bm25_ids = chunk_ids_from_bm25(bm25_hits)
    semantic_ids = chunk_ids_from_semantic(semantic_hits)
    bm25_by_id = {hit.chunk_id: hit for hit in bm25_hits}
    semantic_by_id = {hit.id: hit for hit in semantic_hits}

    hits: list[SearchHit] = []
    for node_with_score in fused_nodes:
        if len(hits) >= top_k:
            break

        node = node_with_score.node
        chunk_text = node.get_content() or ""
        chunk_id = UUID(str(node.id_))

        bm25_hit = bm25_by_id.get(chunk_id)
        semantic_hit = semantic_by_id.get(chunk_id)

        if not is_search_relevant(
            search_text,
            chunk_text,
            exact_phrase=use_exact_phrase,
            bm25_hit=bm25_hit,
            semantic_hit=semantic_hit,
        ):
            continue

        match_sources: list[str] = []
        if chunk_id in bm25_ids:
            match_sources.append("bm25")
        if chunk_id in semantic_ids:
            match_sources.append("semantic")

        document_name = document_name_from_node(node)
        if bm25_hit is not None:
            document_name = bm25_hit.document_name

        metadata = node.metadata or {}
        snippet, highlights = _build_hit_snippet(
            chunk_text,
            search_text,
            bm25_hit=bm25_hit,
            use_exact_phrase=use_exact_phrase,
        )

        score, raw_score = _resolve_scores(
            node_with_score=node_with_score,
            bm25_hit=bm25_hit,
            semantic_hit=semantic_hit,
        )

        hits.append(
            SearchHit(
                chunk_id=chunk_id,
                document_id=_resolve_document_id(metadata, bm25_hit, semantic_hit),
                document_name=document_name,
                chunk_index=_resolve_chunk_index(metadata, bm25_hit, semantic_hit),
                score=score,
                raw_score=raw_score,
                snippet=snippet,
                highlights=highlights,
                match_sources=match_sources or ["semantic"],
                clause_id=_resolve_clause_id(metadata, bm25_hit, semantic_hit),
                page_number=_resolve_page_number(metadata, bm25_hit),
                clause_number=_resolve_clause_number(metadata, bm25_hit),
                clause_title=_resolve_clause_title(metadata, bm25_hit),
            )
        )

    return hits, bm25_result.total_candidates, len(bm25_hits), len(semantic_hits)


def _build_hit_snippet(
    chunk_text: str,
    query: str,
    *,
    bm25_hit: BM25SearchHit | None,
    use_exact_phrase: bool,
) -> tuple[str, list]:
    if bm25_hit is not None and bm25_hit.snippet and not use_exact_phrase:
        return bm25_hit.snippet, list(bm25_hit.highlights)
    return build_snippet(
        chunk_text,
        query,
        max_chars=settings.BM25_SNIPPET_MAX_CHARS,
    )


def _resolve_scores(
    *,
    node_with_score: NodeWithScore,
    bm25_hit: BM25SearchHit | None,
    semantic_hit: SearchResult | None,
) -> tuple[float, float]:
    metadata = node_with_score.node.metadata or {}
    semantic_score = metadata.get("semantic_score")
    if semantic_hit is not None:
        semantic_score = semantic_hit.score
    if bm25_hit is not None and semantic_hit is None:
        semantic_score = bm25_hit.score

    raw = float(
        semantic_score
        if semantic_score is not None
        else (node_with_score.score or metadata.get("bm25_score") or 0.0)
    )
    normalized = round(min(max(raw, 0.0), 1.0), 4)
    return normalized, round(raw, 6)


def _resolve_document_id(
    metadata: dict,
    bm25_hit: BM25SearchHit | None,
    semantic_hit: SearchResult | None,
) -> UUID:
    document_id_raw = metadata.get("document_id")
    if document_id_raw:
        return UUID(str(document_id_raw))
    if bm25_hit is not None:
        return bm25_hit.document_id
    if semantic_hit is not None:
        return semantic_hit.document_id
    raise ValueError("Search hit is missing document_id")


def _resolve_chunk_index(
    metadata: dict,
    bm25_hit: BM25SearchHit | None,
    semantic_hit: SearchResult | None,
) -> int:
    if "chunk_index" in metadata:
        return int(metadata["chunk_index"])
    if bm25_hit is not None:
        return bm25_hit.chunk_index
    if semantic_hit is not None:
        return semantic_hit.chunk_index
    return 0


def _resolve_clause_id(
    metadata: dict,
    bm25_hit: BM25SearchHit | None,
    semantic_hit: SearchResult | None,
) -> UUID | None:
    clause_id_raw = metadata.get("clause_id")
    if clause_id_raw:
        return UUID(str(clause_id_raw))
    if bm25_hit is not None and bm25_hit.clause_id is not None:
        return bm25_hit.clause_id
    if semantic_hit is not None:
        return semantic_hit.clause_id
    return None


def _resolve_page_number(metadata: dict, bm25_hit: BM25SearchHit | None) -> int | None:
    page = metadata.get("page_number")
    if page is not None:
        return int(page)
    if bm25_hit is not None:
        return bm25_hit.page_number
    return None


def _resolve_clause_number(metadata: dict, bm25_hit: BM25SearchHit | None) -> str | None:
    value = metadata.get("clause_number")
    if value:
        return str(value)
    if bm25_hit is not None and bm25_hit.clause_number:
        return bm25_hit.clause_number
    return None


def _resolve_clause_title(metadata: dict, bm25_hit: BM25SearchHit | None) -> str | None:
    value = metadata.get("clause_title")
    if value:
        return str(value)
    if bm25_hit is not None and bm25_hit.clause_title:
        return bm25_hit.clause_title
    return None


async def _empty_bm25_result(query: str) -> BM25SearchResult:
    return BM25SearchResult(query=query, hits=[], total_candidates=0, latency_ms=0.0)


async def _empty_semantic_result() -> list[SearchResult]:
    return []
