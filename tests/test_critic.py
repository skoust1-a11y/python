"""Deterministic critique checks for the strategy-board reflection stage."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.contracts import AgentOutput
from app.agents.manager import (
    FUNDAMENTAL_AGENT,
    MARKET_AGENT,
    OPTIMIZATION_AGENT,
    RISK_AGENT,
    _Plan,
)
from app.models.common import DataSourceMetadata, Evidence
from app.workflow.critic import (
    MAX_REFLECTION_CYCLES,
    CritiqueFinding,
    evaluate_critique,
    needs_critique,
    reanalysis_agents,
)
from app.workflow.state import (
    FundamentalDataSnapshot,
    InvestmentProfile,
    MarketDataSnapshot,
    OptimizationResultSnapshot,
    RiskAnalysisSnapshot,
    SelectedStock,
    UserRequest,
    create_investment_state,
)

UTC = timezone.utc
STARTED = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def _evidence(agent: str) -> Evidence:
    return Evidence(
        source=DataSourceMetadata(
            provider="unit-test",
            source=agent,
            timestamp=STARTED,
        ),
        symbol="AAPL",
        field="summary",
        value=agent,
    )


def _output(
    name: str,
    *,
    status: str = "succeeded",
    findings: list[str] | None = None,
    extras: dict | None = None,
    with_evidence: bool = True,
    error_message: str | None = None,
) -> AgentOutput:
    return AgentOutput(
        agent=name,
        role=name,
        status=status,  # type: ignore[arg-type]
        summary=f"{name} summary",
        findings=findings or ([f"{name} finding"] if status == "succeeded" else []),
        evidence=[_evidence(name)] if with_evidence and status == "succeeded" else [],
        duration_ms=1.0,
        error_message=error_message,
        extras=extras or {},
    )


def _state(**kwargs):
    state = create_investment_state(
        "crit-1",
        user_request=UserRequest(text="Analyze AAPL", symbols=["AAPL"]),
        selected_stock=SelectedStock(symbol="AAPL"),
        investment_profile=kwargs.pop("investment_profile", None),
    )
    state.update(kwargs)
    return state


def _plan() -> _Plan:
    return _Plan("stock_analysis", [MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT])


def _complete_outputs() -> dict[str, AgentOutput]:
    return {
        MARKET_AGENT: _output(MARKET_AGENT, extras={"trend": "uptrend", "unavailable": []}),
        FUNDAMENTAL_AGENT: _output(
            FUNDAMENTAL_AGENT, extras={"financial_health": "healthy", "unavailable": []}
        ),
        RISK_AGENT: _output(
            RISK_AGENT,
            extras={"unavailable": [], "overall_risk_assessment": "Moderate"},
        ),
    }


def test_no_critique_when_evidence_and_agents_agree() -> None:
    findings = evaluate_critique(
        _state(),
        plan=_plan(),
        outputs=_complete_outputs(),
        missing=[],
        started_at=STARTED,
    )
    assert findings == []
    assert needs_critique(findings) is False
    assert reanalysis_agents(findings, reflection_cycle=0, has_portfolio=True) == []


def test_missing_and_unsupported_evidence() -> None:
    outputs = _complete_outputs()
    outputs[MARKET_AGENT] = _output(
        MARKET_AGENT,
        extras={"trend": "uptrend", "unavailable": []},
        with_evidence=False,
    )
    findings = evaluate_critique(
        _state(),
        plan=_plan(),
        outputs=outputs,
        missing=[],
        started_at=STARTED,
    )
    categories = {item.category for item in findings}
    assert "missing_evidence" in categories
    assert "unsupported_recommendation" in categories
    assert reanalysis_agents(findings, reflection_cycle=0, has_portfolio=True) == [
        MARKET_AGENT
    ]


def test_agent_disagreement_does_not_retry() -> None:
    outputs = _complete_outputs()
    outputs[MARKET_AGENT] = _output(
        MARKET_AGENT, extras={"trend": "uptrend", "unavailable": []}
    )
    outputs[FUNDAMENTAL_AGENT] = _output(
        FUNDAMENTAL_AGENT, extras={"financial_health": "stressed", "unavailable": []}
    )
    findings = evaluate_critique(
        _state(),
        plan=_plan(),
        outputs=outputs,
        missing=[],
        started_at=STARTED,
    )
    assert any(item.category == "agent_disagreement" for item in findings)
    assert all(item.severity == "warning" for item in findings)
    assert reanalysis_agents(findings, reflection_cycle=0, has_portfolio=True) == []


def test_missing_analysis_from_failed_agent_is_retryable() -> None:
    outputs = _complete_outputs()
    outputs[MARKET_AGENT] = _output(
        MARKET_AGENT,
        status="failed",
        with_evidence=False,
        error_message="quote feed down",
    )
    findings = evaluate_critique(
        _state(),
        plan=_plan(),
        outputs=outputs,
        missing=["market-analysis did not complete: quote feed down"],
        started_at=STARTED,
    )
    assert any(item.category == "missing_analysis" for item in findings)
    assert reanalysis_agents(findings, reflection_cycle=0, has_portfolio=True) == [
        MARKET_AGENT
    ]


def test_stale_and_unavailable_data() -> None:
    outputs = _complete_outputs()
    outputs[MARKET_AGENT] = _output(
        MARKET_AGENT, extras={"trend": "uptrend", "unavailable": ["quote"]}
    )
    stale_as_of = STARTED - timedelta(days=10)
    state = _state(
        market_data={
            "AAPL": MarketDataSnapshot(symbol="AAPL", current_price=190.0, as_of=stale_as_of)
        }
    )
    findings = evaluate_critique(
        state,
        plan=_plan(),
        outputs=outputs,
        missing=[],
        started_at=STARTED,
    )
    stale = [item for item in findings if item.category == "stale_or_unavailable_data"]
    assert stale
    assert reanalysis_agents(findings, reflection_cycle=0, has_portfolio=True) == [
        MARKET_AGENT
    ]


def test_lagged_filings_are_not_treated_as_stale_market_data() -> None:
    outputs = _complete_outputs()
    filing_as_of = STARTED - timedelta(days=90)
    state = _state(
        fundamental_data={
            "AAPL": FundamentalDataSnapshot(
                symbol="AAPL",
                revenue=100.0,
                as_of_kind="latest_reported",
                as_of=filing_as_of,
                reporting_period="annual FY2025",
            )
        }
    )
    findings = evaluate_critique(
        state,
        plan=_plan(),
        outputs=outputs,
        missing=[],
        started_at=STARTED,
    )
    stale = [item for item in findings if item.category == "stale_or_unavailable_data"]
    assert stale == []


def test_constraint_violation_against_risk_profile() -> None:
    outputs = _complete_outputs()
    outputs[RISK_AGENT] = _output(
        RISK_AGENT,
        extras={"unavailable": [], "overall_risk_assessment": "High concentration"},
    )
    state = _state(
        investment_profile=InvestmentProfile(
            risk_tolerance="conservative",
            constraints=["No AAPL"],
        ),
        risk_analysis=RiskAnalysisSnapshot(
            overall_risk_assessment="High concentration",
            concentration="high",
        ),
        optimization_results=OptimizationResultSnapshot(
            proposed_allocation={"AAPL": 1.0},
            feasible=True,
        ),
    )
    findings = evaluate_critique(
        state,
        plan=_Plan(
            "portfolio_rebalancing",
            [MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT, OPTIMIZATION_AGENT],
        ),
        outputs=outputs,
        missing=[],
        started_at=STARTED,
    )
    categories = {item.category for item in findings}
    assert "constraint_violation" in categories
    agents = reanalysis_agents(findings, reflection_cycle=0, has_portfolio=True)
    assert RISK_AGENT in agents


def test_reanalysis_is_capped_after_one_cycle() -> None:
    finding = CritiqueFinding(
        category="missing_evidence",
        severity="critical",
        message="Required evidence from market-analysis is missing.",
        agents=[MARKET_AGENT],
        target=MARKET_AGENT,
        retryable=True,
    )
    assert reanalysis_agents(
        [finding], reflection_cycle=MAX_REFLECTION_CYCLES, has_portfolio=True
    ) == []


def test_critique_finding_has_no_hidden_reasoning_fields() -> None:
    dumped = CritiqueFinding(
        category="agent_disagreement",
        severity="warning",
        message="Agents disagree.",
        agents=[MARKET_AGENT],
    ).model_dump(mode="json")
    assert "reasoning" not in dumped
    assert "chain_of_thought" not in dumped
    assert "scratchpad" not in dumped
