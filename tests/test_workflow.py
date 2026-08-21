"""Compiled LangGraph investment strategy workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.base import Agent, AgentContext, AgentMetadata
from app.agents.contracts import AgentAnalysis, AgentInput
from app.agents.manager import (
    FUNDAMENTAL_AGENT,
    MARKET_AGENT,
    OPTIMIZATION_AGENT,
    RISK_AGENT,
)
from app.exceptions import AgentError, ProviderError
from app.models.common import DataSourceMetadata, Evidence
from app.models.portfolio import Holding, Portfolio, SymbolValidation
from app.providers.contracts import LLMProvider, TModel
from app.providers.registry import ProviderBundle, build_providers
from app.workflow.graph import build_strategy_graph, invoke_strategy_board
from app.workflow.nodes import (
    CRITIQUE as CRITIQUE_NODE,
    FUNDAMENTAL,
    MARKET,
    OPTIMIZE,
    REANALYZE,
    RISK,
    SYNTHESIZE,
)
from app.workflow.state import UserRequest, create_investment_state
from tests.helpers import make_settings

UTC = timezone.utc
IMPORTED_AT = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)

SYNTHESIS = {
    "summary": "Hold with elevated single-name risk.",
    "findings": ["Market trend is constructive.", "Fundamentals are mixed."],
    "recommendation": "Hold the name and monitor concentration. Do not place trades.",
    "risks": ["A reversal would pressure the position."],
    "assumptions": ["Specialist figures were not re-estimated."],
    "limitations": ["Interpretation is limited to specialist output."],
    "confidence": 0.7,
}

CRITIQUE_PAYLOAD = {
    "message": "Reconcile the uptrend against stressed financial health.",
    "target": "final-recommendation",
}


class _FakeLLM(LLMProvider):
    def __init__(
        self,
        *,
        by_model: dict[str, dict[str, Any]] | None = None,
        routing_error: Exception | None = None,
        synthesis_error: Exception | None = None,
    ) -> None:
        self._by_model = by_model or {}
        self._routing_error = routing_error
        self._synthesis_error = synthesis_error
        self.complete_calls: list[dict[str, Any]] = []
        self.structured_calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "fake-llm"

    @property
    def model(self) -> str:
        return "fake-workflow-model"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        self.complete_calls.append(
            {"prompt": prompt, "system": system, "metadata": metadata}
        )
        raise AssertionError(
            "Workflow must not use free-form complete() for numbers or hidden reasoning."
        )

    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        self.structured_calls.append(
            {
                "prompt": prompt,
                "system": system,
                "metadata": metadata,
                "model": response_model.__name__,
            }
        )
        name = response_model.__name__
        if name == "ManagerRouting" and self._routing_error is not None:
            raise self._routing_error
        if name == "ManagerSynthesis" and self._synthesis_error is not None:
            raise self._synthesis_error
        payload = self._by_model.get(name, _default_payload(name))
        return response_model.model_validate(payload)


def _default_payload(name: str) -> dict[str, Any]:
    if name == "ManagerRouting":
        return {
            "analysis_type": "stock_analysis",
            "required_agents": [MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT],
        }
    if name == "WorkflowCritique":
        return dict(CRITIQUE_PAYLOAD)
    return dict(SYNTHESIS)


class _RecordingAgent(Agent):
    def __init__(
        self,
        name: str,
        role: str,
        *,
        extras: dict[str, Any] | None = None,
        fail: str | None = None,
        findings: list[str] | None = None,
        include_evidence: bool = True,
    ) -> None:
        self._metadata = AgentMetadata(
            name=name, role=role, description=f"{name} test double"
        )
        self.calls: list[AgentInput] = []
        self._extras = extras or {}
        self._fail = fail
        self._findings = findings or [f"{name} finding"]
        self._include_evidence = include_evidence

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def analyze(self, payload: AgentInput, runtime: Any) -> AgentAnalysis:
        self.calls.append(payload)
        if self._fail:
            raise AgentError(self._fail)
        symbol = payload.symbols[0] if payload.symbols else None
        if self._include_evidence:
            runtime.evidence.add(
                Evidence(
                    source=DataSourceMetadata(
                        provider="unit-test",
                        source=self.name,
                        timestamp=IMPORTED_AT,
                    ),
                    symbol=symbol,
                    field="summary",
                    value=self.name,
                )
            )
        return AgentAnalysis(
            summary=f"{self.name} summary",
            findings=list(self._findings),
            extras=dict(self._extras),
        )


def _specialists(
    *,
    extras: dict[str, dict[str, Any]] | None = None,
    fail: dict[str, str] | None = None,
    evidence: dict[str, bool] | None = None,
) -> dict[str, _RecordingAgent]:
    extras = extras or {}
    fail = fail or {}
    evidence = evidence or {}
    return {
        MARKET_AGENT: _RecordingAgent(
            MARKET_AGENT,
            "market-analyst",
            extras=extras.get(MARKET_AGENT, {"trend": "uptrend", "unavailable": []}),
            fail=fail.get(MARKET_AGENT),
            include_evidence=evidence.get(MARKET_AGENT, True),
        ),
        FUNDAMENTAL_AGENT: _RecordingAgent(
            FUNDAMENTAL_AGENT,
            "fundamental-analyst",
            extras=extras.get(
                FUNDAMENTAL_AGENT, {"financial_health": "healthy", "unavailable": []}
            ),
            fail=fail.get(FUNDAMENTAL_AGENT),
            include_evidence=evidence.get(FUNDAMENTAL_AGENT, True),
        ),
        RISK_AGENT: _RecordingAgent(
            RISK_AGENT,
            "risk-analyst",
            extras=extras.get(
                RISK_AGENT,
                {
                    "unavailable": [],
                    "overall_risk_assessment": "Moderate concentration",
                    "risk_metrics": {"concentration": "moderate", "hhi": 0.31},
                },
            ),
            fail=fail.get(RISK_AGENT),
            include_evidence=evidence.get(RISK_AGENT, True),
        ),
        OPTIMIZATION_AGENT: _RecordingAgent(
            OPTIMIZATION_AGENT,
            "portfolio-optimizer",
            extras=extras.get(
                OPTIMIZATION_AGENT,
                {
                    "feasible": True,
                    "trade_execution": "not_implemented",
                    "unavailable": [],
                    "optimization_objective": "minimum_volatility",
                    "current_allocation": {"AAPL": 0.5, "MSFT": 0.5},
                    "proposed_allocation": {"AAPL": 0.4, "MSFT": 0.6},
                },
            ),
            fail=fail.get(OPTIMIZATION_AGENT),
            include_evidence=evidence.get(OPTIMIZATION_AGENT, True),
        ),
    }


def _holding(symbol: str, quantity: float = 10.0) -> Holding:
    return Holding(
        symbol=symbol,
        quantity=quantity,
        average_cost=100.0,
        currency="USD",
        symbol_validation=SymbolValidation(
            input=symbol, normalized=symbol.upper(), status="valid"
        ),
    )


def _portfolio(*symbols: str) -> Portfolio:
    return Portfolio(
        id="pf-workflow",
        holdings=[_holding(symbol) for symbol in symbols],
        base_currency="USD",
        source_filename="holdings.csv",
        source_format="csv",
        imported_at=IMPORTED_AT,
    )


def _context(
    llm: LLMProvider | None = None,
    specialists: dict[str, Agent] | None = None,
    extras: dict[str, Any] | None = None,
) -> AgentContext:
    bundle = build_providers(make_settings())
    if llm is not None:
        bundle = ProviderBundle(
            llm=llm,
            market_data=bundle.market_data,
            fundamentals=bundle.fundamentals,
            news=bundle.news,
        )
    payload = dict(extras or {})
    if specialists is not None:
        payload["specialists"] = specialists
    return AgentContext(providers=bundle, extras=payload or None)


def _invoked(specialists: dict[str, _RecordingAgent]) -> list[str]:
    return [name for name, agent in specialists.items() if agent.calls]


def _run(
    *,
    text: str,
    symbols: list[str] | None = None,
    analysis_type: str | None = None,
    portfolio: Portfolio | None = None,
    investment_profile: Any | None = None,
    specialists: dict[str, _RecordingAgent] | None = None,
    llm: LLMProvider | None = None,
    extras: dict[str, Any] | None = None,
):
    agents = specialists or _specialists()
    request = UserRequest(
        text=text,
        symbols=symbols or [],
        analysis_type=analysis_type,  # type: ignore[arg-type]
        portfolio_id=portfolio.id if portfolio is not None else None,
    )
    state = create_investment_state(
        "wf-1",
        user_request=request,
        portfolio=portfolio,
        investment_profile=investment_profile,
    )
    result = invoke_strategy_board(
        state,
        _context(llm or _FakeLLM(), agents, extras),
        specialists=agents,
    )
    return result, agents


def test_graph_compiles_with_one_reflection_cycle_and_no_infinite_loop() -> None:
    specialists = _specialists()
    graph = build_strategy_graph(_context(_FakeLLM(), specialists), specialists=specialists)
    names = set(graph.nodes)
    for node in (MARKET, FUNDAMENTAL, RISK, OPTIMIZE, CRITIQUE_NODE, REANALYZE, SYNTHESIZE, "plan"):
        assert node in names
    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}
    assert (CRITIQUE_NODE, SYNTHESIZE) in edges
    assert (CRITIQUE_NODE, REANALYZE) in edges
    assert (CRITIQUE_NODE, MARKET) not in edges
    assert (SYNTHESIZE, MARKET) not in edges
    assert (SYNTHESIZE, "plan") not in edges
    assert (SYNTHESIZE, REANALYZE) not in edges
    assert (REANALYZE, SYNTHESIZE) not in edges


def test_stock_analysis_runs_market_fundamental_and_risk_in_planned_order() -> None:
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["aapl"],
        analysis_type="stock_analysis",
    )

    assert _invoked(specialists) == [MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT]
    assert not specialists[OPTIMIZATION_AGENT].calls
    assert result["user_request"].analysis_type == "stock_analysis"
    assert result["execution"].requested_agents == [
        MARKET_AGENT,
        FUNDAMENTAL_AGENT,
        RISK_AGENT,
    ]
    assert set(result["execution"].invoked_agents) == {
        MARKET_AGENT,
        FUNDAMENTAL_AGENT,
        RISK_AGENT,
    }
    assert result["execution"].invoked_agents[-1] == RISK_AGENT
    assert result["execution"].status == "completed"
    assert result["execution"].current_node == SYNTHESIZE
    assert result["execution"].duration_ms is not None
    assert result["final_recommendation"] is not None
    assert result["final_recommendation"].trade_execution == "not_implemented"
    assert result["selected_stock"] is not None
    assert result["selected_stock"].symbol == "AAPL"
    assert specialists[RISK_AGENT].calls[0].extras["synthetic_portfolio"] is True


def test_market_and_fundamental_do_not_wait_on_each_other() -> None:
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["AAPL"],
        analysis_type="stock_analysis",
    )
    del result
    market_extras = specialists[MARKET_AGENT].calls[0].extras
    fundamental_extras = specialists[FUNDAMENTAL_AGENT].calls[0].extras
    assert FUNDAMENTAL_AGENT not in market_extras
    assert MARKET_AGENT not in fundamental_extras
    risk_extras = specialists[RISK_AGENT].calls[0].extras
    assert MARKET_AGENT in risk_extras
    assert FUNDAMENTAL_AGENT in risk_extras


def test_portfolio_risk_skips_fundamental_and_optimizer() -> None:
    result, specialists = _run(
        text="How concentrated is my portfolio risk?",
        analysis_type="portfolio_risk",
        portfolio=_portfolio("AAPL", "MSFT"),
    )

    assert _invoked(specialists) == [MARKET_AGENT, RISK_AGENT]
    assert not specialists[FUNDAMENTAL_AGENT].calls
    assert not specialists[OPTIMIZATION_AGENT].calls
    assert result["user_request"].analysis_type == "portfolio_risk"
    assert specialists[RISK_AGENT].calls[0].extras[MARKET_AGENT]["status"] == "succeeded"


def test_rebalancing_invokes_all_specialists() -> None:
    result, specialists = _run(
        text="Should I rebalance my portfolio?",
        analysis_type="portfolio_rebalancing",
        portfolio=_portfolio("AAPL", "MSFT"),
    )

    assert _invoked(specialists) == [
        MARKET_AGENT,
        FUNDAMENTAL_AGENT,
        RISK_AGENT,
        OPTIMIZATION_AGENT,
    ]
    opt_payload = specialists[OPTIMIZATION_AGENT].calls[0]
    assert RISK_AGENT in opt_payload.extras
    assert FUNDAMENTAL_AGENT in opt_payload.extras
    assert result["optimization_results"] is not None
    assert result["optimization_results"].trade_execution == "not_implemented"
    assert result["risk_analysis"] is not None
    assert result["risk_analysis"].concentration == "moderate"


def test_required_agents_avoid_unnecessary_execution() -> None:
    specialists = _specialists()
    result, specialists = _run(
        text="Review market and risk only",
        symbols=["AAPL"],
        portfolio=_portfolio("AAPL"),
        specialists=specialists,
        extras={"required_agents": ["Market Agent", "Risk Agent"]},
    )

    assert _invoked(specialists) == [MARKET_AGENT, RISK_AGENT]
    assert result["execution"].requested_agents == [MARKET_AGENT, RISK_AGENT]
    assert not specialists[FUNDAMENTAL_AGENT].calls
    assert not specialists[OPTIMIZATION_AGENT].calls


def test_failed_specialist_does_not_abort_the_graph() -> None:
    specialists = _specialists(fail={MARKET_AGENT: "quote feed down"})
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["AAPL"],
        analysis_type="stock_analysis",
        specialists=specialists,
    )

    assert result["execution"].status == "completed"
    assert result["agent_results"][MARKET_AGENT].status == "failed"
    assert result["agent_results"][FUNDAMENTAL_AGENT].status == "succeeded"
    assert any("quote feed down" in item for item in result["execution"].errors)
    assert any("failed" in item.description.lower() for item in result["conflicts"])
    assert result["final_recommendation"] is not None
    assert result["final_recommendation"].confidence == 0.45
    assert specialists[RISK_AGENT].calls


def test_conflicting_views_trigger_optional_critique_once() -> None:
    llm = _FakeLLM()
    specialists = _specialists(
        extras={
            MARKET_AGENT: {"trend": "uptrend", "unavailable": []},
            FUNDAMENTAL_AGENT: {"financial_health": "stressed", "unavailable": []},
        }
    )
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["AAPL"],
        analysis_type="stock_analysis",
        specialists=specialists,
        llm=llm,
    )

    assert any("uptrend" in item.description and "stressed" in item.description for item in result["conflicts"])
    assert result["critiques"]
    structured = [item for item in result["critiques"] if item.category == "agent_disagreement"]
    assert structured
    assert structured[0].author == "portfolio-manager"
    assert structured[0].resolved is False
    dumped = structured[0].model_dump(mode="json")
    assert "reasoning" not in dumped
    assert "chain_of_thought" not in dumped
    critique_calls = [call for call in llm.structured_calls if call["model"] == "WorkflowCritique"]
    assert len(critique_calls) == 1
    assert "chain-of-thought" in (critique_calls[0]["system"] or "").lower()
    assert "structured findings" in (critique_calls[0]["prompt"] or "").lower()
    assert llm.complete_calls == []
    assert _invoked(specialists).count(MARKET_AGENT) == 1
    assert len(specialists[MARKET_AGENT].calls) == 1
    assert result["execution"].current_node == SYNTHESIZE
    assert (result["execution"].reflection_cycle or 0) == 0


def test_critique_is_skipped_when_specialists_agree() -> None:
    llm = _FakeLLM()
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["AAPL"],
        analysis_type="stock_analysis",
        llm=llm,
    )
    del specialists
    assert result["conflicts"] == []
    assert result["critiques"] == []
    assert [call["model"] for call in llm.structured_calls if call["model"] == "WorkflowCritique"] == []
    assert (result["execution"].reflection_cycle or 0) == 0


def test_critical_critique_triggers_one_reanalysis_cycle() -> None:
    llm = _FakeLLM()
    specialists = _specialists(evidence={MARKET_AGENT: False})
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["AAPL"],
        analysis_type="stock_analysis",
        specialists=specialists,
        llm=llm,
    )

    assert len(specialists[MARKET_AGENT].calls) == 2
    assert len(specialists[FUNDAMENTAL_AGENT].calls) == 1
    assert result["execution"].reflection_cycle == 1
    categories = {item.category for item in result["critiques"]}
    assert "missing_evidence" in categories
    assert "unsupported_recommendation" in categories
    critique_calls = [call for call in llm.structured_calls if call["model"] == "WorkflowCritique"]
    assert 1 <= len(critique_calls) <= 2
    assert llm.complete_calls == []
    assert result["execution"].current_node == SYNTHESIZE
    assert specialists[MARKET_AGENT].calls[1].extras.get("reflection_cycle") == 1


def test_unresolved_conflict_after_reanalysis_does_not_loop() -> None:
    llm = _FakeLLM()
    specialists = _specialists(evidence={MARKET_AGENT: False})
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["AAPL"],
        analysis_type="stock_analysis",
        specialists=specialists,
        llm=llm,
    )

    assert len(specialists[MARKET_AGENT].calls) == 2
    unresolved = [
        item
        for item in result["critiques"]
        if item.category in {"missing_evidence", "unsupported_recommendation"}
        and item.resolved is False
    ]
    assert unresolved
    assert result["final_recommendation"] is not None
    assert any(
        "evidence" in item.lower()
        for item in result["final_recommendation"].risks
        + result["final_recommendation"].limitations
    )
    critique_calls = [call for call in llm.structured_calls if call["model"] == "WorkflowCritique"]
    assert len(critique_calls) == 2
    assert result["execution"].reflection_cycle == 1
    assert result["execution"].current_node == SYNTHESIZE


def test_missing_portfolio_skips_optimizer() -> None:
    result, specialists = _run(
        text="Should I rebalance AAPL?",
        symbols=["AAPL"],
        analysis_type="portfolio_rebalancing",
    )

    assert OPTIMIZATION_AGENT not in _invoked(specialists)
    assert RISK_AGENT not in _invoked(specialists)
    assert any("portfolio" in item.lower() for item in result["execution"].errors)
    assert result["final_recommendation"] is not None
    assert any("not invoked" in item.lower() or "optimization" in item.lower() for item in result["final_recommendation"].limitations)


def test_missing_user_inputs_return_structured_failure() -> None:
    llm = _FakeLLM()
    state = create_investment_state(
        "wf-empty",
        user_request=UserRequest(text="What should I do?"),
    )
    result = invoke_strategy_board(state, _context(llm, _specialists()), specialists=_specialists())
    assert result["execution"].status == "failed"
    assert result["final_recommendation"] is not None
    assert result["final_recommendation"].trade_execution == "not_implemented"
    assert llm.complete_calls == []
    assert not any(call["model"] == "ManagerSynthesis" for call in llm.structured_calls)


def test_llm_routing_is_used_when_analysis_type_is_unset() -> None:
    specialists = _specialists()
    llm = _FakeLLM(
        by_model={
            "ManagerRouting": {
                "analysis_type": "portfolio_risk",
                "required_agents": [RISK_AGENT, MARKET_AGENT],
            }
        }
    )
    result, specialists = _run(
        text="How risky is my book?",
        portfolio=_portfolio("AAPL", "MSFT"),
        specialists=specialists,
        llm=llm,
    )
    routing_calls = [call for call in llm.structured_calls if call["model"] == "ManagerRouting"]
    assert len(routing_calls) == 1
    assert "chain-of-thought" in (routing_calls[0]["system"] or "").lower()
    assert result["user_request"].analysis_type == "portfolio_risk"
    assert _invoked(specialists) == [MARKET_AGENT, RISK_AGENT]


def test_routing_failure_falls_back_to_heuristic() -> None:
    specialists = _specialists()
    llm = _FakeLLM(routing_error=ProviderError("router unavailable"))
    result, specialists = _run(
        text="Should I rebalance my portfolio?",
        portfolio=_portfolio("AAPL", "MSFT"),
        specialists=specialists,
        llm=llm,
    )
    assert result["user_request"].analysis_type == "portfolio_rebalancing"
    assert OPTIMIZATION_AGENT in _invoked(specialists)


def test_synthesis_is_structured_and_does_not_expose_chain_of_thought() -> None:
    llm = _FakeLLM()
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["AAPL"],
        analysis_type="stock_analysis",
        llm=llm,
    )
    recommendation = result["final_recommendation"]
    assert recommendation is not None
    dumped = recommendation.model_dump(mode="json")
    assert "reasoning" not in dumped
    assert "chain_of_thought" not in dumped
    assert dumped["trade_execution"] == "not_implemented"
    assert result["agent_results"]["portfolio-manager"].summary == SYNTHESIS["summary"]
    synthesis_calls = [call for call in llm.structured_calls if call["model"] == "ManagerSynthesis"]
    assert len(synthesis_calls) == 1
    assert "Do not invent" in (synthesis_calls[0]["system"] or "")
    assert llm.complete_calls == []
    assert any(item.field == "trade_execution" for item in result["evidence"])
    assert specialists[MARKET_AGENT].calls


def test_synthesis_failure_still_returns_structured_output() -> None:
    llm = _FakeLLM(synthesis_error=ProviderError("synthesis unavailable"))
    result, specialists = _run(
        text="Analyze AAPL",
        symbols=["AAPL"],
        analysis_type="stock_analysis",
        llm=llm,
    )
    del specialists
    assert result["execution"].status == "completed"
    assert result["final_recommendation"] is not None
    assert result["final_recommendation"].trade_execution == "not_implemented"
    assert "Do not place trades" in result["final_recommendation"].recommendation


def test_typed_state_is_preserved_across_nodes() -> None:
    result, specialists = _run(
        text="Review my book",
        analysis_type="portfolio_review",
        portfolio=_portfolio("AAPL", "MSFT"),
    )
    del specialists
    assert result["request_id"] == "wf-1"
    assert result["portfolio"].id == "pf-workflow"
    assert result["user_request"].text == "Review my book"
    assert isinstance(result["agent_results"], dict)
    assert result["news"] == []
    assert result["execution"].llm_provider == "fake-llm"
    assert result["execution"].started_at is not None


def test_workflow_package_does_not_use_manager_analyze_or_vendor_sdks() -> None:
    text = Path("app/workflow/graph.py").read_text(encoding="utf-8") + Path(
        "app/workflow/nodes.py"
    ).read_text(encoding="utf-8")
    assert "PortfolioManagerAgent" not in text
    assert ".analyze(" not in text
    for token in ("yfinance", "openai", "groq", "google.genai", "chain_of_thought"):
        assert token not in text
    assert "complete_structured" in text
    assert "execute_agent" in text
