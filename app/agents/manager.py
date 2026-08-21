"""Portfolio Manager Agent.

Orchestrates specialist investment agents. It does not retrieve market,
fundamental, or news data itself. Numerical work stays in specialists and
Python tools. The LLM classifies the request and synthesizes a structured
recommendation from specialist output. Hidden chain-of-thought is not returned.
Trades are never executed.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import AwareDatetime, Field, ValidationError

from app.agents.base import Agent, AgentContext, AgentMetadata, AgentRuntime
from app.agents.contracts import AgentAnalysis, AgentInput, AgentOutput
from app.agents.execution import execute_agent
from app.agents.fundamental import FundamentalAnalysisAgent
from app.agents.market import MarketAnalysisAgent
from app.agents.optimization import PortfolioOptimizationAgent
from app.agents.risk import RiskAssessmentAgent
from app.exceptions import AgentError, AppError
from app.models.common import DataSourceMetadata, DomainModel, Evidence
from app.models.portfolio import Holding, Portfolio, SymbolValidation
from app.models.types import NonEmptyText, UnitInterval, normalize_symbol

UTC = timezone.utc
logger = logging.getLogger("app.agents")

MARKET_AGENT = "market-analysis"
FUNDAMENTAL_AGENT = "fundamental-analysis"
RISK_AGENT = "risk-assessment"
OPTIMIZATION_AGENT = "portfolio-optimization"

AnalysisType = Literal[
    "stock_analysis",
    "portfolio_risk",
    "portfolio_review",
    "portfolio_rebalancing",
]
DelegationRound = Literal["initial", "follow_up"]

CANONICAL_AGENTS: dict[str, tuple[str, ...]] = {
    "stock_analysis": (MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT),
    "portfolio_risk": (MARKET_AGENT, RISK_AGENT),
    "portfolio_review": (MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT),
    "portfolio_rebalancing": (
        MARKET_AGENT,
        FUNDAMENTAL_AGENT,
        RISK_AGENT,
        OPTIMIZATION_AGENT,
    ),
}
INVOCATION_ORDER = (
    MARKET_AGENT,
    FUNDAMENTAL_AGENT,
    RISK_AGENT,
    OPTIMIZATION_AGENT,
)
AGENT_ALIASES = {
    MARKET_AGENT: MARKET_AGENT,
    "market": MARKET_AGENT,
    "market-agent": MARKET_AGENT,
    "market_agent": MARKET_AGENT,
    "market analysis": MARKET_AGENT,
    FUNDAMENTAL_AGENT: FUNDAMENTAL_AGENT,
    "fundamental": FUNDAMENTAL_AGENT,
    "fundamental-agent": FUNDAMENTAL_AGENT,
    "fundamental_agent": FUNDAMENTAL_AGENT,
    "fundamental analysis": FUNDAMENTAL_AGENT,
    RISK_AGENT: RISK_AGENT,
    "risk": RISK_AGENT,
    "risk-agent": RISK_AGENT,
    "risk_agent": RISK_AGENT,
    "risk assessment": RISK_AGENT,
    OPTIMIZATION_AGENT: OPTIMIZATION_AGENT,
    "optimizer": OPTIMIZATION_AGENT,
    "portfolio-optimizer": OPTIMIZATION_AGENT,
    "portfolio_optimizer": OPTIMIZATION_AGENT,
    "portfolio optimizer": OPTIMIZATION_AGENT,
    "optimization": OPTIMIZATION_AGENT,
}
PORTFOLIO_AGENTS = {RISK_AGENT, OPTIMIZATION_AGENT}
MANAGER_EXTRA_KEYS = {
    "specialists",
    "analysis_type",
    "required_agents",
    "max_follow_up_rounds",
}
REBALANCE_TERMS = (
    "rebalance",
    "rebalancing",
    "reallocat",
    "optimize",
    "optimis",
    "optimizer",
    "target allocation",
    "new weights",
    "proposed allocation",
)
RISK_TERMS = (
    "risk",
    "concentration",
    "drawdown",
    "volatil",
    "diversif",
    "exposure",
    "tracking error",
    "correlation",
    "beta",
    "value at risk",
)
STOCK_TERMS = (
    "stock",
    "ticker",
    "share",
    "company",
    "equity",
    "fundamental",
    "valuation",
    "earnings",
    "price of",
    "analyze ",
)
FOLLOW_UP_FUNDAMENTAL_TERMS = (
    "valuation",
    "earning",
    "fundamental",
    "revenue",
    "margin",
    "balance sheet",
)
FOLLOW_UP_MARKET_TERMS = ("price", "trend", "momentum", "volume", "quote")
FOLLOW_UP_OPTIMIZER_TERMS = REBALANCE_TERMS
HIGH_CONCENTRATION = {"high", "severe"}

ROUTING_SYSTEM_PROMPT = (
    "You are a Portfolio Manager router. Classify the user request into exactly "
    "one analysis_type and the specialist agents required. "
    "Use only the allowed analysis types and agent names. "
    "Do not retrieve market data. Do not invent prices or holdings. "
    "Do not recommend trades. Do not include chain-of-thought, scratchpads, "
    "or step-by-step hidden reasoning. Return only the structured fields."
)
SYNTHESIS_SYSTEM_PROMPT = (
    "You are a Portfolio Manager synthesizing specialist investment-analysis "
    "results into a final recommendation. Interpret only the supplied specialist "
    "output. Do not invent prices, weights, fundamentals, risk metrics, or other "
    "figures. If a field is null or listed as unavailable, treat it as missing "
    "and say so. Do not execute or recommend brokerage trades, orders, or fills; "
    "any proposed allocation is a candidate for later evaluation, not a trade. "
    "Do not include chain-of-thought, scratchpads, or step-by-step hidden "
    "reasoning. Return only the structured fields."
)


class ManagerRouting(DomainModel):
    """LLM selection of analysis type and specialists. No reasoning payload."""

    analysis_type: AnalysisType
    required_agents: list[NonEmptyText] = Field(default_factory=list)


class ManagerSynthesis(DomainModel):
    """LLM reading of specialist results. Must not introduce new figures."""

    summary: NonEmptyText
    findings: list[NonEmptyText] = Field(default_factory=list)
    recommendation: NonEmptyText
    risks: list[NonEmptyText] = Field(default_factory=list)
    assumptions: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)
    confidence: UnitInterval


class AgentResultUsed(DomainModel):
    """Compact specialist result included in the manager recommendation."""

    agent: NonEmptyText
    role: NonEmptyText
    status: Literal["succeeded", "failed"]
    summary: NonEmptyText
    findings: list[NonEmptyText] = Field(default_factory=list)


class DelegationEvent(DomainModel):
    """One specialist invocation performed by the manager."""

    agent: NonEmptyText
    round: DelegationRound
    status: Literal["succeeded", "failed"]


class ManagerAgentExtras(DomainModel):
    """Structured payload stored on `AgentOutput.extras`."""

    analysis_type: AnalysisType
    requested_agents: list[NonEmptyText] = Field(default_factory=list)
    invoked_agents: list[NonEmptyText] = Field(default_factory=list)
    follow_up_agents: list[NonEmptyText] = Field(default_factory=list)
    agent_results_used: list[AgentResultUsed] = Field(default_factory=list)
    summary: NonEmptyText
    findings: list[NonEmptyText] = Field(default_factory=list)
    recommendation: NonEmptyText
    risks: list[NonEmptyText] = Field(default_factory=list)
    assumptions: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)
    missing_information: list[NonEmptyText] = Field(default_factory=list)
    conflicts: list[NonEmptyText] = Field(default_factory=list)
    delegation: list[DelegationEvent] = Field(default_factory=list)
    used_synthetic_portfolio: bool = False
    trade_execution: Literal["not_implemented"] = "not_implemented"
    analyzed_at: AwareDatetime


class PortfolioManagerAgent(Agent):
    """Orchestrator that delegates to specialists and synthesizes their results."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="portfolio-manager",
            role="portfolio-manager",
            description=(
                "Classifies the user request, selectively delegates to market, "
                "fundamental, risk, and portfolio-optimization specialists, "
                "resolves gaps and conflicts, and synthesizes a structured "
                "investment recommendation. Does not execute trades."
            ),
        )

    def analyze(self, payload: AgentInput, runtime: AgentRuntime) -> AgentAnalysis:
        extras = dict(payload.extras)
        portfolio = _portfolio_from_extras(extras)
        symbols = _resolve_symbols(payload.symbols, portfolio)
        if not symbols and portfolio is None:
            raise AgentError(
                "Portfolio manager requires symbols or an uploaded portfolio."
            )

        specialists = _resolve_specialists(runtime)
        plan = _build_plan(payload, runtime, extras, portfolio, symbols)
        if plan.analysis_type == "stock_analysis" and payload.symbols:
            symbols = _unique(list(payload.symbols))
        specialist_extras = _specialist_extras(extras, portfolio, plan.analysis_type, symbols)
        used_synthetic = bool(specialist_extras.get("synthetic_portfolio"))
        results: dict[str, AgentOutput] = {}
        delegation: list[DelegationEvent] = []

        _delegate(
            plan.requested_agents,
            payload,
            runtime,
            specialists,
            specialist_extras,
            symbols,
            results,
            delegation,
            round_name="initial",
        )
        missing, conflicts = _review_results(plan, results, specialist_extras, portfolio)
        follow_up = _follow_up_agents(
            plan, results, extras, payload.question, specialist_extras, specialists
        )
        if follow_up:
            _delegate(
                follow_up,
                payload,
                runtime,
                specialists,
                specialist_extras,
                symbols,
                results,
                delegation,
                round_name="follow_up",
            )
            missing, conflicts = _review_results(
                plan, results, specialist_extras, portfolio
            )

        used = [
            _result_used(results[name])
            for name in INVOCATION_ORDER
            if name in results
        ]
        evidence = _merge_evidence(runtime, results)
        assumptions = _assumptions(plan, specialist_extras, used_synthetic, portfolio)
        python_limitations = _limitations(
            plan, results, missing, used_synthetic, specialist_extras
        )
        synthesis = runtime.complete_structured(
            _synthesis_prompt(
                payload,
                plan,
                results,
                missing,
                conflicts,
                assumptions,
                python_limitations,
            ),
            ManagerSynthesis,
            system=SYNTHESIS_SYSTEM_PROMPT,
            metadata={"task": "manager-synthesis"},
        )
        extras_model = _build_extras(
            plan=plan,
            follow_up=follow_up,
            used=used,
            synthesis=synthesis,
            missing=missing,
            conflicts=conflicts,
            assumptions=assumptions,
            python_limitations=python_limitations,
            delegation=delegation,
            used_synthetic=used_synthetic,
        )
        return AgentAnalysis(
            summary=extras_model.summary,
            findings=list(extras_model.findings),
            evidence=evidence,
            confidence=_capped_confidence(
                synthesis.confidence, results, missing, conflicts
            ),
            extras=extras_model.model_dump(mode="json"),
        )


