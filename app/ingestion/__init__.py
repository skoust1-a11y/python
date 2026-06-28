"""Document ingestion pipeline — parsing, chunking, and indexing."""

from app.ingestion.models import (
    Clause,
    DocumentMetadata,
    Heading,
    ParsedDocument,
    Section,
    TableData,
)
from app.ingestion.parser import DocumentParser
from app.ingestion.parsers import (
    DocxParser,
    PDFParser,
    ParserFactory,
    ScannedPDFParser,
    TxtParser,
)
from app.ingestion.chunker import LegalChunk, LegalChunkMetadata, LegalDocumentChunker
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.reader import LegalDocumentReader

__all__ = [
    "LegalChunk",
    "LegalChunkMetadata",
    "LegalDocumentChunker",
    "Clause",
    "DocumentMetadata",
    "DocumentParser",
    "DocxParser",
    "Heading",
    "IngestionPipeline",
    "LegalDocumentReader",
    "ParsedDocument",
    "PDFParser",
    "ParserFactory",
    "ScannedPDFParser",
    "Section",
    "TableData",
    "TxtParser",
]
