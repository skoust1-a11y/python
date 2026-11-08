"""LLM-based planner that maps natural-language queries to SQL retrieval operations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from llama_index.core.llms import ChatMessage, MessageRole

from app.core.exceptions import RouterError
from app.prompts.templates import (
    SQL_QUERY_PLANNER_SYSTEM_PROMPT,
    SQL_QUERY_PLANNER_USER_PROMPT_TEMPLATE,
)
from app.services.llm_service import LLMService

OperationType = Literal[
    "contracts_by_year",
    "clauses_by_topic",
    "case_by_number",
    "metadata_lookup",
]

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_VALID_OPERATIONS: frozenset[str] = frozenset(
    {"contracts_by_year", "clauses_by_topic", "case_by_number", "metadata_lookup"}
)
_VALID_ENTITY_TYPES: frozenset[str] = frozenset({"document", "case", "clause", "statute"})


@dataclass(frozen=True)
class SqlOperation:
    """A single structured retrieval operation."""

    type: OperationType
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SqlQueryPlan:
    """Structured plan produced by the SQL query planner."""

    operations: tuple[SqlOperation, ...]
    explanation: str = ""


class SqlQueryPlanner:
    """Translate natural-language queries into SqlRetrievalService operations."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm_service = llm_service or LLMService()

    async def plan(self, query: str, *, provider: str | None = None) -> SqlQueryPlan:
        query = query.strip()
        if not query:
            return SqlQueryPlan(operations=(), explanation="Empty query — no SQL operations planned.")

        llm = self._llm_service.get_llm(provider)
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=SQL_QUERY_PLANNER_SYSTEM_PROMPT),
            ChatMessage(
                role=MessageRole.USER,
                content=SQL_QUERY_PLANNER_USER_PROMPT_TEMPLATE.format(query=query),
            ),
        ]

        try:
            response = await llm.achat(messages)
            raw = (response.message.content or "").strip()
            return self._validate_plan(self._parse_response(raw))
        except RouterError:
            raise
        except Exception as exc:
            raise RouterError(f"SQL query planning failed: {exc}") from exc

    def _parse_response(self, raw: str) -> dict[str, Any]:
        candidates = [raw]
        block_match = _JSON_BLOCK_RE.search(raw)
        if block_match:
            candidates.insert(0, block_match.group(1).strip())

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data

        raise RouterError("SQL planner response did not contain valid JSON")

    def _validate_plan(self, data: dict[str, Any]) -> SqlQueryPlan:
        explanation = data.get("explanation", "")
        if not isinstance(explanation, str):
            explanation = ""

        raw_ops = data.get("operations", [])
        if not isinstance(raw_ops, list):
            raw_ops = []

        operations: list[SqlOperation] = []
        for item in raw_ops:
            if not isinstance(item, dict):
                continue
            op_type = item.get("type")
            if not isinstance(op_type, str) or op_type not in _VALID_OPERATIONS:
                continue
            params = item.get("params", {})
            if not isinstance(params, dict):
                params = {}
            normalized = self._normalize_params(op_type, params)
            if normalized is not None:
                operations.append(SqlOperation(type=op_type, params=normalized))

        return SqlQueryPlan(
            operations=tuple(operations),
            explanation=explanation.strip() or "Structured retrieval plan generated.",
        )

    def _normalize_params(
        self,
        op_type: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        if op_type == "contracts_by_year":
            year = params.get("year")
            try:
                year_int = int(year)
            except (TypeError, ValueError):
                return None
            if year_int < 1900 or year_int > 2100:
                return None
            return {"year": year_int}

        if op_type == "clauses_by_topic":
            topic = params.get("topic")
            if not isinstance(topic, str) or not topic.strip():
                return None
            return {"topic": topic.strip()}

        if op_type == "case_by_number":
            case_number = params.get("case_number")
            if not isinstance(case_number, str) or not case_number.strip():
                return None
            return {"case_number": case_number.strip()}

        if op_type == "metadata_lookup":
            entity_type = params.get("entity_type")
            entity_id = params.get("entity_id")
            if (
                not isinstance(entity_type, str)
                or entity_type not in _VALID_ENTITY_TYPES
                or not isinstance(entity_id, str)
            ):
                return None
            try:
                UUID(entity_id)
            except ValueError:
                return None
            return {"entity_type": entity_type, "entity_id": entity_id}

        return None