class _Plan:
    def __init__(self, analysis_type: AnalysisType, requested_agents: Sequence[str]) -> None:
        self.analysis_type: AnalysisType = analysis_type
        self.requested_agents: list[str] = _order_agents(requested_agents)


def _build_plan(
    payload: AgentInput,
    runtime: AgentRuntime,
    extras: Mapping[str, Any],
    portfolio: Portfolio | None,
    symbols: Sequence[str],
) -> _Plan:
    has_portfolio = portfolio is not None
    heuristic_type = _classify_heuristic(payload.question, has_portfolio, symbols)
    explicit_type = _analysis_type_from_extras(extras)
    explicit_agents = _agents_from_extras(extras)

    if explicit_type is not None or explicit_agents:
        analysis_type = explicit_type or _infer_analysis_type(explicit_agents, has_portfolio)
        agents = explicit_agents or list(CANONICAL_AGENTS[analysis_type])
        return _Plan(analysis_type, agents)

    routing = _route_with_llm(payload, runtime, heuristic_type, has_portfolio, symbols)
    if routing is not None:
        agents = _normalize_agent_names(routing.required_agents)
        analysis_type = routing.analysis_type
        if not agents:
            agents = list(CANONICAL_AGENTS[analysis_type])
        return _Plan(analysis_type, agents)
    return _Plan(heuristic_type, CANONICAL_AGENTS[heuristic_type])


