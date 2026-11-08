"""Build LLM context and source citations from retrieved nodes."""

from dataclasses import dataclass

from llama_index.core.schema import NodeWithScore


@dataclass(frozen=True)
class SourceReference:
    """A cited source chunk returned alongside the generated answer."""

    document_id: str
    chunk_index: int
    excerpt: str
    full_text: str
    score: float
    citation_label: str
    metadata: dict


def internal_source_to_dict(source: SourceReference) -> dict:
    """Serialize a source reference for internal pipeline use (includes chunk text)."""
    return {
        "document_id": source.document_id,
        "chunk_index": source.chunk_index,
        "excerpt": source.excerpt,
        "full_text": source.full_text,
        "score": source.score,
        "citation_label": source.citation_label,
        "source_type": source.metadata.get("source_type", "vector"),
        "entity_id": source.metadata.get("entity_id"),
        "entity_type": source.metadata.get("entity_type"),
        "metadata": source.metadata,
    }


@dataclass(frozen=True)
class BuiltContext:
    """Structured retrieval context ready for prompt injection."""

    context_text: str
    sources: list[SourceReference]


class LegalContextBuilder:
    """Format retrieved nodes into numbered, citable context blocks."""

    def __init__(self, *, excerpt_max_chars: int = 1500) -> None:
        self._excerpt_max_chars = excerpt_max_chars

    def build(self, nodes: list[NodeWithScore]) -> BuiltContext:
        if not nodes:
            return BuiltContext(context_text="", sources=[])

        blocks: list[str] = []
        sources: list[SourceReference] = []

        for index, node_with_score in enumerate(nodes, start=1):
            node = node_with_score.node
            metadata = node.metadata or {}
            label = f"[Source {index}]"
            document_id = str(metadata.get("document_id", "unknown"))
            chunk_index = int(metadata.get("chunk_index", index - 1))
            semantic_score = metadata.get("semantic_score")
            score = float(
                semantic_score
                if semantic_score is not None
                else (node_with_score.score or metadata.get("score", 0.0))
            )
            excerpt = (node.get_content() or "")[: self._excerpt_max_chars]
            full_text = node.get_content() or ""
            location_parts = _format_location_metadata(metadata)

            blocks.append(
                f"{label} [{metadata.get('source_type', 'vector')}] "
                f"(document={_document_display_name(metadata, document_id)}, "
                f"{location_parts}, chunk={chunk_index})\n{full_text}"
            )
            sources.append(
                SourceReference(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    excerpt=excerpt,
                    full_text=full_text,
                    score=score,
                    citation_label=label,
                    metadata={
                        key: value
                        for key, value in metadata.items()
                        if key not in {"document_id", "chunk_index", "score"}
                    },
                )
            )

        return BuiltContext(
            context_text="\n\n---\n\n".join(blocks),
            sources=sources,
        )


def _document_display_name(metadata: dict, document_id: str) -> str:
    for key in ("document_name", "filename", "title", "source_file"):
        value = metadata.get(key)
        if value:
            return str(value)
    return document_id


def _format_location_metadata(metadata: dict) -> str:
    parts: list[str] = []
    if metadata.get("clause_number"):
        parts.append(f"clause={metadata['clause_number']}")
    if metadata.get("clause_title"):
        parts.append(f"section={metadata['clause_title']}")
    if metadata.get("page_number") is not None:
        parts.append(f"page={metadata['page_number']}")
    if not parts:
        return "location=not specified"
    return ", ".join(parts)
