"""Orchestrates the full document ingestion pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llama_index.core.schema import BaseNode

from app.ingestion.chunker import LegalDocumentChunker, get_legal_chunker
from app.ingestion.models import ParsedDocument
from app.ingestion.parsers.factory import ParserFactory
from app.ingestion.reader import LegalDocumentReader


class IngestionPipeline:
    """Parse → structure → chunk with legal-aware boundaries."""

    def __init__(
        self,
        parser_factory: ParserFactory | None = None,
        chunker: LegalDocumentChunker | None = None,
    ) -> None:
        self._factory = parser_factory or ParserFactory()
        self.reader = LegalDocumentReader(parser_factory=self._factory)
        self.chunker = chunker or get_legal_chunker()

    def parse_document(self, file_path: Path) -> ParsedDocument:
        """Parse a file and return structured content."""
        return self._factory.get_parser(file_path).parse(file_path)

    def parse_to_json(self, file_path: Path, *, indent: int = 2) -> str:
        """Parse a file and return JSON representation."""
        return self.parse_document(file_path).to_json(indent=indent)

    async def ingest(
        self,
        file_path: Path,
        *,
        jurisdiction: str | None = None,
    ) -> tuple[ParsedDocument, list[str], list[BaseNode]]:
        """
        Full ingestion: parse, chunk by legal structure, return nodes.

        Returns:
            Tuple of (parsed document, chunk texts, LlamaIndex nodes).
        """
        parsed = self.parse_document(file_path)
        nodes = self.chunker.chunk_to_nodes(parsed, jurisdiction=jurisdiction)
        chunks = [node.get_content() for node in nodes]
        return parsed, chunks, nodes

    def ingest_sync(
        self,
        file_path: Path,
        *,
        jurisdiction: str | None = None,
    ) -> tuple[ParsedDocument, list[str], list[BaseNode]]:
        """Synchronous variant of ingest for scripts and tests."""
        parsed = self.parse_document(file_path)
        nodes = self.chunker.chunk_to_nodes(parsed, jurisdiction=jurisdiction)
        chunks = [node.get_content() for node in nodes]
        return parsed, chunks, nodes

    def build_node_metadata(self, parsed: ParsedDocument) -> dict[str, Any]:
        """Extract metadata dict suitable for vector store indexing."""
        return {
            "title": parsed.title,
            "filename": parsed.metadata.filename,
            "file_type": parsed.metadata.file_type,
            "jurisdiction": parsed.metadata.jurisdiction,
            "section_count": len(parsed.sections),
            "heading_count": len(parsed.headings),
            "clause_count": len(parsed.clauses),
            "table_count": len(parsed.tables),
            "is_scanned": parsed.metadata.is_scanned,
        }