def _route_with_llm(
    payload: AgentInput,
    runtime: AgentRuntime,
    heuristic_type: AnalysisType,
    has_portfolio: bool,
    symbols: Sequence[str],
) -> ManagerRouting | None:
    try:
        routing = runtime.complete_structured(
            _routing_prompt(payload, heuristic_type, has_portfolio, symbols),
            ManagerRouting,
            system=ROUTING_SYSTEM_PROMPT,
            metadata={"task": "manager-routing"},
        )
    except (AppError, ValidationError):
        logger.info(
            "manager.routing_fallback request_id=%s heuristic=%s",
            payload.request_id,
            heuristic_type,
        )
        return None
    return routing


def _classify_heuristic(
    question: str | None, has_portfolio: bool, symbols: Sequence[str]
) -> AnalysisType:
    text = (question or "").strip().lower()
    if _contains_any(text, REBALANCE_TERMS):
        return "portfolio_rebalancing"
    if has_portfolio and _contains_any(text, RISK_TERMS) and not _stock_only_intent(text, symbols):
        return "portfolio_risk"
    if has_portfolio and not _stock_only_intent(text, symbols):
        return "portfolio_review"
    return "stock_analysis"


def _stock_only_intent(text: str, symbols: Sequence[str]) -> bool:
    if not text:
        return False
    if _contains_any(text, ("portfolio", "holdings", "rebalance", "allocation")):
        return False
    if len(symbols) == 1 and symbols[0].lower() in text.lower():
        return True
    return _contains_any(text, STOCK_TERMS) and not _contains_any(text, ("portfolio",))


