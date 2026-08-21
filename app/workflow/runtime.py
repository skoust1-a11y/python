"""Per-run workflow bookkeeping kept off the typed graph payload."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agents.base import Agent, AgentContext, AgentRuntime
from app.agents.contracts import AgentInput, AgentOutput
from app.agents.manager import _Plan, _resolve_specialists

UTC = timezone.utc


@dataclass
class WorkflowRuntime:
    """Mutable run context shared by graph nodes in a single invocation."""

    context: AgentContext
    specialists: dict[str, Agent]
    outputs: dict[str, AgentOutput] = field(default_factory=dict)
    plan: _Plan | None = None
    symbols: list[str] = field(default_factory=list)
    question: str | None = None
    specialist_extras: dict[str, Any] = field(default_factory=dict)
    payload: AgentInput | None = None
    missing: list[str] = field(default_factory=list)
    conflict_notes: list[str] = field(default_factory=list)
    pending_findings: list[Any] = field(default_factory=list)
    issued_critiques: list[Any] = field(default_factory=list)
    reanalysis_agents: list[str] = field(default_factory=list)
    reflection_cycle: int = 0
    used_synthetic: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    started_perf: float = field(default_factory=time.perf_counter)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.child_context = AgentContext(providers=self.context.providers)

    def reset(self) -> None:
        """Clear specialist results so a compiled graph can be reused sequentially."""
        with self.lock:
            self.outputs.clear()
        self.plan = None
        self.symbols = []
        self.question = None
        self.specialist_extras = {}
        self.payload = None
        self.missing = []
        self.conflict_notes = []
        self.pending_findings = []
        self.issued_critiques = []
        self.reanalysis_agents = []
        self.reflection_cycle = 0
        self.used_synthetic = False
        self.started_at = datetime.now(tz=UTC)
        self.started_perf = time.perf_counter()

    def record(self, output: AgentOutput) -> None:
        with self.lock:
            self.outputs[output.agent] = output

    def snapshot_outputs(self) -> dict[str, AgentOutput]:
        with self.lock:
            return dict(self.outputs)


def resolve_specialists(
    context: AgentContext,
    specialists: dict[str, Agent] | None = None,
) -> dict[str, Agent]:
    """Use injected specialists when provided; otherwise construct the defaults."""
    if specialists:
        return dict(specialists)
    runtime = AgentRuntime(
        providers=context.providers,
        agent_name="portfolio-manager",
        request_id="workflow-setup",
        extras=dict(context.extras or {}),
    )
    return _resolve_specialists(runtime)
