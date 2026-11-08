"""Unit tests for post-retrieval ranking."""

from uuid import uuid4

from llama_index.core.schema import NodeWithScore, TextNode

from app.rag.ranking import (
    deduplicate_chunks,
    extract_query_terms,
    merge_overlapping_chunks,
    rank_retrieval_results,
    rerank_chunks,
)


def _vector_node(
    document_id: str,
    chunk_index: int,
    *,
    text: str = "sample chunk text",
    score: float = 0.9,
    keywords: list[str] | None = None,
) -> NodeWithScore:
    metadata = {
        "document_id": document_id,
        "chunk_index": chunk_index,
        "source_type": "vector",
        "score": score,
        "semantic_score": score,
    }
    if keywords:
        metadata["keywords"] = keywords
    return NodeWithScore(
        node=TextNode(
            id_=f"vec-{document_id}-{chunk_index}",
            text=text,
            metadata=metadata,
        ),
        score=score,
    )


class TestDeduplicateChunks:
    def test_removes_exact_chunk_duplicates(self) -> None:
        doc_id = str(uuid4())
        nodes = [
            _vector_node(doc_id, 1, text="termination clause", score=0.7),
            _vector_node(doc_id, 1, text="termination clause", score=0.9),
        ]

        deduped, removed = deduplicate_chunks(nodes)

        assert len(deduped) == 1
        assert removed == 1
        assert deduped[0].score == 0.9

    def test_removes_near_duplicate_content(self) -> None:
        doc_id = str(uuid4())
        shared = "termination for cause indemnification liability breach damages"
        nodes = [
            _vector_node(doc_id, 1, text=shared, score=0.75),
            _vector_node(doc_id, 2, text=f"{shared} extra", score=0.95),
        ]

        deduped, removed = deduplicate_chunks(nodes)

        assert len(deduped) == 1
        assert removed == 1


class TestMergeOverlappingChunks:
    def test_merges_adjacent_overlapping_chunks(self) -> None:
        doc_id = str(uuid4())
        overlap = "the party shall provide written notice within thirty days"
        left = f"Section 4.2 Termination. {overlap}"
        right = f"{overlap} of the effective termination date."
        nodes = [
            _vector_node(doc_id, 2, text=left, score=0.82),
            _vector_node(doc_id, 3, text=right, score=0.79),
        ]

        merged, overlaps_merged = merge_overlapping_chunks(nodes)

        assert overlaps_merged == 1
        assert len(merged) == 1
        assert overlap in merged[0].node.get_content()
        assert "effective termination date" in merged[0].node.get_content()


class TestRerankChunks:
    def test_boosts_exact_keyword_matches(self) -> None:
        doc_a = str(uuid4())
        doc_b = str(uuid4())
        nodes = [
            _vector_node(
                doc_a,
                0,
                text="general obligations of the parties",
                score=0.80,
            ),
            _vector_node(
                doc_b,
                0,
                text="indemnification clause for third-party claims",
                score=0.78,
                keywords=["indemnification"],
            ),
        ]

        reranked = rerank_chunks(nodes, "indemnification clause")

        assert "indemnification" in reranked[0].node.get_content().lower()

    def test_prefers_chunks_from_same_document(self) -> None:
        dominant_doc = str(uuid4())
        other_doc = str(uuid4())
        nodes = [
            _vector_node(
                dominant_doc,
                0,
                text="master services agreement termination",
                score=0.91,
            ),
            _vector_node(
                other_doc,
                0,
                text="unrelated privacy policy statement",
                score=0.90,
            ),
            _vector_node(
                dominant_doc,
                1,
                text="notice period for termination events",
                score=0.70,
            ),
        ]

        reranked = rerank_chunks(nodes, "termination notice")

        top_doc = reranked[0].node.metadata["document_id"]
        assert top_doc == dominant_doc


class TestRankRetrievalResults:
    def test_returns_at_most_five_chunks(self) -> None:
        nodes = [
            _vector_node(str(uuid4()), index, text=f"chunk {index}", score=0.5 + index * 0.01)
            for index in range(12)
        ]

        ranked, stats = rank_retrieval_results(nodes, "chunk")

        assert len(ranked) == 5
        assert stats.output_count == 5
        assert stats.input_count == 12

    def test_extract_query_terms_skips_stop_words(self) -> None:
        terms = extract_query_terms("What is the termination clause?")

        assert "termination" in terms
        assert "clause" in terms
        assert "what" not in terms
        assert "the" not in terms