def _infer_analysis_type(agents: Sequence[str], has_portfolio: bool) -> AnalysisType:
    names = set(agents)
    if OPTIMIZATION_AGENT in names:
        return "portfolio_rebalancing"
    if names == {MARKET_AGENT, RISK_AGENT} or names == {RISK_AGENT}:
        return "portfolio_risk"
    if has_portfolio:
        return "portfolio_review"
    return "stock_analysis"


def _analysis_type_from_extras(extras: Mapping[str, Any]) -> AnalysisType | None:
    raw = extras.get("analysis_type")
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise AgentError("analysis_type must be a string.")
    value = raw.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "stock": "stock_analysis",
        "stock_only": "stock_analysis",
        "single_stock": "stock_analysis",
        "risk": "portfolio_risk",
        "portfolio-risk": "portfolio_risk",
        "rebalance": "portfolio_rebalancing",
        "rebalancing": "portfolio_rebalancing",
        "optimization": "portfolio_rebalancing",
        "review": "portfolio_review",
    }
    value = aliases.get(value, value)
    if value not in CANONICAL_AGENTS:
        raise AgentError(
            "analysis_type must be stock_analysis, portfolio_risk, "
            "portfolio_review, or portfolio_rebalancing."
        )
    return value  # type: ignore[return-value]


def _agents_from_extras(extras: Mapping[str, Any]) -> list[str]:
    raw = extras.get("required_agents")
    if raw is None or raw == []:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, Sequence) or isinstance(raw, (bytes, bytearray)):
        raise AgentError("required_agents must be a list of agent names.")
    names = _normalize_agent_names(raw)
    if not names:
        raise AgentError("required_agents must contain known specialist agent names.")
    return names


def _normalize_agent_names(values: Sequence[Any]) -> list[str]:
    names: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            continue
        key = re.sub(r"[\s_]+", "-", item.strip().lower())
        key = AGENT_ALIASES.get(key, AGENT_ALIASES.get(key.replace("-agent", ""), key))
        if key in AGENT_ALIASES:
            key = AGENT_ALIASES[key]
        if key in {MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT, OPTIMIZATION_AGENT}:
            if key not in names:
                names.append(key)
    return names


def _order_agents(agents: Sequence[str]) -> list[str]:
    requested = [name for name in agents if name in INVOCATION_ORDER]
    return [name for name in INVOCATION_ORDER if name in requested]


def _resolve_specialists(runtime: AgentRuntime) -> dict[str, Agent]:
    injected = runtime.extras.get("specialists")
    if isinstance(injected, Mapping) and injected:
        resolved: dict[str, Agent] = {}
        for key, agent in injected.items():
            name = _normalize_agent_names([str(key)])
            if name and isinstance(agent, Agent):
                resolved[name[0]] = agent
        if resolved:
            return resolved
    return {
        MARKET_AGENT: MarketAnalysisAgent(),
        FUNDAMENTAL_AGENT: FundamentalAnalysisAgent(),
        RISK_AGENT: RiskAssessmentAgent(),
        OPTIMIZATION_AGENT: PortfolioOptimizationAgent(),
    }


