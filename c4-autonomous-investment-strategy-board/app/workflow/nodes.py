"""LangGraph node and routing functions for one strategy-board run."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.agents.base import AgentRuntime
from app.agents.contracts import AgentInput
from app.agents.execution import execute_agent
from app.agents.manager import (
    FUNDAMENTAL_AGENT,
    INVOCATION_ORDER,
    MARKET_AGENT,
    OPTIMIZATION_AGENT,
    PORTFOLIO_AGENTS,
    RISK_AGENT,
    SYNTHESIS_SYSTEM_PROMPT,
    ManagerSynthesis,
    _assumptions,
    _build_plan,
    _capped_confidence,
    _limitations,
    _resolve_symbols,
    _review_results,
    _specialist_extras,
    _synthesis_prompt,
    _unique,
)
from app.exceptions import AgentError, AppError
from app.models.common import DataSourceMetadata, DomainModel, Evidence
from app.models.portfolio import Portfolio
from app.models.types import NonEmptyText
from app.workflow.critic import (
    MAX_REFLECTION_CYCLES,
    evaluate_critique,
    needs_critique,
    reanalysis_agents,
    records_from_findings,
)
from app.workflow.mapping import snapshot_update_from_output
from app.workflow.runtime import WorkflowRuntime
from app.workflow.state import (
    AgentResultSnapshot,
    ConflictRecord,
    CritiqueRecord,
    ExecutionMetadata,
    FinalRecommendation,
    InvestmentState,
    SelectedStock,
    UserRequest,
)

UTC = timezone.utc
logger = logging.getLogger("app.workflow")

PLAN = "plan"
MARKET = MARKET_AGENT
FUNDAMENTAL = FUNDAMENTAL_AGENT
JOIN = "join"
RISK = RISK_AGENT
OPTIMIZE = OPTIMIZATION_AGENT
COLLECT = "collect"
DETECT_CONFLICTS = "detect_conflicts"
CRITIQUE = "critique"
REANALYZE = "reanalyze"
SYNTHESIZE = "synthesize"

CRITIQUE_SYSTEM_PROMPT = (
    "You are a Portfolio Manager reviewer. Critique using only the supplied "
    "structured findings. Check evidence coverage, unsupported claims, agent "
    "disagreement, missing analysis, stale or unavailable data, and known "
    "portfolio-constraint violations. "
    "Do not invent prices, weights, fundamentals, or other figures. "
    "Do not recommend executing trades. "
    "Do not include chain-of-thought, scratchpads, or step-by-step hidden "
    "reasoning. Return only the structured fields."
)


class WorkflowCritique(DomainModel):
    """Short reviewer note. Findings are produced in Python, not as hidden reasoning."""

    message: NonEmptyText
    target: str | None = None


def plan_node(state: InvestmentState, runtime: WorkflowRuntime) -> dict[str, Any]:
    runtime.reset()
    now = datetime.now(tz=UTC)
    llm = runtime.context.providers.llm
    request = state.get("user_request")
    if request is None:
        return _failed_plan_update(
            runtime,
            now,
            "user_request is required",
            llm_provider=llm.name,
            llm_model=llm.model or None,
        )

    extras = _planning_extras(state, runtime)
    portfolio = _portfolio_from_state(state, extras)
    payload = AgentInput(
        request_id=str(state.get("request_id") or "unknown"),
        symbols=list(request.symbols),
        question=request.text,
        extras=extras,
    )
    agent_runtime = _manager_runtime(state, runtime)
    try:
        symbols = _resolve_symbols(payload.symbols, portfolio)
        if not symbols and portfolio is None:
            raise AgentError(
                "Portfolio manager requires symbols or an uploaded portfolio."
            )
        plan = _build_plan(payload, agent_runtime, extras, portfolio, symbols)
        if plan.analysis_type == "stock_analysis" and payload.symbols:
            symbols = _unique(list(payload.symbols))
        specialist_extras = _specialist_extras(
            extras, portfolio, plan.analysis_type, symbols
        )
    except AppError as exc:
        runtime.payload = payload
        logger.warning(
            "workflow.plan_failed request_id=%s error=%s",
            payload.request_id,
            exc.message,
        )
        return _failed_plan_update(
            runtime,
            now,
            exc.message,
            llm_provider=llm.name,
            llm_model=llm.model or None,
        )

    runtime.plan = plan
    runtime.symbols = list(symbols)
    runtime.question = payload.question
    runtime.specialist_extras = specialist_extras
    runtime.payload = payload
    runtime.used_synthetic = bool(specialist_extras.get("synthetic_portfolio"))
    logger.info(
        "workflow.plan request_id=%s analysis_type=%s agents=%s",
        payload.request_id,
        plan.analysis_type,
        ",".join(plan.requested_agents),
    )
    logger.debug(
        "workflow.plan_details symbols=%s specialist_extras_keys=%s",
        symbols,
        list(specialist_extras.keys()),
    )
    update: dict[str, Any] = {
        "user_request": request.model_copy(
            update={"analysis_type": plan.analysis_type}
        ),
        "execution": ExecutionMetadata(
            status="running",
            current_node=PLAN,
            requested_agents=list(plan.requested_agents),
            started_at=runtime.started_at,
            updated_at=now,
            llm_provider=llm.name,
            llm_model=llm.model or None,
        ),
    }
    if state.get("selected_stock") is None and symbols:
        if plan.analysis_type == "stock_analysis" or len(symbols) == 1:
            update["selected_stock"] = SelectedStock(symbol=symbols[0])
    return update


def specialist_node(
    state: InvestmentState, runtime: WorkflowRuntime, name: str
) -> dict[str, Any]:
    now = datetime.now(tz=UTC)
    agent = runtime.specialists.get(name)
    if agent is None:
        logger.warning("workflow.skip name=%s reason=unregistered", name)
        return {
            "execution": ExecutionMetadata(
                current_node=name,
                updated_at=now,
                errors=[f"{name} is not registered."],
            )
        }
    extras = dict(runtime.specialist_extras)
    if runtime.reflection_cycle:
        extras["reflection_cycle"] = runtime.reflection_cycle
        extras["critique_findings"] = [
            item.model_dump(mode="json") for item in runtime.pending_findings
        ]
    research = {MARKET, FUNDAMENTAL}
    for prior_name, output in runtime.snapshot_outputs().items():
        if name in research and prior_name in research and prior_name != name:
            continue
        extras[prior_name] = output.model_dump(mode="json")
    payload = AgentInput(
        request_id=str(state.get("request_id") or "unknown"),
        symbols=list(runtime.symbols),
        question=runtime.question,
        extras=extras,
    )
    logger.info(
        "workflow.delegate agent=%s request_id=%s", name, payload.request_id
    )
    output = execute_agent(agent, payload, runtime.child_context)
    runtime.record(output)
    return snapshot_update_from_output(output, current_node=name, now=now)


def join_node(state: InvestmentState, runtime: WorkflowRuntime) -> dict[str, Any]:
    del state, runtime
    return {
        "execution": ExecutionMetadata(
            current_node=JOIN,
            updated_at=datetime.now(tz=UTC),
        )
    }


def collect_node(state: InvestmentState, runtime: WorkflowRuntime) -> dict[str, Any]:
    now = datetime.now(tz=UTC)
    if runtime.plan is None:
        return {"execution": ExecutionMetadata(current_node=COLLECT, updated_at=now)}
    missing, conflict_notes = _review_results(
        runtime.plan,
        runtime.snapshot_outputs(),
        runtime.specialist_extras,
        _portfolio_from_state(state, runtime.specialist_extras)
        if not runtime.used_synthetic
        else None,
    )
    runtime.missing = missing
    runtime.conflict_notes = conflict_notes
    logger.info(
        "workflow.collect request_id=%s invoked=%s missing=%d conflicts=%d",
        state.get("request_id"),
        ",".join(runtime.snapshot_outputs()),
        len(missing),
        len(conflict_notes),
    )
    runtime.reanalysis_agents = []
    return {
        "execution": ExecutionMetadata(
            current_node=COLLECT,
            updated_at=now,
            errors=list(missing),
        )
    }


def detect_conflicts_node(
    state: InvestmentState, runtime: WorkflowRuntime
) -> dict[str, Any]:
    del state
    records = [
        ConflictRecord(
            description=note,
            agents=_agents_mentioned(note),
            severity="error" if "failed" in note.lower() else "warning",
        )
        for note in runtime.conflict_notes
    ]
    return {
        "conflicts": records,
        "execution": ExecutionMetadata(
            current_node=DETECT_CONFLICTS,
            updated_at=datetime.now(tz=UTC),
        ),
    }


def critique_node(state: InvestmentState, runtime: WorkflowRuntime) -> dict[str, Any]:
    now = datetime.now(tz=UTC)
    findings = runtime.pending_findings or evaluate_critique(
        state,
        plan=runtime.plan,
        outputs=runtime.snapshot_outputs(),
        missing=runtime.missing,
        started_at=runtime.started_at,
    )
    runtime.pending_findings = list(findings)
    runtime.reanalysis_agents = reanalysis_agents(
        findings,
        reflection_cycle=runtime.reflection_cycle,
        has_portfolio=runtime.specialist_extras.get("portfolio") is not None,
    )
    records = records_from_findings(findings, previous=runtime.issued_critiques)
    agent_runtime = _manager_runtime(state, runtime)
    try:
        critique = agent_runtime.complete_structured(
            _critique_prompt(state, runtime, findings),
            WorkflowCritique,
            system=CRITIQUE_SYSTEM_PROMPT,
            metadata={"task": "manager-critique"},
        )
        records.append(
            CritiqueRecord(
                author="portfolio-manager",
                message=critique.message,
                target=critique.target,
                severity="info",
                resolved=False,
            )
        )
    except (AppError, ValidationError) as exc:
        logger.warning(
            "workflow.critique_skipped request_id=%s reason=%s", state.get("request_id"), exc
        )
    runtime.issued_critiques = [
        item for item in records if item.category is not None
    ]
    logger.info(
        "workflow.critique request_id=%s findings=%d reanalysis=%s cycle=%s",
        state.get("request_id"),
        len(findings),
        ",".join(runtime.reanalysis_agents) or "none",
        runtime.reflection_cycle,
    )
    return {
        "critiques": records,
        "execution": ExecutionMetadata(
            current_node=CRITIQUE,
            updated_at=now,
            reflection_cycle=runtime.reflection_cycle,
        ),
    }


def reanalyze_node(state: InvestmentState, runtime: WorkflowRuntime) -> dict[str, Any]:
    now = datetime.now(tz=UTC)
    if runtime.reflection_cycle >= MAX_REFLECTION_CYCLES:
        logger.warning(
            "workflow.reanalyze_blocked request_id=%s cycle=%s",
            state.get("request_id"),
            runtime.reflection_cycle,
        )
        runtime.reanalysis_agents = []
        return {
            "execution": ExecutionMetadata(
                current_node=REANALYZE,
                updated_at=now,
                reflection_cycle=runtime.reflection_cycle,
            )
        }
    runtime.reflection_cycle += 1
    extras = dict(runtime.specialist_extras)
    extras["reflection_cycle"] = runtime.reflection_cycle
    extras["critique_findings"] = [
        item.model_dump(mode="json") for item in runtime.pending_findings
    ]
    extras["prior_agent_results"] = {
        name: output.model_dump(mode="json")
        for name, output in runtime.snapshot_outputs().items()
    }
    runtime.specialist_extras = extras
    for name in runtime.reanalysis_agents:
        with runtime.lock:
            runtime.outputs.pop(name, None)
    logger.info(
        "workflow.reanalyze request_id=%s cycle=%s agents=%s",
        state.get("request_id"),
        runtime.reflection_cycle,
        ",".join(runtime.reanalysis_agents),
    )
    return {
        "execution": ExecutionMetadata(
            current_node=REANALYZE,
            updated_at=now,
            reflection_cycle=runtime.reflection_cycle,
        )
    }


def synthesize_node(
    state: InvestmentState, runtime: WorkflowRuntime
) -> dict[str, Any]:
    now = datetime.now(tz=UTC)
    duration_ms = max(0.0, (time.perf_counter() - runtime.started_perf) * 1000.0)
    llm = runtime.context.providers.llm
    execution = state.get("execution")
    if runtime.plan is None:
        message = "The request could not be analyzed."
        detail = (
            execution.errors[0]
            if execution is not None and execution.errors
            else "Provide symbols or an uploaded portfolio."
        )
        logger.error("workflow.synthesize_aborted reason=no_plan detail=%s", detail)
        return {
            "final_recommendation": FinalRecommendation(
                summary=message,
                recommendation=detail,
                limitations=[
                    "No specialist analysis was performed.",
                    "Trade execution is not implemented.",
                ],
                assumptions=["Trade execution is not implemented."],
                confidence=0.2,
            ),
            "execution": ExecutionMetadata(
                status="failed",
                current_node=SYNTHESIZE,
                updated_at=now,
                duration_ms=duration_ms,
                llm_provider=llm.name,
                llm_model=llm.model or None,
            ),
        }

    payload = runtime.payload or AgentInput(
        request_id=str(state.get("request_id") or "unknown"),
        symbols=list(runtime.symbols),
        question=runtime.question,
    )
    results = runtime.snapshot_outputs()
    missing = list(runtime.missing)
    unresolved = [
        item.message
        for item in (state.get("critiques") or [])
        if not item.resolved
    ]
    conflicts = _unique([*runtime.conflict_notes, *unresolved])
    uploaded = _portfolio_from_state(state, {})
    assumptions = _assumptions(
        runtime.plan, runtime.specialist_extras, runtime.used_synthetic, uploaded
    )
    limitations = _limitations(
        runtime.plan,
        results,
        missing,
        runtime.used_synthetic,
        runtime.specialist_extras,
    )
    agent_runtime = _manager_runtime(state, runtime)
    try:
        synthesis = agent_runtime.complete_structured(
            _synthesis_prompt(
                payload,
                runtime.plan,
                results,
                missing,
                conflicts,
                assumptions,
                limitations,
            ),
            ManagerSynthesis,
            system=SYNTHESIS_SYSTEM_PROMPT,
            metadata={"task": "manager-synthesis"},
        )
    except (AppError, ValidationError) as exc:
        logger.warning(
            "workflow.synthesis_fallback request_id=%s error=%s", payload.request_id, exc
        )
        synthesis = _fallback_synthesis(results, missing, conflicts)

    confidence = _capped_confidence(
        synthesis.confidence, results, missing, conflicts
    )
    recommendation = FinalRecommendation(
        summary=synthesis.summary,
        recommendation=synthesis.recommendation,
        findings=list(synthesis.findings),
        risks=_unique([*synthesis.risks, *conflicts]),
        assumptions=_unique([*assumptions, *synthesis.assumptions]),
        limitations=_unique([*limitations, *synthesis.limitations]),
        confidence=confidence,
    )
    return {
        "final_recommendation": recommendation,
        "agent_results": {
            "portfolio-manager": AgentResultSnapshot(
                agent="portfolio-manager",
                role="portfolio-manager",
                status="succeeded",
                summary=recommendation.summary,
                findings=list(recommendation.findings),
                confidence=confidence,
            )
        },
        "evidence": [
            Evidence(
                source=DataSourceMetadata(
                    provider="portfolio-manager",
                    source="manager-orchestration",
                    timestamp=now,
                ),
                field="trade_execution",
                value="not_implemented",
            )
        ],
        "execution": ExecutionMetadata(
            status="completed",
            current_node=SYNTHESIZE,
            updated_at=now,
            duration_ms=duration_ms,
            llm_provider=llm.name,
            llm_model=llm.model or None,
            reflection_cycle=runtime.reflection_cycle,
        ),
    }


def route_after_plan(state: InvestmentState, runtime: WorkflowRuntime) -> list[str]:
    execution = state.get("execution")
    if runtime.plan is None or (
        execution is not None and execution.status == "failed"
    ):
        return [SYNTHESIZE]
    requested = set(runtime.plan.requested_agents)
    nodes: list[str] = []
    if MARKET in requested and runtime.symbols:
        nodes.append(MARKET)
    if FUNDAMENTAL in requested and runtime.symbols:
        nodes.append(FUNDAMENTAL)
    if nodes:
        return nodes
    return [JOIN]


def route_after_join(state: InvestmentState, runtime: WorkflowRuntime) -> str:
    del state
    if _should_run(runtime, RISK):
        return RISK
    if _should_run(runtime, OPTIMIZE):
        return OPTIMIZE
    return COLLECT


def route_after_risk(state: InvestmentState, runtime: WorkflowRuntime) -> str:
    del state
    if _should_run(runtime, OPTIMIZE):
        return OPTIMIZE
    return COLLECT


def route_after_conflicts(state: InvestmentState, runtime: WorkflowRuntime) -> str:
    findings = evaluate_critique(
        state,
        plan=runtime.plan,
        outputs=runtime.snapshot_outputs(),
        missing=runtime.missing,
        started_at=runtime.started_at,
    )
    runtime.pending_findings = list(findings)
    if needs_critique(findings):
        return CRITIQUE
    return SYNTHESIZE


def route_after_critique(state: InvestmentState, runtime: WorkflowRuntime) -> str:
    cycle = _reflection_cycle(state, runtime)
    if cycle >= MAX_REFLECTION_CYCLES:
        runtime.reanalysis_agents = []
        return SYNTHESIZE
    if runtime.reanalysis_agents:
        return REANALYZE
    return SYNTHESIZE


def route_after_reanalyze(state: InvestmentState, runtime: WorkflowRuntime) -> list[str] | str:
    del state
    requested = set(runtime.reanalysis_agents)
    if not requested:
        return COLLECT
    nodes: list[str] = []
    if MARKET in requested:
        nodes.append(MARKET)
    if FUNDAMENTAL in requested:
        nodes.append(FUNDAMENTAL)
    if nodes:
        return nodes
    if RISK in requested:
        return RISK
    if OPTIMIZE in requested:
        return OPTIMIZE
    return COLLECT


def _should_run(runtime: WorkflowRuntime, name: str) -> bool:
    if runtime.plan is None or name not in runtime.plan.requested_agents:
        return False
    if runtime.reanalysis_agents and name not in runtime.reanalysis_agents:
        return False
    if name in runtime.snapshot_outputs():
        return False
    if name in PORTFOLIO_AGENTS and runtime.specialist_extras.get("portfolio") is None:
        logger.info("workflow.skip name=%s reason=missing-portfolio", name)
        return False
    return True


def _reflection_cycle(state: InvestmentState, runtime: WorkflowRuntime) -> int:
    execution = state.get("execution")
    state_cycle = (
        execution.reflection_cycle
        if execution is not None and execution.reflection_cycle is not None
        else 0
    )
    return max(runtime.reflection_cycle, state_cycle)


def _planning_extras(
    state: InvestmentState, runtime: WorkflowRuntime
) -> dict[str, Any]:
    extras = dict(runtime.context.extras or {})
    extras.pop("specialists", None)
    request = state.get("user_request")
    if isinstance(request, UserRequest):
        if request.analysis_type:
            extras["analysis_type"] = request.analysis_type
        bench = request.benchmark or request.index_symbol
        if bench:
            extras["index_symbol"] = bench
            extras["benchmark"] = bench
    portfolio = state.get("portfolio")
    if portfolio is not None:
        extras["portfolio"] = portfolio
    profile = state.get("investment_profile")
    if profile is not None:
        extras["investment_profile"] = profile
    return extras


def _portfolio_from_state(
    state: InvestmentState, extras: dict[str, Any]
) -> Portfolio | None:
    portfolio = state.get("portfolio")
    if isinstance(portfolio, Portfolio):
        return portfolio
    raw = extras.get("portfolio")
    return raw if isinstance(raw, Portfolio) else None


def _manager_runtime(
    state: InvestmentState, runtime: WorkflowRuntime
) -> AgentRuntime:
    return AgentRuntime(
        providers=runtime.context.providers,
        agent_name="portfolio-manager",
        request_id=str(state.get("request_id") or "unknown"),
        extras=dict(runtime.context.extras or {}),
    )


def _failed_plan_update(
    runtime: WorkflowRuntime,
    now: datetime,
    message: str,
    *,
    llm_provider: str,
    llm_model: str | None,
) -> dict[str, Any]:
    return {
        "execution": ExecutionMetadata(
            status="failed",
            current_node=PLAN,
            started_at=runtime.started_at,
            updated_at=now,
            llm_provider=llm_provider,
            llm_model=llm_model,
            errors=[message],
        )
    }


def _agents_mentioned(note: str) -> list[str]:
    mentioned = [name for name in INVOCATION_ORDER if name in note]
    return mentioned or ["portfolio-manager"]


def _critique_prompt(
    state: InvestmentState,
    runtime: WorkflowRuntime,
    findings: list[Any],
) -> str:
    bundle = {
        "request_id": state.get("request_id"),
        "question": runtime.question,
        "analysis_type": runtime.plan.analysis_type if runtime.plan else None,
        "findings": [item.model_dump(mode="json") for item in findings],
        "conflicts": [
            item.model_dump(mode="json") for item in (state.get("conflicts") or [])
        ],
        "missing_information": list(runtime.missing),
        "specialist_results": {
            name: {
                "status": output.status,
                "summary": output.summary,
                "findings": list(output.findings),
                "evidence_count": len(output.evidence),
            }
            for name, output in runtime.snapshot_outputs().items()
        },
        "trade_execution": "not_implemented",
        "rules": [
            "Use only the supplied structured findings.",
            "Do not invent figures or recommend executing trades.",
            "Do not include chain-of-thought or hidden reasoning.",
            "Do not propose additional autonomous retry loops.",
        ],
    }
    return (
        "Review the structured critique findings and return a short critique "
        "message and optional target.\n\n"
        + json.dumps(bundle, indent=2, default=str)
    )


def _fallback_synthesis(
    results: dict[str, Any],
    missing: list[str],
    conflicts: list[str],
) -> ManagerSynthesis:
    findings = [f"{name}: {output.summary}" for name, output in results.items()]
    return ManagerSynthesis(
        summary=(
            "Specialist results were collected without additional interpretation."
            if results
            else "No specialist results were available."
        ),
        findings=findings or ["No specialist findings were produced."],
        recommendation=(
            "Hold the current approach pending better specialist coverage. "
            "Do not place trades."
        ),
        risks=list(conflicts) or ["Analysis coverage is incomplete."],
        assumptions=[
            "Specialist outputs are the only analytical inputs; missing fields "
            "were not estimated."
        ],
        limitations=list(missing) or ["Interpretation is limited to specialist output."],
        confidence=0.4,
    )
