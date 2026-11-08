"""Deterministic critique checks for one strategy-board reflection cycle.

The critic inspects specialist output and graph snapshots. It does not invent
figures, execute trades, or return hidden chain-of-thought. Re-analysis is a
single controlled retry of flagged specialists, not autonomous self-improvement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from pydantic import Field

from app.agents.contracts import AgentOutput
from app.agents.manager import (
    FUNDAMENTAL_AGENT,
    HIGH_CONCENTRATION,
    INVOCATION_ORDER,
    MARKET_AGENT,
    OPTIMIZATION_AGENT,
    PORTFOLIO_AGENTS,
    RISK_AGENT,
    _Plan,
)
from app.models.common import DomainModel
from app.models.types import NonEmptyText
from app.workflow.state import (
    CritiqueCategory,
    CritiqueRecord,
    CritiqueSeverity,
    InvestmentProfile,
    InvestmentState,
    OptimizationResultSnapshot,
    RiskAnalysisSnapshot,
)

MAX_REFLECTION_CYCLES = 1
# Live quotes and current-market valuation older than this are flagged.
# Latest reported and historical filings are lagged by design and are not
# treated as stale market data.
STALE_MAX_AGE = timedelta(days=7)
CONSTRAINT_FORBIDS = ("no ", "not ", "exclude", "avoid", "forbid")


class CritiqueFinding(DomainModel):
    """One structured reviewer finding. No reasoning payload."""

    category: CritiqueCategory
    severity: CritiqueSeverity
    message: NonEmptyText
    agents: list[NonEmptyText] = Field(default_factory=list)
    target: str | None = None
    retryable: bool = False


def evaluate_critique(
    state: InvestmentState,
    *,
    plan: _Plan | None,
    outputs: Mapping[str, AgentOutput],
    missing: Sequence[str],
    started_at: datetime,
) -> list[CritiqueFinding]:
    """Return structured findings for the current specialist snapshot."""
    if plan is None:
        return []
    findings: list[CritiqueFinding] = []
    findings.extend(_missing_analysis_findings(plan, outputs, missing))
    findings.extend(_evidence_findings(plan, outputs))
    findings.extend(_disagreement_findings(outputs))
    findings.extend(_stale_or_unavailable_findings(outputs, state, started_at))
    findings.extend(_constraint_findings(state, outputs))
    return _unique_findings(findings)


def needs_critique(findings: Sequence[CritiqueFinding]) -> bool:
    return bool(findings)


def reanalysis_agents(
    findings: Sequence[CritiqueFinding],
    *,
    reflection_cycle: int,
    has_portfolio: bool,
) -> list[str]:
    """Specialists to retry once. Empty after the prototype cycle cap."""
    if reflection_cycle >= MAX_REFLECTION_CYCLES:
        return []
    selected: list[str] = []
    for finding in findings:
        if finding.severity != "critical" or not finding.retryable:
            continue
        for name in finding.agents:
            if name not in INVOCATION_ORDER or name in selected:
                continue
            if name in PORTFOLIO_AGENTS and not has_portfolio:
                continue
            selected.append(name)
    return [name for name in INVOCATION_ORDER if name in selected]


def records_from_findings(
    findings: Sequence[CritiqueFinding],
    *,
    previous: Sequence[CritiqueRecord] | None = None,
) -> list[CritiqueRecord]:
    """Map findings to graph records and mark disappeared issues resolved."""
    current_keys = {_record_key(finding_record(item)) for item in findings}
    records = [finding_record(item) for item in findings]
    for prior in previous or []:
        if prior.category is None:
            continue
        if _record_key(prior) in current_keys:
            continue
        records.append(prior.model_copy(update={"resolved": True}))
    return records


def finding_record(finding: CritiqueFinding) -> CritiqueRecord:
    return CritiqueRecord(
        author="portfolio-manager",
        message=finding.message,
        target=finding.target,
        category=finding.category,
        severity=finding.severity,
        resolved=False,
    )


def _missing_analysis_findings(
    plan: _Plan,
    outputs: Mapping[str, AgentOutput],
    missing: Sequence[str],
) -> list[CritiqueFinding]:
    findings: list[CritiqueFinding] = []
    for name in plan.requested_agents:
        output = outputs.get(name)
        if output is None:
            blocked = any(
                name in item and "portfolio" in item.lower() for item in missing
            )
            findings.append(
                CritiqueFinding(
                    category="missing_analysis",
                    severity="critical",
                    message=f"Required analysis from {name} is missing.",
                    agents=[name],
                    target=name,
                    retryable=not blocked,
                )
            )
            continue
        if output.status == "failed":
            findings.append(
                CritiqueFinding(
                    category="missing_analysis",
                    severity="critical",
                    message=(
                        f"Required analysis from {name} failed: "
                        f"{output.error_message or output.summary}."
                    ),
                    agents=[name],
                    target=name,
                    retryable=True,
                )
            )
    return findings


def _evidence_findings(
    plan: _Plan,
    outputs: Mapping[str, AgentOutput],
) -> list[CritiqueFinding]:
    findings: list[CritiqueFinding] = []
    for name in plan.requested_agents:
        output = outputs.get(name)
        if output is None or output.status != "succeeded":
            continue
        if output.evidence:
            continue
        findings.append(
            CritiqueFinding(
                category="missing_evidence",
                severity="critical",
                message=f"Required evidence from {name} is missing.",
                agents=[name],
                target=name,
                retryable=True,
            )
        )
        if output.findings:
            findings.append(
                CritiqueFinding(
                    category="unsupported_recommendation",
                    severity="critical",
                    message=f"{name} findings are not supported by evidence.",
                    agents=[name],
                    target=name,
                    retryable=True,
                )
            )
    return findings


def _disagreement_findings(outputs: Mapping[str, AgentOutput]) -> list[CritiqueFinding]:
    findings: list[CritiqueFinding] = []
    market = outputs.get(MARKET_AGENT)
    fundamental = outputs.get(FUNDAMENTAL_AGENT)
    trend = _extra(market, "trend")
    health = _extra(fundamental, "financial_health")
    if trend == "uptrend" and health == "stressed":
        findings.append(
            CritiqueFinding(
                category="agent_disagreement",
                severity="warning",
                message=(
                    "Market analysis reports an uptrend while fundamental "
                    "financial health is stressed."
                ),
                agents=[MARKET_AGENT, FUNDAMENTAL_AGENT],
                target="final-recommendation",
                retryable=False,
            )
        )
    if trend == "downtrend" and health == "healthy":
        findings.append(
            CritiqueFinding(
                category="agent_disagreement",
                severity="warning",
                message=(
                    "Market analysis reports a downtrend while fundamental "
                    "financial health is healthy."
                ),
                agents=[MARKET_AGENT, FUNDAMENTAL_AGENT],
                target="final-recommendation",
                retryable=False,
            )
        )
    optimization = outputs.get(OPTIMIZATION_AGENT)
    if optimization is not None and optimization.status == "succeeded":
        if _extra(optimization, "feasible") is False:
            findings.append(
                CritiqueFinding(
                    category="agent_disagreement",
                    severity="warning",
                    message=(
                        "Portfolio optimizer did not produce a feasible "
                        "candidate allocation."
                    ),
                    agents=[OPTIMIZATION_AGENT],
                    target=OPTIMIZATION_AGENT,
                    retryable=False,
                )
            )
    return findings


def _stale_or_unavailable_findings(
    outputs: Mapping[str, AgentOutput],
    state: InvestmentState,
    started_at: datetime,
) -> list[CritiqueFinding]:
    findings: list[CritiqueFinding] = []
    for name, output in outputs.items():
        if output.status != "succeeded":
            continue
        unavailable = _unavailable(output)
        if unavailable:
            findings.append(
                CritiqueFinding(
                    category="stale_or_unavailable_data",
                    severity="critical",
                    message=(
                        f"{name} reported unavailable data: "
                        + ", ".join(unavailable)
                        + "."
                    ),
                    agents=[name],
                    target=name,
                    retryable=True,
                )
            )
    findings.extend(_stale_snapshot_findings(state, started_at))
    return findings


def _stale_snapshot_findings(
    state: InvestmentState, started_at: datetime
) -> list[CritiqueFinding]:
    findings: list[CritiqueFinding] = []
    cutoff = started_at - STALE_MAX_AGE
    for snapshot in (state.get("market_data") or {}).values():
        if snapshot.as_of is None or snapshot.as_of >= cutoff:
            continue
        findings.append(
            CritiqueFinding(
                category="stale_or_unavailable_data",
                severity="critical",
                message=f"Market data for {snapshot.symbol} is stale.",
                agents=[MARKET_AGENT],
                target=MARKET_AGENT,
                retryable=True,
            )
        )
    for snapshot in (state.get("fundamental_data") or {}).values():
        if snapshot.as_of is None or snapshot.as_of >= cutoff:
            continue
        if snapshot.as_of_kind in {"latest_reported", "historical"}:
            continue
        findings.append(
            CritiqueFinding(
                category="stale_or_unavailable_data",
                severity="critical",
                message=f"Fundamental data for {snapshot.symbol} is stale.",
                agents=[FUNDAMENTAL_AGENT],
                target=FUNDAMENTAL_AGENT,
                retryable=True,
            )
        )
    return findings


def _constraint_findings(
    state: InvestmentState, outputs: Mapping[str, AgentOutput]
) -> list[CritiqueFinding]:
    findings: list[CritiqueFinding] = []
    profile = state.get("investment_profile")
    risk = state.get("risk_analysis")
    optimization = state.get("optimization_results")
    if isinstance(profile, InvestmentProfile) and isinstance(risk, RiskAnalysisSnapshot):
        concentration = (risk.concentration or "").lower()
        if profile.risk_tolerance == "conservative" and concentration in HIGH_CONCENTRATION:
            findings.append(
                CritiqueFinding(
                    category="constraint_violation",
                    severity="critical",
                    message=(
                        "Recommendation violates the conservative risk-tolerance "
                        "constraint because portfolio concentration is "
                        f"{concentration}."
                    ),
                    agents=[RISK_AGENT],
                    target=RISK_AGENT,
                    retryable=True,
                )
            )
    if isinstance(optimization, OptimizationResultSnapshot) and optimization.feasible is False:
        findings.append(
            CritiqueFinding(
                category="constraint_violation",
                severity="critical",
                message="Proposed allocation is infeasible under known constraints.",
                agents=[OPTIMIZATION_AGENT],
                target=OPTIMIZATION_AGENT,
                retryable=True,
            )
        )
    findings.extend(_profile_constraint_findings(state, profile, optimization))
    if OPTIMIZATION_AGENT in outputs and outputs[OPTIMIZATION_AGENT].status == "succeeded":
        extras = outputs[OPTIMIZATION_AGENT].extras or {}
        if extras.get("feasible") is False and not any(
            item.category == "constraint_violation" and OPTIMIZATION_AGENT in item.agents
            for item in findings
        ):
            findings.append(
                CritiqueFinding(
                    category="constraint_violation",
                    severity="critical",
                    message="Proposed allocation is infeasible under known constraints.",
                    agents=[OPTIMIZATION_AGENT],
                    target=OPTIMIZATION_AGENT,
                    retryable=True,
                )
            )
    return findings


def _profile_constraint_findings(
    state: InvestmentState,
    profile: InvestmentProfile | None,
    optimization: OptimizationResultSnapshot | None,
) -> list[CritiqueFinding]:
    if profile is None or not profile.constraints:
        return []
    symbols = _known_symbols(state, optimization)
    if not symbols:
        return []
    findings: list[CritiqueFinding] = []
    for constraint in profile.constraints:
        lowered = constraint.lower()
        if not any(token in lowered for token in CONSTRAINT_FORBIDS):
            continue
        for symbol in symbols:
            if symbol.lower() not in lowered:
                continue
            findings.append(
                CritiqueFinding(
                    category="constraint_violation",
                    severity="critical",
                    message=(
                        f"Recommendation includes {symbol}, which violates "
                        f"the portfolio constraint '{constraint}'."
                    ),
                    agents=[OPTIMIZATION_AGENT] if optimization else [MARKET_AGENT],
                    target="final-recommendation",
                    retryable=bool(optimization),
                )
            )
    return findings


def _known_symbols(
    state: InvestmentState, optimization: OptimizationResultSnapshot | None
) -> list[str]:
    symbols: list[str] = []
    selected = state.get("selected_stock")
    if selected is not None:
        symbols.append(selected.symbol)
    portfolio = state.get("portfolio")
    if portfolio is not None:
        symbols.extend(holding.symbol for holding in portfolio.holdings)
    if optimization is not None:
        symbols.extend(optimization.proposed_allocation)
    seen: list[str] = []
    for symbol in symbols:
        if symbol and symbol not in seen:
            seen.append(symbol)
    return seen


def _unavailable(output: AgentOutput) -> list[str]:
    raw = (output.extras or {}).get("unavailable")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _extra(output: AgentOutput | None, key: str) -> Any:
    if output is None:
        return None
    return (output.extras or {}).get(key)


def _unique_findings(findings: Sequence[CritiqueFinding]) -> list[CritiqueFinding]:
    unique: list[CritiqueFinding] = []
    seen: set[tuple[Any, ...]] = set()
    for item in findings:
        key = (item.category, item.target, item.message, tuple(item.agents))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _record_key(record: CritiqueRecord) -> tuple[Any, ...]:
    return (record.author, record.target, record.category, record.message)
