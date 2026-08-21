"""Agent execution wrapper: logging, timing, errors, and evidence merge."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable

from pydantic import ValidationError

from app.agents.base import Agent, AgentContext, AgentRuntime
from app.agents.contracts import AgentAnalysis, AgentInput, AgentOutput
from app.agents.evidence import EvidenceCollector
from app.exceptions import AgentError, AppError
from app.models.common import Evidence
from app.workflow.state import BoardState

logger = logging.getLogger("app.agents")

_GENERIC_FAILURE = "An unexpected agent error occurred."


def execute_agent(agent: Agent, payload: AgentInput, context: AgentContext) -> AgentOutput:
    """Run `agent.analyze` with logging, timing, and error isolation."""
    started = time.perf_counter()
    runtime = AgentRuntime(
        providers=context.providers,
        agent_name=agent.name,
        request_id=payload.request_id,
        extras=dict(context.extras or {}),
    )
    logger.info(
        "agent.start name=%s role=%s request_id=%s llm=%s",
        agent.name,
        agent.metadata.role,
        payload.request_id,
        context.providers.llm.name,
    )
    try:
        analysis = agent.analyze(payload, runtime)
        if not isinstance(analysis, AgentAnalysis):
            raise AgentError("Agent analyze() must return AgentAnalysis.")
        duration_ms = _elapsed_ms(started)
        output = _succeeded_output(agent, context, analysis, runtime, duration_ms)
        _log_finish(output)
        return output
    except AppError as exc:
        output = _failed_output(agent, context, runtime, started, exc)
        logger.warning(
            "agent.finish name=%s status=failed duration_ms=%.1f error_code=%s",
            output.agent,
            output.duration_ms,
            output.error_code,
        )
        return output
    except Exception:
        logger.exception("agent.crash name=%s request_id=%s", agent.name, payload.request_id)
        output = _failed_output(
            agent,
            context,
            runtime,
            started,
            AgentError(_GENERIC_FAILURE),
        )
        logger.warning(
            "agent.finish name=%s status=failed duration_ms=%.1f error_code=%s",
            output.agent,
            output.duration_ms,
            output.error_code,
        )
        return output


def run_agent_on_state(agent: Agent, state: BoardState, context: AgentContext) -> BoardState:
    """Convert graph state to `AgentInput`, execute, and write artifacts back."""
    try:
        payload = input_from_state(state)
    except (KeyError, TypeError, ValidationError) as exc:
        logger.warning("agent.invalid_state name=%s error=%s", agent.name, exc)
        started = time.perf_counter()
        runtime = AgentRuntime(
            providers=context.providers,
            agent_name=agent.name,
            request_id=str(state.get("request_id") or "unknown"),
            extras=dict(context.extras or {}),
        )
        output = _failed_output(
            agent,
            context,
            runtime,
            started,
            AgentError("Invalid agent input from workflow state."),
        )
        return apply_output_to_state(state, output)
    return apply_output_to_state(state, execute_agent(agent, payload, context))


def input_from_state(state: BoardState) -> AgentInput:
    """Map shared graph state onto the structured agent input contract."""
    artifacts = dict(state.get("artifacts") or {})
    raw_symbols = artifacts.get("symbols") or []
    if isinstance(raw_symbols, str):
        raw_symbols = [raw_symbols]
    raw_question = artifacts.get("question")
    question = raw_question.strip() if isinstance(raw_question, str) else None
    extras = {key: value for key, value in artifacts.items() if key not in {"symbols", "question"}}
    return AgentInput(
        request_id=state["request_id"],
        symbols=list(raw_symbols),
        question=question or None,
        extras=extras,
    )


def apply_output_to_state(state: BoardState, output: AgentOutput) -> BoardState:
    """Merge an agent result into graph artifacts, messages, and errors."""
    artifacts = dict(state.get("artifacts") or {})
    artifacts[output.agent] = output.model_dump(mode="json")
    messages = list(state.get("messages") or [])
    messages.append(
        {
            "role": "agent",
            "name": output.agent,
            "content": output.summary,
            "status": output.status,
        }
    )
    errors = list(state.get("errors") or [])
    if output.status == "failed" and output.error_message:
        errors.append(f"{output.agent}: {output.error_message}")
    return BoardState(
        request_id=str(state.get("request_id") or output.extras.get("request_id") or "unknown"),
        messages=messages,
        artifacts=artifacts,
        errors=errors,
    )


def _succeeded_output(
    agent: Agent,
    context: AgentContext,
    analysis: AgentAnalysis,
    runtime: AgentRuntime,
    duration_ms: float,
) -> AgentOutput:
    return AgentOutput(
        agent=agent.name,
        role=agent.metadata.role,
        status="succeeded",
        summary=analysis.summary,
        findings=list(analysis.findings),
        evidence=_merge_evidence(runtime.evidence.items(), analysis.evidence),
        confidence=analysis.confidence,
        duration_ms=duration_ms,
        llm_provider=context.providers.llm.name,
        llm_model=context.providers.llm.model or None,
        extras=dict(analysis.extras),
    )


def _failed_output(
    agent: Agent,
    context: AgentContext,
    runtime: AgentRuntime,
    started: float,
    exc: AppError,
) -> AgentOutput:
    return AgentOutput(
        agent=agent.name,
        role=agent.metadata.role,
        status="failed",
        summary=f"{agent.name} failed",
        evidence=runtime.evidence.items(),
        duration_ms=_elapsed_ms(started),
        llm_provider=context.providers.llm.name,
        llm_model=context.providers.llm.model or None,
        error_code=exc.error_code,
        error_message=exc.message,
    )


def _merge_evidence(*groups: Iterable[Evidence]) -> list[Evidence]:
    collector = EvidenceCollector()
    for group in groups:
        collector.extend(group)
    return collector.items()


def _elapsed_ms(started: float) -> float:
    return max(0.0, (time.perf_counter() - started) * 1000.0)


def _log_finish(output: AgentOutput) -> None:
    logger.info(
        "agent.finish name=%s status=%s duration_ms=%.1f evidence=%d",
        output.agent,
        output.status,
        output.duration_ms,
        len(output.evidence),
    )