def _resolve_symbols(symbols: Sequence[str], portfolio: Portfolio | None) -> list[str]:
    resolved = _unique([normalize_symbol(symbol) for symbol in symbols])
    if portfolio is None:
        return resolved
    for holding in portfolio.holdings:
        if holding.symbol not in resolved:
            resolved.append(holding.symbol)
    return resolved


def _portfolio_from_extras(extras: Mapping[str, Any]) -> Portfolio | None:
    raw = extras.get("portfolio")
    if raw is None:
        return None
    if isinstance(raw, Portfolio):
        return raw
    if isinstance(raw, dict):
        try:
            return Portfolio.model_validate(_portable_portfolio_payload(raw))
        except ValidationError as exc:
            raise AgentError("portfolio extras must be a confirmed Portfolio payload.") from exc
    raise AgentError("portfolio extras must be a confirmed Portfolio payload.")


def _portable_portfolio_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = dict(raw)
    payload.pop("holding_count", None)
    holdings = payload.get("holdings")
    if isinstance(holdings, list):
        cleaned: list[Any] = []
        for item in holdings:
            if isinstance(item, dict):
                holding = dict(item)
                holding.pop("cost_value", None)
                cleaned.append(holding)
            else:
                cleaned.append(item)
        payload["holdings"] = cleaned
    return payload


def _specialist_extras(
    extras: Mapping[str, Any],
    portfolio: Portfolio | None,
    analysis_type: AnalysisType,
    symbols: Sequence[str],
) -> dict[str, Any]:
    forwarded = {
        key: value for key, value in extras.items() if key not in MANAGER_EXTRA_KEYS
    }
    if portfolio is not None:
        forwarded["portfolio"] = portfolio
        return forwarded
    if analysis_type == "stock_analysis" and symbols:
        forwarded["portfolio"] = _synthetic_unit_portfolio(symbols)
        forwarded["synthetic_portfolio"] = True
    return forwarded


def _synthetic_unit_portfolio(symbols: Sequence[str]) -> Portfolio:
    count = len(symbols)
    weight = 1.0 / count if count else 1.0
    holdings = [
        Holding(
            symbol=symbol,
            quantity=1.0,
            weight=weight,
            symbol_validation=SymbolValidation(
                input=symbol, normalized=symbol, status="valid"
            ),
        )
        for symbol in symbols
    ]
    return Portfolio(
        id="synthetic-unit-portfolio",
        holdings=holdings,
        source_filename="synthetic-unit-portfolio",
        source_format="csv",
        imported_at=datetime.now(tz=UTC),
    )


def _delegate(
    agents: Sequence[str],
    payload: AgentInput,
    runtime: AgentRuntime,
    specialists: Mapping[str, Agent],
    specialist_extras: dict[str, Any],
    symbols: Sequence[str],
    results: dict[str, AgentOutput],
    delegation: list[DelegationEvent],
    *,
    round_name: DelegationRound,
) -> None:
    child_context = AgentContext(providers=runtime.providers)
    for name in _order_agents(agents):
        if name in results:
            continue
        agent = specialists.get(name)
        if agent is None:
            continue
        if name in PORTFOLIO_AGENTS and specialist_extras.get("portfolio") is None:
            logger.info(
                "manager.skip name=%s reason=missing-portfolio request_id=%s",
                name,
                payload.request_id,
            )
            continue
        request_extras = dict(specialist_extras)
        for prior_name, output in results.items():
            request_extras[prior_name] = output.model_dump(mode="json")
        specialist_payload = AgentInput(
            request_id=payload.request_id,
            symbols=list(symbols),
            question=payload.question,
            extras=request_extras,
        )
        logger.info(
            "manager.delegate agent=%s round=%s request_id=%s",
            name,
            round_name,
            payload.request_id,
        )
        output = execute_agent(agent, specialist_payload, child_context)
        results[name] = output
        delegation.append(
            DelegationEvent(agent=name, round=round_name, status=output.status)
        )
        runtime.evidence.extend(output.evidence)


