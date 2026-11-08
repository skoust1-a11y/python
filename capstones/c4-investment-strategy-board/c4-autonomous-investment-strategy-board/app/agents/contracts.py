"""Structured input and output contracts for investment-analysis agents.

Specialist agents will later extend these models. Timing, status, and
error fields on `AgentOutput` are owned by the execution wrapper.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.models.common import DomainModel, Evidence
from app.models.types import NonEmptyText, NonNegativeFinite, Symbol, UnitInterval


class AgentInput(DomainModel):
    """Provider-independent request passed into an agent."""

    request_id: NonEmptyText
    symbols: list[Symbol] = Field(default_factory=list)
    question: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class AgentAnalysis(DomainModel):
    """Specialist result before the wrapper attaches timing and status."""

    summary: NonEmptyText
    findings: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: UnitInterval | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(DomainModel):
    """Completed agent result, including execution metadata."""

    agent: NonEmptyText
    role: NonEmptyText
    status: Literal["succeeded", "failed"]
    summary: NonEmptyText
    findings: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: UnitInterval | None = None
    duration_ms: NonNegativeFinite
    llm_provider: NonEmptyText | None = None
    llm_model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)
