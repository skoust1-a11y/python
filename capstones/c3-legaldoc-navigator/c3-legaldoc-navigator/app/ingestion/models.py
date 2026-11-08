"""Structured models for parsed legal documents."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """File-level metadata extracted during parsing."""

    filename: str
    file_type: str
    file_size_bytes: int
    page_count: int | None = None
    author: str | None = None
    title: str | None = None
    subject: str | None = None
    creator: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    is_scanned: bool = False
    jurisdiction: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class TableData(BaseModel):
    """Tabular content extracted from a document."""

    index: int
    page: int | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    caption: str | None = None


class Heading(BaseModel):
    """A heading or sub-heading within the document."""

    level: int
    text: str
    page: int | None = None
    line_number: int | None = None


class Clause(BaseModel):
    """A numbered or lettered clause within the document."""

    identifier: str
    text: str
    parent_heading: str | None = None
    page: int | None = None
    line_number: int | None = None


class Section(BaseModel):
    """A logical section bounded by headings."""

    title: str
    level: int
    content: str
    page_start: int | None = None
    page_end: int | None = None
    headings: list[Heading] = Field(default_factory=list)
    clauses: list[Clause] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    """Complete structured representation of a parsed legal document."""

    title: str | None = None
    metadata: DocumentMetadata
    sections: list[Section] = Field(default_factory=list)
    headings: list[Heading] = Field(default_factory=list)
    clauses: list[Clause] = Field(default_factory=list)
    tables: list[TableData] = Field(default_factory=list)
    raw_text: str = ""

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