def _review_results(
    plan: _Plan,
    results: Mapping[str, AgentOutput],
    specialist_extras: Mapping[str, Any],
    portfolio: Portfolio | None,
) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    conflicts: list[str] = []
    if plan.analysis_type in {"portfolio_risk", "portfolio_rebalancing", "portfolio_review"}:
        if portfolio is None and specialist_extras.get("portfolio") is None:
            missing.append("Uploaded portfolio data is required for this analysis.")
    for name in plan.requested_agents:
        output = results.get(name)
        if output is None:
            if name in PORTFOLIO_AGENTS and specialist_extras.get("portfolio") is None:
                missing.append(f"{name} was not invoked because no portfolio was available.")
            else:
                missing.append(f"{name} was not invoked.")
            continue
        if output.status == "failed":
            message = output.error_message or output.summary
            missing.append(f"{name} did not complete: {message}")
            conflicts.append(f"{name} failed during delegation.")
            continue
        unavailable = _unavailable_from_output(output)
        if unavailable:
            missing.append(
                f"{name} reported unavailable inputs: " + ", ".join(unavailable) + "."
            )
    conflicts.extend(_content_conflicts(results))
    return _unique(missing), _unique(conflicts)


def _unavailable_from_output(output: AgentOutput) -> list[str]:
    extras = output.extras or {}
    raw = extras.get("unavailable")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if item]


def _content_conflicts(results: Mapping[str, AgentOutput]) -> list[str]:
    conflicts: list[str] = []
    market = results.get(MARKET_AGENT)
    fundamental = results.get(FUNDAMENTAL_AGENT)
    optimization = results.get(OPTIMIZATION_AGENT)
    market_trend = _extra_value(market, "trend") if market else None
    health = _extra_value(fundamental, "financial_health") if fundamental else None
    if market_trend == "uptrend" and health == "stressed":
        conflicts.append(
            "Market analysis reports an uptrend while fundamental financial health is stressed."
        )
    if market_trend == "downtrend" and health == "healthy":
        conflicts.append(
            "Market analysis reports a downtrend while fundamental financial health is healthy."
        )
    if optimization is not None and optimization.status == "succeeded":
        if _extra_value(optimization, "feasible") is False:
            conflicts.append(
                "Portfolio optimizer did not produce a feasible candidate allocation."
            )
    return conflicts


def _extra_value(output: AgentOutput | None, key: str) -> Any:
    if output is None:
        return None
    extras = output.extras or {}
    return extras.get(key)


def _follow_up_agents(
    plan: _Plan,
    results: Mapping[str, AgentOutput],
    extras: Mapping[str, Any],
    question: str | None,
    specialist_extras: Mapping[str, Any],
    specialists: Mapping[str, Agent],
) -> list[str]:
    raw_rounds = extras.get("max_follow_up_rounds", 1)
    try:
        max_rounds = int(raw_rounds)
    except (TypeError, ValueError):
        max_rounds = 1
    if max_rounds < 1:
        return []
    text = (question or "").lower()
    needed: list[str] = []
    if _contains_any(text, FOLLOW_UP_MARKET_TERMS) and MARKET_AGENT not in results:
        needed.append(MARKET_AGENT)
    if _contains_any(text, FOLLOW_UP_FUNDAMENTAL_TERMS) and FUNDAMENTAL_AGENT not in results:
        needed.append(FUNDAMENTAL_AGENT)
    if (
        specialist_extras.get("portfolio") is not None
        and _contains_any(text, FOLLOW_UP_OPTIMIZER_TERMS)
        and OPTIMIZATION_AGENT not in results
    ):
        needed.append(OPTIMIZATION_AGENT)
    if (
        plan.analysis_type == "portfolio_risk"
        and _high_concentration(results.get(RISK_AGENT))
        and _contains_any(text, FOLLOW_UP_OPTIMIZER_TERMS)
        and OPTIMIZATION_AGENT not in results
        and specialist_extras.get("portfolio") is not None
    ):
        needed.append(OPTIMIZATION_AGENT)
    return [
        name
        for name in _order_agents(needed)
        if name in specialists and name not in results
    ]


def _high_concentration(output: AgentOutput | None) -> bool:
    if output is None or output.status != "succeeded":
        return False
    metrics = output.extras.get("risk_metrics") if output.extras else None
    if not isinstance(metrics, dict):
        return False
    label = str(metrics.get("concentration") or "").lower()
    return label in HIGH_CONCENTRATION


