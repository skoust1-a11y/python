"""Unit tests for pre-LLM context compression."""

from app.utils.tokens import count_tokens
from app.rag.context_builder import BuiltContext, SourceReference
from app.services.context_compression_service import ContextCompressionService


def _built_context(*blocks: tuple[str, str]) -> BuiltContext:
    rendered_blocks: list[str] = []
    sources: list[SourceReference] = []

    for index, (header, body) in enumerate(blocks, start=1):
        label = f"[Source {index}]"
        rendered_blocks.append(f"{header}\n{body}")
        sources.append(
            SourceReference(
                document_id="doc-1",
                chunk_index=index - 1,
                excerpt=body[:200],
                full_text=body,
                score=0.9 - (index * 0.05),
                citation_label=label,
                metadata={"source_type": "vector"},
            )
        )

    return BuiltContext(
        context_text="\n\n---\n\n".join(rendered_blocks),
        sources=sources,
    )


class TestContextCompressionService:
    def test_removes_duplicate_sentences_across_sources(self) -> None:
        shared = (
            "The party shall provide written notice within thirty days of termination."
        )
        context = _built_context(
            (
                "[Source 1] [vector] (document=doc-1, chunk=0)",
                f"Section 4.2 Termination. {shared}",
            ),
            (
                "[Source 2] [vector] (document=doc-1, chunk=1)",
                f"{shared} Additional indemnification obligations apply.",
            ),
        )
        service = ContextCompressionService(enabled=True, relevance_threshold=0.0)

        result = service.compress(context, "termination notice")

        assert "[Source 1]" in result.context_text
        assert "[Source 2]" in result.context_text
        assert result.context_text.count(shared) == 1
        assert result.stats.duplicate_sentences_removed >= 1
        assert result.stats.compressed_tokens <= result.stats.original_tokens

    def test_merges_overlapping_clauses(self) -> None:
        overlap = "written notice within thirty days of the effective termination date"
        left = f"Section 4.2 Termination. The party shall provide {overlap}"
        right = f"{overlap} and deliver all confidential materials."
        context = _built_context(
            (
                "[Source 1] [vector] (document=doc-1, chunk=0)",
                f"{left}. {right}",
            ),
        )
        service = ContextCompressionService(enabled=True, relevance_threshold=0.0)

        result = service.compress(context, "termination notice")

        assert overlap in result.context_text
        assert result.context_text.count(overlap) == 1
        assert result.stats.overlaps_merged >= 1

    def test_filters_irrelevant_sentences(self) -> None:
        context = _built_context(
            (
                "[Source 1] [vector] (document=doc-1, chunk=0)",
                (
                    "Section 1. Definitions. The agreement governs general corporate matters. "
                    "Section 4.2 Termination requires written notice within thirty days."
                ),
            ),
        )
        service = ContextCompressionService(
            enabled=True,
            relevance_threshold=0.34,
        )

        result = service.compress(context, "termination notice requirements")

        assert "[Source 1]" in result.context_text
        assert "written notice within thirty days" in result.context_text
        assert "general corporate matters" not in result.context_text
        assert result.stats.irrelevant_sentences_removed >= 1

    def test_preserves_citation_headers_when_filtering(self) -> None:
        context = _built_context(
            (
                "[Source 1] [vector] (document=doc-1, chunk=0)",
                "Termination requires written notice within thirty days.",
            ),
            (
                "[Source 2] [vector] (document=doc-1, chunk=1)",
                "Definitions include affiliate and subsidiary entities only.",
            ),
        )
        service = ContextCompressionService(enabled=True, relevance_threshold=0.34)

        result = service.compress(context, "termination notice")

        assert "[Source 1]" in result.context_text
        assert "written notice" in result.context_text

    def test_enforces_token_budget(self) -> None:
        filler = " ".join(
            [
                "Termination notice obligations require written notice and cure periods.",
                "Indemnification caps apply to direct damages only.",
                "Confidentiality survives for five years after expiration.",
            ]
            * 20
        )
        context = _built_context(
            ("[Source 1] [vector] (document=doc-1, chunk=0)", filler),
        )
        service = ContextCompressionService(
            enabled=True,
            max_context_tokens=80,
            relevance_threshold=0.0,
        )

        result = service.compress(context, "termination notice indemnification")

        assert count_tokens(result.context_text) <= 80
        assert result.stats.compressed_tokens < result.stats.original_tokens

    def test_disabled_returns_original_context(self) -> None:
        context = _built_context(
            (
                "[Source 1] [vector] (document=doc-1, chunk=0)",
                "Termination requires written notice within thirty days.",
            ),
        )
        service = ContextCompressionService(enabled=False)

        result = service.compress(context, "termination")

        assert result.context_text == context.context_text
        assert result.stats.enabled is False
        assert result.stats.tokens_saved == 0
