"""Document-level citation formatting for API responses.

Aggregates chunk-level retrieval records into deduplicated document citations
with optional pinpoint metadata (clause number, clause title, page number).
Raw chunk text is never included in the public output.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.schemas import CitationLocation, SourceCitation


def format_document_citations(sources: list[dict[str, Any]]) -> list[SourceCitation]:
    """Collapse chunk-level sources into sorted document-level citations."""
    if not sources:
        return []

    groups: dict[str, dict[str, Any]] = {}

    for source in sources:
        key = _group_key(source)
        metadata = _source_metadata(source)
        score = float(source.get("score", metadata.get("score", 0.0)))
        source_type = str(source.get("source_type") or metadata.get("source_type") or "vector")
        label = source.get("citation_label")
        location = _extract_location(metadata)

        bucket = groups.get(key)
        if bucket is None:
            bucket = {
                "document_id": _parse_document_id(source, metadata),
                "document_name": _resolve_document_name(source, metadata),
                "entity_id": _parse_entity_id(source, metadata),
                "entity_type": source.get("entity_type") or metadata.get("entity_type"),
                "score": score,
                "source_types": {source_type},
                "citation_labels": [],
                "locations": {},
            }
            groups[key] = bucket
        else:
            bucket["score"] = max(bucket["score"], score)
            bucket["source_types"].add(source_type)
            if not bucket["document_name"]:
                bucket["document_name"] = _resolve_document_name(source, metadata)

        if label and label not in bucket["citation_labels"]:
            bucket["citation_labels"].append(label)

        if location is not None:
            location_key = (
                location.clause_number or "",
                location.clause_title or "",
                location.page_number,
            )
            bucket["locations"][location_key] = location

    citations = [
        SourceCitation(
            document_id=bucket["document_id"],
            document_name=bucket["document_name"],
            score=bucket["score"],
            source_types=sorted(bucket["source_types"]),
            locations=_sort_locations(list(bucket["locations"].values())),
            citation_labels=bucket["citation_labels"],
            entity_id=bucket["entity_id"],
            entity_type=bucket["entity_type"],
        )
        for bucket in groups.values()
    ]

    citations.sort(key=lambda item: (-item.score, item.document_name.lower()))
    return citations


def format_citation_line(citation: SourceCitation) -> str:
    """Render a single document citation as a human-readable line."""
    return citation.document_name


def format_location_line(location: CitationLocation) -> str | None:
    """Render optional pinpoint metadata when present."""
    parts: list[str] = []
    if location.clause_number:
        parts.append(f"Clause {location.clause_number}")
    if location.clause_title:
        parts.append(location.clause_title)
    if location.page_number is not None:
        parts.append(f"Page {location.page_number}")
    if not parts:
        return None
    return " · ".join(parts)


def extract_location_from_metadata(metadata: dict[str, Any] | None) -> CitationLocation | None:
    """Extract pinpoint metadata from chunk embed_metadata."""
    if not metadata:
        return None
    return _extract_location(metadata)


def _source_metadata(source: dict[str, Any]) -> dict[str, Any]:
    metadata = source.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _group_key(source: dict[str, Any]) -> str:
    metadata = _source_metadata(source)
    document_id = source.get("document_id") or metadata.get("document_id")
    if document_id:
        return f"doc:{document_id}"

    entity_type = source.get("entity_type") or metadata.get("entity_type")
    entity_id = source.get("entity_id") or metadata.get("entity_id")
    if entity_type and entity_id:
        return f"{entity_type}:{entity_id}"

    external = metadata.get("external_source") or metadata.get("citation")
    if external:
        return f"external:{external}"

    name = _resolve_document_name(source, metadata)
    return f"name:{name}"


def _parse_document_id(
    source: dict[str, Any],
    metadata: dict[str, Any],
) -> UUID | None:
    return _parse_uuid(source.get("document_id") or metadata.get("document_id"))


def _parse_entity_id(
    source: dict[str, Any],
    metadata: dict[str, Any],
) -> UUID | None:
    return _parse_uuid(source.get("entity_id") or metadata.get("entity_id"))


def _parse_uuid(value: Any) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _resolve_document_name(source: dict[str, Any], metadata: dict[str, Any]) -> str:
    for key in (
        "filename",
        "document_name",
        "document_title",
        "title",
        "case_name",
        "case_citation",
        "external_source",
    ):
        candidate = _str_or_none(metadata.get(key))
        if candidate:
            return candidate

    entity_type = source.get("entity_type") or metadata.get("entity_type")
    if entity_type == "case":
        for key in ("case_name", "case_citation"):
            candidate = _str_or_none(source.get(key))
            if candidate:
                return candidate

    document_id = source.get("document_id") or metadata.get("document_id")
    if document_id:
        return f"Document {document_id}"

    return "Unknown source"


def _resolve_clause_title(metadata: dict[str, Any]) -> str | None:
    for key in ("clause_title", "title", "heading", "section"):
        candidate = _str_or_none(metadata.get(key))
        if candidate:
            return candidate
    return None


def _extract_location(metadata: dict[str, Any]) -> CitationLocation | None:
    clause_number = _str_or_none(metadata.get("clause_number"))
    clause_title = _resolve_clause_title(metadata)
    page_number = _int_or_none(metadata.get("page_number"))

    if not any([clause_number, clause_title, page_number is not None]):
        return None

    return CitationLocation(
        clause_number=clause_number,
        clause_title=clause_title,
        page_number=page_number,
    )


def _sort_locations(locations: list[CitationLocation]) -> list[CitationLocation]:
    def sort_key(location: CitationLocation) -> tuple[Any, ...]:
        page = location.page_number if location.page_number is not None else 10**9
        clause = location.clause_number or ""
        return (page, _clause_sort_key(clause), location.clause_title or "")

    return sorted(locations, key=sort_key)


def _clause_sort_key(clause_number: str) -> tuple[Any, ...]:
    """Sort clause numbers naturally (e.g. 4.2 before 4.10)."""
    parts: list[Any] = []
    for segment in clause_number.replace(" ", "").split("."):
        if segment.isdigit():
            parts.append((0, int(segment)))
        else:
            parts.append((1, segment.lower()))
    return tuple(parts) if parts else (2, clause_number.lower())


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