def _merge_evidence(
    runtime: AgentRuntime, results: Mapping[str, AgentOutput]
) -> list[Evidence]:
    for output in results.values():
        runtime.evidence.extend(output.evidence)
    manager_source = DataSourceMetadata(
        provider="portfolio-manager",
        source="manager-orchestration",
        timestamp=datetime.now(tz=UTC),
    )
    runtime.evidence.add(
        Evidence(
            source=manager_source,
            field="trade_execution",
            value="not_implemented",
        )
    )
    return runtime.evidence.items()


def _result_used(output: AgentOutput) -> AgentResultUsed:
    return AgentResultUsed(
        agent=output.agent,
        role=output.role,
        status=output.status,
        summary=output.summary,
        findings=list(output.findings),
    )


def _assumptions(
    plan: _Plan,
    specialist_extras: Mapping[str, Any],
    used_synthetic: bool,
    portfolio: Portfolio | None,
) -> list[str]:
    notes: list[str] = [
        "Specialist outputs are the only analytical inputs; missing fields were not estimated.",
        "The manager does not retrieve market or fundamental data independently.",
        "Trade execution is not implemented.",
    ]
    if used_synthetic:
        notes.append(
            "Risk analysis used a synthetic unit-weight portfolio because no uploaded "
            "portfolio was provided."
        )
    if portfolio is not None:
        notes.append("Holdings come from the confirmed uploaded portfolio.")
    if plan.analysis_type == "portfolio_rebalancing":
        notes.append(
            "Any optimizer sleeve is a candidate allocation, not an executed rebalance."
        )
    return notes


def _limitations(
    plan: _Plan,
    results: Mapping[str, AgentOutput],
    missing: Sequence[str],
    used_synthetic: bool,
    specialist_extras: Mapping[str, Any],
) -> list[str]:
    notes: list[str] = []
    if missing:
        notes.append("Some specialist inputs or outputs were incomplete.")
    failed = [
        name for name, output in results.items() if output.status == "failed"
    ]
    if failed:
        notes.append("Failed specialists: " + ", ".join(failed) + ".")
    skipped = [name for name in plan.requested_agents if name not in results]
    if skipped:
        notes.append("Specialists not invoked: " + ", ".join(skipped) + ".")
    if used_synthetic:
        notes.append(
            "Single-name risk is based on a synthetic unit portfolio, not uploaded holdings."
        )
    if specialist_extras.get("portfolio") is None and OPTIMIZATION_AGENT in plan.requested_agents:
        notes.append("Portfolio optimization was not run without uploaded holdings.")
    notes.append("No trades were executed.")
    return notes


def _build_extras(
    *,
    plan: _Plan,
    follow_up: Sequence[str],
    used: Sequence[AgentResultUsed],
    synthesis: ManagerSynthesis,
    missing: Sequence[str],
    conflicts: Sequence[str],
    assumptions: Sequence[str],
    python_limitations: Sequence[str],
    delegation: Sequence[DelegationEvent],
    used_synthetic: bool,
) -> ManagerAgentExtras:
    risks = _unique([*synthesis.risks, *conflicts])
    assumptions_out = _unique([*assumptions, *synthesis.assumptions])
    limitations = _unique([*python_limitations, *synthesis.limitations])
    if missing and not any("unavailable" in item.lower() or "not invoke" in item.lower() for item in limitations):
        limitations.append("Missing information was left unresolved rather than estimated.")
    return ManagerAgentExtras(
        analysis_type=plan.analysis_type,
        requested_agents=list(plan.requested_agents),
        invoked_agents=[event.agent for event in delegation],
        follow_up_agents=list(follow_up),
        agent_results_used=list(used),
        summary=synthesis.summary,
        findings=list(synthesis.findings),
        recommendation=synthesis.recommendation,
        risks=risks,
        assumptions=assumptions_out,
        limitations=limitations,
        missing_information=list(missing),
        conflicts=list(conflicts),
        delegation=list(delegation),
        used_synthetic_portfolio=used_synthetic,
        analyzed_at=datetime.now(tz=UTC),
    )


