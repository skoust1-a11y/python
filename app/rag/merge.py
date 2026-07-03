"""Merge, deduplicate, and rank-fuse vector and SQL retrieval results."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable

from llama_index.core.schema import NodeWithScore, TextNode

from app.mcp.models import ExternalLegalHit
from app.services.sql_query_executor import SqlRetrievalResult
from app.services.sql_retrieval_service import (
    CaseSummary,
    ClauseSummary,
    ContractSummary,
    MetadataRecord,
)

RRF_K = 60
SQL_SOURCE_SCORE = 0.85
EXTERNAL_SOURCE_SCORE = 0.80


@dataclass(frozen=True)
class MergeStats:
    """Diagnostics from the merge step."""

    vector_input_count: int
    sql_input_count: int
    merged_count: int
    duplicates_removed: int
    external_input_count: int = 0


def merge_retrieval_results(
    vector_nodes: list[NodeWithScore],
    sql_result: SqlRetrievalResult,
    *,
    external_nodes: list[NodeWithScore] | None = None,
    max_results: int | None = None,
) -> tuple[list[NodeWithScore], MergeStats]:
    """
    Convert SQL hits to nodes, fuse with vector hits via RRF, and deduplicate.

    Deduplication keys (in priority order):
    - clause_id
    - document_id + chunk_index
    - source_type + entity_id
    - normalized content prefix hash
    """
    sql_nodes = sql_results_to_nodes(sql_result)
    external_nodes = external_nodes or []
    ranked_lists = [vector_nodes, sql_nodes]
    if external_nodes:
        ranked_lists.append(external_nodes)
    fused = reciprocal_rank_fusion(ranked_lists)

    deduped: list[NodeWithScore] = []
    seen: set[str] = set()
    duplicates_removed = 0

    for node in fused:
        key = _dedup_key(node)
        if key in seen:
            duplicates_removed += 1
            continue
        seen.add(key)
        deduped.append(node)

    if max_results is not None and len(deduped) > max_results:
        deduped = deduped[:max_results]

    stats = MergeStats(
        vector_input_count=len(vector_nodes),
        sql_input_count=len(sql_nodes),
        merged_count=len(deduped),
        duplicates_removed=duplicates_removed,
        external_input_count=len(external_nodes),
    )
    return deduped, stats


def external_results_to_nodes(hits: list[ExternalLegalHit]) -> list[NodeWithScore]:
    """Map external MCP legal database hits to LlamaIndex nodes."""
    nodes: list[NodeWithScore] = []
    for hit in hits:
        nodes.append(_external_hit_to_node(hit))
    return nodes


def _external_hit_to_node(hit: ExternalLegalHit) -> NodeWithScore:
    citation_line = f"Citation: {hit.citation}\n" if hit.citation else ""
    jurisdiction_line = (
        f"Jurisdiction: {hit.jurisdiction}\n" if hit.jurisdiction else ""
    )
    url_line = f"URL: {hit.url}\n" if hit.url else ""
    text = (
        f"{hit.title}\n"
        f"Source: {hit.source_name}\n"
        f"{citation_line}"
        f"{jurisdiction_line}"
        f"{url_line}"
        f"{hit.content}"
    )
    metadata: dict[str, Any] = {
        "chunk_index": -1,
        "source_type": hit.source_type,
        "entity_id": hit.entity_id,
        "entity_type": hit.entity_type,
        "external_source": hit.source_name,
        "score": hit.score,
        **hit.metadata,
    }
    if hit.citation:
        metadata["citation"] = hit.citation
    if hit.jurisdiction:
        metadata["jurisdiction"] = hit.jurisdiction
    if hit.url:
        metadata["url"] = hit.url

    return NodeWithScore(
        node=TextNode(
            id_=f"external-{hit.source_name}-{hit.entity_id}",
            text=text,
            metadata=metadata,
        ),
        score=hit.score,
    )


def reciprocal_rank_fusion(
    ranked_lists: Iterable[list[NodeWithScore]],
    *,
    k: int = RRF_K,
) -> list[NodeWithScore]:
    """Combine multiple ranked lists using reciprocal rank fusion."""
    scores: dict[str, float] = {}
    nodes_by_key: dict[str, NodeWithScore] = {}

    for ranked in ranked_lists:
        for rank, node in enumerate(ranked, start=1):
            key = _dedup_key(node)
            scores[key] = scores.get(key, 0.0) + (1.0 / (k + rank))
            existing = nodes_by_key.get(key)
            if existing is None or (node.score or 0.0) > (existing.score or 0.0):
                nodes_by_key[key] = node

    ordered_keys = sorted(scores.keys(), key=lambda item: scores[item], reverse=True)
    fused: list[NodeWithScore] = []
    for key in ordered_keys:
        node = nodes_by_key[key]
        fused.append(
            NodeWithScore(
                node=node.node,
                score=round(scores[key], 6),
            )
        )
    return fused


def sql_results_to_nodes(sql_result: SqlRetrievalResult) -> list[NodeWithScore]:
    """Map structured SQL retrieval rows to LlamaIndex nodes."""
    nodes: list[NodeWithScore] = []

    for contract in sql_result.contracts:
        nodes.append(_contract_to_node(contract))

    for clause in sql_result.clauses:
        nodes.append(_clause_to_node(clause))

    for case in sql_result.cases:
        nodes.append(_case_to_node(case))

    for record in sql_result.metadata_records:
        nodes.append(_metadata_to_node(record))

    return nodes


def _contract_to_node(contract: ContractSummary) -> NodeWithScore:
    parties = ", ".join(contract.parties_involved or []) or "N/A"
    text = (
        f"Contract: {contract.title or contract.filename}\n"
        f"Contract ID: {contract.contract_id or 'N/A'}\n"
        f"Date: {contract.document_date or 'N/A'}\n"
        f"Subtype: {contract.document_subtype or 'N/A'}\n"
        f"Parties: {parties}\n"
        f"Status: {contract.status}\n"
        f"Summary: {contract.summary or 'N/A'}"
    )
    metadata: dict[str, Any] = {
        "document_id": str(contract.id),
        "chunk_index": -1,
        "source_type": "sql_contract",
        "entity_id": str(contract.id),
        "entity_type": "document",
        "document_name": contract.filename,
        "title": contract.title,
        "score": SQL_SOURCE_SCORE,
    }
    return NodeWithScore(
        node=TextNode(id_=f"sql-contract-{contract.id}", text=text, metadata=metadata),
        score=SQL_SOURCE_SCORE,
    )


def _clause_to_node(clause: ClauseSummary) -> NodeWithScore:
    header = clause.title or clause.clause_type or "Clause"
    number = f" {clause.clause_number}" if clause.clause_number else ""
    text = (
        f"Clause{number}: {header}\n"
        f"Document: {clause.document_title or clause.document_id}\n"
        f"Type: {clause.clause_type or 'N/A'}\n"
        f"Risk: {clause.risk_level or 'N/A'}\n"
        f"{clause.content}"
    )
    metadata: dict[str, Any] = {
        "document_id": str(clause.document_id),
        "chunk_index": -1,
        "clause_id": str(clause.id),
        "source_type": "sql_clause",
        "entity_id": str(clause.id),
        "entity_type": "clause",
        "document_name": clause.document_title,
        "clause_number": clause.clause_number,
        "clause_title": clause.title,
        "page_number": clause.page_number,
        "score": SQL_SOURCE_SCORE,
    }
    return NodeWithScore(
        node=TextNode(id_=f"sql-clause-{clause.id}", text=text, metadata=metadata),
        score=SQL_SOURCE_SCORE,
    )


def _case_to_node(case: CaseSummary) -> NodeWithScore:
    text = (
        f"Case: {case.case_name}\n"
        f"Citation: {case.case_citation}\n"
        f"Docket: {case.docket_number or 'N/A'}\n"
        f"Court: {case.court or 'N/A'} ({case.jurisdiction or 'N/A'})\n"
        f"Filed: {case.filing_date or 'N/A'} | Decided: {case.decision_date or 'N/A'}\n"
        f"Type: {case.case_type or 'N/A'} | Status: {case.case_status or 'N/A'}\n"
        f"Summary: {case.summary or 'N/A'}"
    )
    metadata: dict[str, Any] = {
        "chunk_index": -1,
        "source_type": "sql_case",
        "entity_id": str(case.id),
        "entity_type": "case",
        "case_name": case.case_name,
        "case_citation": case.case_citation,
        "document_name": case.case_name,
        "score": SQL_SOURCE_SCORE,
    }
    return NodeWithScore(
        node=TextNode(id_=f"sql-case-{case.id}", text=text, metadata=metadata),
        score=SQL_SOURCE_SCORE,
    )


def _metadata_to_node(record: MetadataRecord) -> NodeWithScore:
    field_lines = "\n".join(f"{key}: {value}" for key, value in record.fields.items())
    text = f"{record.entity_type.title()} metadata ({record.entity_id}):\n{field_lines}"
    metadata: dict[str, Any] = {
        "chunk_index": -1,
        "source_type": f"sql_{record.entity_type}",
        "entity_id": str(record.entity_id),
        "entity_type": record.entity_type,
        "score": SQL_SOURCE_SCORE,
    }
    if record.entity_type == "clause" and "document_id" in record.fields:
        metadata["document_id"] = str(record.fields["document_id"])
    elif record.entity_type == "document":
        metadata["document_id"] = str(record.entity_id)

    return NodeWithScore(
        node=TextNode(
            id_=f"sql-meta-{record.entity_type}-{record.entity_id}",
            text=text,
            metadata=metadata,
        ),
        score=SQL_SOURCE_SCORE,
    )


def _dedup_key(node: NodeWithScore) -> str:
    metadata = node.node.metadata or {}

    clause_id = metadata.get("clause_id")
    if clause_id:
        return f"clause:{clause_id}"

    document_id = metadata.get("document_id")
    chunk_index = metadata.get("chunk_index")
    if document_id is not None and chunk_index is not None and int(chunk_index) >= 0:
        return f"chunk:{document_id}:{chunk_index}"

    entity_id = metadata.get("entity_id")
    source_type = metadata.get("source_type", "vector")
    if entity_id:
        return f"{source_type}:{entity_id}"

    content = (node.node.get_content() or "").strip().lower()[:200]
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return f"content:{digest}"
