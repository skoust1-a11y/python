"""Tests for document-level citation formatting."""

from uuid import uuid4

from app.utils.citation_formatter import (
    format_document_citations,
    format_location_line,
)


DOC_A = str(uuid4())
DOC_B = str(uuid4())


def _vector_source(
    *,
    document_id: str,
    document_name: str,
    chunk_index: int,
    score: float,
    label: str,
    clause_number: str | None = None,
    heading: str | None = None,
    page_number: int | None = None,
) -> dict:
    return {
        "document_id": document_id,
        "chunk_index": chunk_index,
        "excerpt": "Sensitive chunk text that must not leak.",
        "full_text": "Full chunk body.",
        "score": score,
        "citation_label": label,
        "source_type": "vector",
        "metadata": {
            "document_name": document_name,
            "clause_number": clause_number,
            "heading": heading,
            "page_number": page_number,
        },
    }


class TestFormatDocumentCitations:
    def test_collapses_chunks_to_document_level(self) -> None:
        sources = [
            _vector_source(
                document_id=DOC_A,
                document_name="Employment Contract",
                chunk_index=0,
                score=0.91,
                label="[Source 1]",
                clause_number="4.2",
                heading="Termination",
                page_number=12,
            ),
            _vector_source(
                document_id=DOC_A,
                document_name="Employment Contract",
                chunk_index=3,
                score=0.88,
                label="[Source 2]",
                clause_number="4.2",
                heading="Termination",
                page_number=12,
            ),
            _vector_source(
                document_id=DOC_B,
                document_name="NDA_2024.pdf",
                chunk_index=1,
                score=0.79,
                label="[Source 3]",
            ),
        ]
        for source in sources[:2]:
            source["metadata"]["filename"] = "Employment_Contract.pdf"
        sources[2]["metadata"]["filename"] = "NDA_2024.pdf"

        citations = format_document_citations(sources)

        assert len(citations) == 2
        assert citations[0].document_name == "Employment_Contract.pdf"
        assert citations[0].score == 0.91
        assert citations[0].citation_labels == ["[Source 1]", "[Source 2]"]
        assert len(citations[0].locations) == 1
        assert citations[0].locations[0].clause_number == "4.2"
        assert citations[0].locations[0].clause_title == "Termination"
        assert citations[0].locations[0].page_number == 12

        assert citations[1].document_name == "NDA_2024.pdf"
        assert citations[1].locations == []

    def test_collects_multiple_locations_per_document(self) -> None:
        sources = [
            _vector_source(
                document_id=DOC_A,
                document_name="Service_Agreement.pdf",
                chunk_index=0,
                score=0.85,
                label="[Source 1]",
                clause_number="7.1",
                heading="Confidentiality",
                page_number=18,
            ),
            _vector_source(
                document_id=DOC_A,
                document_name="Service_Agreement.pdf",
                chunk_index=2,
                score=0.82,
                label="[Source 2]",
                clause_number="4.2",
                heading="Payment Terms",
                page_number=9,
            ),
        ]

        citations = format_document_citations(sources)

        assert len(citations) == 1
        assert len(citations[0].locations) == 2
        assert citations[0].locations[0].page_number == 9
        assert citations[0].locations[1].page_number == 18

    def test_sql_case_without_document_id(self) -> None:
        case_id = str(uuid4())
        sources = [
            {
                "chunk_index": -1,
                "score": 0.85,
                "citation_label": "[Source 1]",
                "source_type": "sql_case",
                "entity_id": case_id,
                "entity_type": "case",
                "metadata": {
                    "case_name": "Smith v. Jones",
                    "case_citation": "123 F.3d 456",
                    "document_name": "Smith v. Jones",
                },
            }
        ]

        citations = format_document_citations(sources)

        assert len(citations) == 1
        assert citations[0].document_name == "Smith v. Jones"
        assert citations[0].entity_type == "case"

    def test_does_not_include_chunk_text(self) -> None:
        citations = format_document_citations(
            [
                _vector_source(
                    document_id=DOC_A,
                    document_name="Employment_Contract.pdf",
                    chunk_index=0,
                    score=0.9,
                    label="[Source 1]",
                )
            ]
        )
        payload = citations[0].model_dump()
        assert "excerpt" not in payload
        assert "full_text" not in payload
        assert "chunk_index" not in payload

    def test_format_location_line(self) -> None:
        from app.models.schemas import CitationLocation

        line = format_location_line(
            CitationLocation(
                clause_number="4.2",
                clause_title="Termination",
                page_number=12,
            )
        )
        assert line == "Clause 4.2 · Termination · Page 12"