def _capped_confidence(
    confidence: float,
    results: Mapping[str, AgentOutput],
    missing: Sequence[str],
    conflicts: Sequence[str],
) -> float:
    capped = confidence
    if any(output.status == "failed" for output in results.values()):
        capped = min(capped, 0.45)
    if missing:
        capped = min(capped, 0.6)
    if conflicts:
        capped = min(capped, 0.55)
    if not results:
        capped = min(capped, 0.3)
    return capped


def _routing_prompt(
    payload: AgentInput,
    heuristic_type: AnalysisType,
    has_portfolio: bool,
    symbols: Sequence[str],
) -> str:
    bundle = {
        "request_id": payload.request_id,
        "question": payload.question,
        "symbols": list(symbols),
        "has_uploaded_portfolio": has_portfolio,
        "heuristic_analysis_type": heuristic_type,
        "allowed_analysis_types": list(CANONICAL_AGENTS),
        "canonical_agents": {
            key: list(value) for key, value in CANONICAL_AGENTS.items()
        },
        "allowed_agents": list(INVOCATION_ORDER),
        "examples": {
            "stock_analysis": [MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT],
            "portfolio_risk": [RISK_AGENT, MARKET_AGENT],
            "portfolio_rebalancing": [
                MARKET_AGENT,
                FUNDAMENTAL_AGENT,
                RISK_AGENT,
                OPTIMIZATION_AGENT,
            ],
        },
        "rules": [
            "Select one analysis_type from allowed_analysis_types.",
            "required_agents must be a subset of allowed_agents.",
            "Do not include reasoning or chain-of-thought.",
        ],
    }
    return (
        "Classify this investment-analysis request and return analysis_type "
        "and required_agents.\n\n"
        + json.dumps(bundle, indent=2, default=str)
    )


def _synthesis_prompt(
    payload: AgentInput,
    plan: _Plan,
    results: Mapping[str, AgentOutput],
    missing: Sequence[str],
    conflicts: Sequence[str],
    assumptions: Sequence[str],
    limitations: Sequence[str],
) -> str:
    bundle = {
        "request_id": payload.request_id,
        "question": payload.question,
        "analysis_type": plan.analysis_type,
        "requested_agents": list(plan.requested_agents),
        "specialist_results": {
            name: _trim_specialist_output(output) for name, output in results.items()
        },
        "missing_information": list(missing),
        "conflicts": list(conflicts),
        "assumptions": list(assumptions),
        "limitations": list(limitations),
        "trade_execution": "not_implemented",
        "rules": [
            "Use only specialist results in this payload.",
            "Null fields and unavailable lists are missing. Do not fill them in.",
            "Do not cite figures that are not in this payload.",
            "Do not recommend executing trades or placing orders.",
            "Do not include chain-of-thought or hidden reasoning.",
        ],
    }
    return (
        "Synthesize the following specialist results and return summary, "
        "findings, recommendation, risks, assumptions, limitations, and "
        "confidence.\n\n"
        + json.dumps(bundle, indent=2, default=str)
    )


def _trim_specialist_output(output: AgentOutput) -> dict[str, Any]:
    extras = output.extras or {}
    keep = (
        "market_assessment",
        "trend",
        "risks",
        "key_observations",
        "fundamental_assessment",
        "strengths",
        "weaknesses",
        "financial_health",
        "profitability",
        "financial_risks",
        "overall_risk_assessment",
        "major_risks",
        "concentration_findings",
        "diversification_findings",
        "allocation_assessment",
        "comparison_findings",
        "constraint_findings",
        "manager_notes",
        "current_allocation",
        "proposed_allocation",
        "optimization_objective",
        "feasible",
        "solver_status",
        "warnings",
        "limitations",
        "unavailable",
        "weight_basis",
        "trade_execution",
    )
    trimmed_extras = {key: extras[key] for key in keep if key in extras}
    metrics = extras.get("risk_metrics")
    if isinstance(metrics, dict):
        trimmed_extras["risk_metrics"] = {
            key: value
            for key, value in metrics.items()
            if key not in {"positions", "pairwise_correlations"}
        }
    return {
        "agent": output.agent,
        "role": output.role,
        "status": output.status,
        "summary": output.summary,
        "findings": list(output.findings),
        "confidence": output.confidence,
        "error_message": output.error_message,
        "extras": trimmed_extras,
    }


def _contains_any(text: str, terms: Sequence[str]) -> bool:
    return any(term in text for term in terms)


def _unique(values: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
