"""Structured SQL retrieval for legal entities via SQLAlchemy ORM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm import Case, Clause, Document, Statute

MetadataEntityType = Literal["document", "case", "clause", "statute"]


@dataclass
class ContractSummary:
    """A contract document matched by signing date."""

    id: UUID
    title: str | None
    filename: str
    contract_id: str | None
    document_date: date | None
    document_subtype: str | None
    parties_involved: list[str] | None
    status: str
    summary: str | None = None


@dataclass
class ClauseSummary:
    """A clause matched by topic or keyword."""

    id: UUID
    document_id: UUID
    clause_number: str | None
    title: str | None
    content: str
    clause_type: str | None
    page_number: int | None
    risk_level: str | None
    keywords: list[str] | None = None
    document_title: str | None = None


@dataclass
class CaseSummary:
    """A case matched by docket or citation number."""

    id: UUID
    case_citation: str
    case_name: str
    docket_number: str | None
    court: str | None
    jurisdiction: str | None
    filing_date: date | None
    decision_date: date | None
    case_type: str | None
    case_status: str | None
    summary: str | None = None


@dataclass
class MetadataRecord:
    """Normalized metadata payload for any supported entity."""

    entity_type: MetadataEntityType
    entity_id: UUID
    fields: dict[str, Any] = field(default_factory=dict)
    custom_metadata: dict[str, Any] | None = None


class SqlRetrievalService:
    """Reusable ORM queries for structured legal document retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_contracts_signed_in_year(
        self,
        year: int,
        *,
        limit: int = 100,
    ) -> list[ContractSummary]:
        """
        Find contract documents signed within a calendar year.

        Matches rows where ``document_subtype`` indicates a contract and
        ``document_date`` falls in ``year``.
        """
        stmt = (
            select(Document)
            .where(
                Document.document_date.isnot(None),
                extract("year", Document.document_date) == year,
                or_(
                    Document.document_subtype.ilike("%contract%"),
                    Document.filename.ilike("%contract%"),
                    Document.title.ilike("%contract%"),
                    Document.title.ilike("%agreement%"),
                ),
            )
            .order_by(Document.document_date.desc(), Document.title)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_contract_summary(doc) for doc in result.scalars().all()]

    async def find_clauses_related_to(
        self,
        topic: str,
        *,
        document_id: UUID | None = None,
        limit: int = 50,
    ) -> list[ClauseSummary]:
        """
        Find clauses related to a topic (e.g. termination, indemnity).

        Searches ``clause_type``, ``title``, ``content``, and ``keywords``.
        """
        pattern = f"%{topic.strip()}%"
        topic_keyword = topic.strip().lower()

        conditions = [
            Clause.clause_type.ilike(pattern),
            Clause.title.ilike(pattern),
            Clause.content.ilike(pattern),
        ]
        if topic_keyword:
            conditions.append(Clause.keywords.overlap([topic_keyword]))

        stmt = (
            select(Clause)
            .options(selectinload(Clause.document))
            .where(or_(*conditions))
            .order_by(Clause.document_id, Clause.position_order)
            .limit(limit)
        )
        if document_id is not None:
            stmt = stmt.where(Clause.document_id == document_id)

        result = await self._session.execute(stmt)
        return [self._to_clause_summary(clause) for clause in result.scalars().unique().all()]

    async def find_case_by_number(
        self,
        case_number: str,
        *,
        limit: int = 20,
    ) -> list[CaseSummary]:
        """
        Find cases by docket number, citation, or case name fragment.

        Example: ``find_case_by_number("XYZ-2024-001")``.
        """
        needle = case_number.strip()
        if not needle:
            return []

        pattern = f"%{needle}%"
        stmt = (
            select(Case)
            .where(
                or_(
                    Case.docket_number.ilike(pattern),
                    Case.case_citation.ilike(pattern),
                    Case.case_name.ilike(pattern),
                )
            )
            .order_by(Case.decision_date.desc().nullslast(), Case.case_name)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_case_summary(case) for case in result.scalars().all()]

    async def retrieve_metadata(
        self,
        entity_type: MetadataEntityType,
        entity_id: UUID,
    ) -> MetadataRecord | None:
        """Retrieve structured metadata for a document, case, clause, or statute."""
        if entity_type == "document":
            return await self._retrieve_document_metadata(entity_id)
        if entity_type == "case":
            return await self._retrieve_case_metadata(entity_id)
        if entity_type == "clause":
            return await self._retrieve_clause_metadata(entity_id)
        return await self._retrieve_statute_metadata(entity_id)

    async def retrieve_document_metadata(self, document_id: UUID) -> MetadataRecord | None:
        """Retrieve metadata for a single document."""
        return await self._retrieve_document_metadata(document_id)

    async def retrieve_case_metadata(self, case_id: UUID) -> MetadataRecord | None:
        """Retrieve metadata for a single case."""
        return await self._retrieve_case_metadata(case_id)

    async def retrieve_clause_metadata(self, clause_id: UUID) -> MetadataRecord | None:
        """Retrieve metadata for a single clause."""
        return await self._retrieve_clause_metadata(clause_id)

    async def _retrieve_document_metadata(self, document_id: UUID) -> MetadataRecord | None:
        document = await self._session.get(Document, document_id)
        if document is None:
            return None

        return MetadataRecord(
            entity_type="document",
            entity_id=document.id,
            fields={
                "filename": document.filename,
                "file_type": document.file_type,
                "title": document.title,
                "status": document.status,
                "contract_id": document.contract_id,
                "document_subtype": document.document_subtype,
                "document_date": document.document_date,
                "parties_involved": document.parties_involved,
                "page_count": document.page_count,
                "file_size_bytes": document.file_size_bytes,
                "chunk_count": document.chunk_count,
                "keywords": document.keywords,
                "summary": document.summary,
                "content_hash": document.content_hash,
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            },
            custom_metadata=document.doc_metadata,
        )

    async def _retrieve_case_metadata(self, case_id: UUID) -> MetadataRecord | None:
        case = await self._session.get(Case, case_id)
        if case is None:
            return None

        return MetadataRecord(
            entity_type="case",
            entity_id=case.id,
            fields={
                "case_citation": case.case_citation,
                "case_name": case.case_name,
                "court": case.court,
                "jurisdiction": case.jurisdiction,
                "filing_date": case.filing_date,
                "decision_date": case.decision_date,
                "case_type": case.case_type,
                "case_status": case.case_status,
                "primary_judge": case.primary_judge,
                "docket_number": case.docket_number,
                "summary": case.summary,
                "keywords": case.keywords,
                "legal_act_references": case.legal_act_references,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
            },
            custom_metadata=case.case_metadata,
        )

    async def _retrieve_clause_metadata(self, clause_id: UUID) -> MetadataRecord | None:
        clause = await self._session.get(Clause, clause_id)
        if clause is None:
            return None

        return MetadataRecord(
            entity_type="clause",
            entity_id=clause.id,
            fields={
                "document_id": clause.document_id,
                "parent_clause_id": clause.parent_clause_id,
                "clause_number": clause.clause_number,
                "title": clause.title,
                "clause_type": clause.clause_type,
                "page_number": clause.page_number,
                "position_order": clause.position_order,
                "risk_level": clause.risk_level,
                "keywords": clause.keywords,
                "related_clause_ids": clause.related_clause_ids,
                "created_at": clause.created_at,
                "updated_at": clause.updated_at,
            },
            custom_metadata=clause.clause_metadata,
        )

    async def _retrieve_statute_metadata(self, statute_id: UUID) -> MetadataRecord | None:
        statute = await self._session.get(Statute, statute_id)
        if statute is None:
            return None

        return MetadataRecord(
            entity_type="statute",
            entity_id=statute.id,
            fields={
                "statute_code": statute.statute_code,
                "act_name": statute.act_name,
                "act_short_name": statute.act_short_name,
                "title": statute.title,
                "section_title": statute.section_title,
                "jurisdiction": statute.jurisdiction,
                "enactment_year": statute.enactment_year,
                "category": statute.category,
                "section_number": statute.section_number,
                "effective_date": statute.effective_date,
                "keywords": statute.keywords,
                "created_at": statute.created_at,
                "updated_at": statute.updated_at,
            },
            custom_metadata=statute.statute_metadata,
        )

    @staticmethod
    def _to_contract_summary(document: Document) -> ContractSummary:
        return ContractSummary(
            id=document.id,
            title=document.title,
            filename=document.filename,
            contract_id=document.contract_id,
            document_date=document.document_date,
            document_subtype=document.document_subtype,
            parties_involved=document.parties_involved,
            status=document.status,
            summary=document.summary,
        )

    @staticmethod
    def _to_clause_summary(clause: Clause) -> ClauseSummary:
        document_title = clause.document.title if clause.document else None
        return ClauseSummary(
            id=clause.id,
            document_id=clause.document_id,
            clause_number=clause.clause_number,
            title=clause.title,
            content=clause.content,
            clause_type=clause.clause_type,
            page_number=clause.page_number,
            risk_level=clause.risk_level,
            keywords=clause.keywords,
            document_title=document_title,
        )

    @staticmethod
    def _to_case_summary(case: Case) -> CaseSummary:
        return CaseSummary(
            id=case.id,
            case_citation=case.case_citation,
            case_name=case.case_name,
            docket_number=case.docket_number,
            court=case.court,
            jurisdiction=case.jurisdiction,
            filing_date=case.filing_date,
            decision_date=case.decision_date,
            case_type=case.case_type,
            case_status=case.case_status,
            summary=case.summary,
        )
