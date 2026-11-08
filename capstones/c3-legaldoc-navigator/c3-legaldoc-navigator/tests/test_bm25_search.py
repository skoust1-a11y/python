"""Unit tests for BM25 keyword search utilities and ranking."""

from uuid import uuid4

from app.rag.bm25_retrieval import (
    BM25ChunkRecord,
    build_bm25_index,
    search_bm25,
    search_exact_phrase,
)
from app.utils.bm25_tokenizer import parse_search_query, tokenize, tokenize_query
from app.utils.snippet_builder import build_snippet


def test_tokenize_lowercases_and_splits_words() -> None:
    assert tokenize("Section 420 IPC indemnification") == [
        "section",
        "420",
        "ipc",
        "indemnification",
    ]


def test_tokenize_query_preserves_numeric_tokens() -> None:
    assert tokenize_query("Section 9") == ["section", "9"]


def test_parse_search_query_detects_quoted_phrase() -> None:
    query, exact = parse_search_query('"force majeure"')
    assert query == "force majeure"
    assert exact is True


def test_parse_search_query_leaves_unquoted_queries_unchanged() -> None:
    query, exact = parse_search_query("contract termination")
    assert query == "contract termination"
    assert exact is False


def test_build_snippet_highlights_matching_terms() -> None:
    text = (
        "The indemnification clause requires the supplier to defend and hold harmless "
        "the buyer against third-party claims arising from the agreement."
    )
    snippet, highlights = build_snippet(text, "indemnification claims")

    assert "indemnification" in snippet.lower()
    assert any(segment.matched for segment in highlights)
    assert "".join(segment.text for segment in highlights) == snippet


def test_bm25_search_ranks_relevant_chunk_higher() -> None:
    chunks = [
        BM25ChunkRecord(
            id=uuid4(),
            document_id=uuid4(),
            document_name="Contract A",
            chunk_index=0,
            chunk_text="Termination may occur with thirty days written notice.",
            clause_id=None,
            page_number=1,
        ),
        BM25ChunkRecord(
            id=uuid4(),
            document_id=uuid4(),
            document_name="Contract B",
            chunk_index=1,
            chunk_text="Indemnification covers third-party claims and defense costs.",
            clause_id=None,
            page_number=2,
        ),
    ]
    index = build_bm25_index(chunks, fingerprint="test")

    ranked = search_bm25(index, "indemnification claims", top_k=2)

    assert ranked
    assert ranked[0][0].chunk_index == 1


def test_exact_phrase_search_requires_literal_match() -> None:
    chunks = [
        BM25ChunkRecord(
            id=uuid4(),
            document_id=uuid4(),
            document_name="Contract A",
            chunk_index=0,
            chunk_text="Written notice must be delivered within thirty days.",
            clause_id=None,
            page_number=1,
        ),
        BM25ChunkRecord(
            id=uuid4(),
            document_id=uuid4(),
            document_name="Contract B",
            chunk_index=1,
            chunk_text="Thirty days written notice is required before termination.",
            clause_id=None,
            page_number=2,
        ),
    ]
    index = build_bm25_index(chunks, fingerprint="test")

    ranked = search_exact_phrase(index, "written notice")

    assert len(ranked) == 2
    assert all(score == 1.0 for _, score in ranked)
