"""Similarity threshold filtering with scoped-document fallback."""

from dataclasses import replace
from typing import TypeVar
from uuid import UUID

T = TypeVar("T")


def apply_similarity_threshold(
    candidates: list[T],
    min_score: float,
    *,
    document_id: UUID | None = None,
) -> list[T]:
    """
    Filter search hits by similarity score (document-scoped search only).

    When scoped to a single document and nothing passes the threshold, return
    the best available chunks from that document so the LLM can still answer
    from partial context. Global search uses :meth:`SearchService._finalize_global_results`.
    """
    hits = [candidate for candidate in candidates if float(getattr(candidate, "score")) >= min_score]
    if hits or not candidates or document_id is None:
        return hits

    return [
        replace(
            candidate,
            metadata={
                **(getattr(candidate, "metadata") or {}),
                "threshold_fallback": True,
            },
        )
        for candidate in candidates
    ]
