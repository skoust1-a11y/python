"""Tests for shared chunk text formatting utilities."""

from app.utils.chunk_text_formatter import clean_chunk_text


def test_clean_chunk_text_preserves_paragraph_breaks() -> None:
    text = "First paragraph line.\n\nSecond paragraph line."
    assert clean_chunk_text(text) == "First paragraph line.\n\nSecond paragraph line."


def test_clean_chunk_text_collapses_internal_whitespace() -> None:
    text = "Too   many    spaces\n\nAnd\t\ttabs   here"
    assert clean_chunk_text(text) == "Too many spaces\n\nAnd tabs here"


def test_clean_chunk_text_trims_blank_lines() -> None:
    text = "\n\n  Leading blank.\n\n\n\nTrailing blank.  \n\n"
    assert clean_chunk_text(text) == "Leading blank.\n\nTrailing blank."


def test_clean_chunk_text_returns_empty_for_blank_input() -> None:
    assert clean_chunk_text("") == ""
    assert clean_chunk_text("   \n\n  ") == ""


def test_build_snippet_preserves_paragraph_breaks_in_excerpt() -> None:
    from app.utils.snippet_builder import build_snippet

    text = (
        "Unrelated preamble about general terms.\n\n"
        "The indemnification clause requires defense against third-party claims."
    )
    snippet, highlights = build_snippet(text, "indemnification")

    assert "\n\n" in snippet or "indemnification" in snippet.lower()
    assert any(segment.matched for segment in highlights)
    assert "".join(segment.text for segment in highlights) == snippet
