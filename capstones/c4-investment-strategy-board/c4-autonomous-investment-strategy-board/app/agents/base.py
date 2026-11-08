"""Agent contracts used by the LangGraph workflow.

Agents must not create independent workflows or call vendor SDKs directly.
LLM calls go through `AgentRuntime`, which uses the injected `LLMProvider`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.agents.contracts import AgentAnalysis, AgentInput
from app.agents.evidence import EvidenceCollector
from app.providers.contracts import LLMProvider, TModel
from app.providers.registry import ProviderBundle
from app.workflow.state import BoardState


@dataclass(frozen=True)
class AgentMetadata:
    """Stable identity for an agent. Specialists declare this; they do not
    name a vendor or model here.
    """

    name: str
    role: str
    description: str
    version: str = "0.1.0"

    def __post_init__(self) -> None:
        for field_name in ("name", "role", "description", "version"):
            value = str(getattr(self, field_name)).strip()
            if not value:
                raise ValueError(f"agent metadata {field_name} is required")
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True)
class AgentContext:
    """Runtime dependencies injected into an agent. Providers are never hardcoded."""

    providers: ProviderBundle
    extras: dict[str, Any] | None = None


@dataclass
class AgentRuntime:
    """Per-run facade over injected providers, evidence, and LLM access.

    Specialists must use this object instead of constructing an LLM adapter.
    """

    providers: ProviderBundle
    agent_name: str
    request_id: str
    evidence: EvidenceCollector = field(default_factory=EvidenceCollector)
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def llm(self) -> LLMProvider:
        return self.providers.llm

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Invoke the configured LLM adapter for free-form text."""
        return self.llm.complete(
            prompt,
            system=system,
            metadata=self._llm_metadata(metadata),
        )

    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        """Invoke the configured LLM adapter for schema-validated output."""
        return self.llm.complete_structured(
            prompt,
            response_model,
            system=system,
            metadata=self._llm_metadata(metadata),
        )

    def _llm_metadata(self, metadata: dict[str, Any] | None) -> dict[str, Any]:
        merged = {"agent": self.agent_name, "request_id": self.request_id}
        if metadata:
            merged.update(metadata)
        return merged


class Agent(ABC):
    """A single specialist that reads and writes shared graph state.

    Implement `metadata` and `analyze`. Execution timing, logging, evidence
    merging, and error handling belong to the wrapper, not to specialists.
    """

    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Name, role, and description for this specialist."""

    @property
    def name(self) -> str:
        return self.metadata.name

    def run(self, state: BoardState, context: AgentContext) -> BoardState:
        """Return an updated graph state. Implementations belong in `analyze`."""
        from app.agents.execution import run_agent_on_state

        return run_agent_on_state(self, state, context)

    @abstractmethod
    def analyze(self, payload: AgentInput, runtime: AgentRuntime) -> AgentAnalysis:
        """Perform specialist work using injected providers and the LLM contract."""
