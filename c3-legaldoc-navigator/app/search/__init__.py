"""Independent document search pipeline (separate from /query RAG retrieval)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.search.service import DocumentSearchService

__all__ = ["DocumentSearchService"]


def __getattr__(name: str):
    if name == "DocumentSearchService":
        from app.search.service import DocumentSearchService

        return DocumentSearchService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

