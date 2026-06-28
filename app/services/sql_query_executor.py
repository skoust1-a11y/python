"""Execute SQL query plans against SqlRetrievalService."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.sql_query_planner import SqlOperation, SqlQueryPlan
from app.services.sql_retrieval_service import (
    CaseSummary,
    ClauseSummary,
    ContractSummary,
    MetadataRecord,
    SqlRetrievalService,
)


@dataclass
class SqlRetrievalResult:
    """Aggregated structured retrieval output."""

    contracts: list[ContractSummary] = field(default_factory=list)
    clauses: list[ClauseSummary] = field(default_factory=list)
    cases: list[CaseSummary] = field(default_factory=list)
    metadata_records: list[MetadataRecord] = field(default_factory=list)
    plan_explanation: str = ""

    @property
    def total_count(self) -> int:
        return (
            len(self.contracts)
            + len(self.clauses)
            + len(self.cases)
            + len(self.metadata_records)
        )


class SqlQueryExecutor:
    """Run planned SQL operations and aggregate results."""

    def __init__(self, session: AsyncSession) -> None:
        self._sql = SqlRetrievalService(session)

    async def execute(
        self,
        plan: SqlQueryPlan,
        *,
        document_id: UUID | None = None,
    ) -> SqlRetrievalResult:
        result = SqlRetrievalResult(plan_explanation=plan.explanation)

        for operation in plan.operations:
            await self._run_operation(operation, result, document_id=document_id)

        return result

    async def _run_operation(
        self,
        operation: SqlOperation,
        result: SqlRetrievalResult,
        *,
        document_id: UUID | None,
    ) -> None:
        op_type = operation.type
        params: dict[str, Any] = operation.params

        if op_type == "contracts_by_year":
            contracts = await self._sql.find_contracts_signed_in_year(params["year"])
            result.contracts.extend(contracts)
            return

        if op_type == "clauses_by_topic":
            scope = document_id
            clauses = await self._sql.find_clauses_related_to(
                params["topic"],
                document_id=scope,
            )
            result.clauses.extend(clauses)
            return

        if op_type == "case_by_number":
            cases = await self._sql.find_case_by_number(params["case_number"])
            result.cases.extend(cases)
            return

        if op_type == "metadata_lookup":
            record = await self._sql.retrieve_metadata(
                params["entity_type"],
                UUID(params["entity_id"]),
            )
            if record is not None:
                result.metadata_records.append(record)
