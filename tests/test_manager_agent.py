"""Unit tests for the Portfolio Manager Agent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.base import Agent, AgentContext, AgentMetadata
from app.agents.contracts import AgentAnalysis, AgentInput
from app.agents.execution import execute_agent
from app.agents.manager import (
    FUNDAMENTAL_AGENT,
    MARKET_AGENT,
    OPTIMIZATION_AGENT,
    RISK_AGENT,
    ManagerSynthesis,
    PortfolioManagerAgent,
)
from app.exceptions import AgentError, ProviderError
from app.models.common import DataSourceMetadata, Evidence
from app.models.portfolio import Holding, Portfolio, SymbolValidation
from app.providers.contracts import LLMProvider, TModel
from app.providers.registry import ProviderBundle, build_providers
from app.workflow.state import BoardState
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


class _FakeLLM(LLMProvider):
    def __init__(
        self,
        *,
        by_model: dict[str, dict[str, Any]] | None = None,
        routing_error: Exception | None = None,
    ) -> None:
        self._by_model = by_model or {}
        self._routing_error = routing_error
        self.complete_calls: list[dict[str, Any]] = []
        self.structured_calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "fake-llm"

    @property
    def model(self) -> str:
        return "fake-manager-model"

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
            "Portfolio manager must not use free-form complete() for numbers or hidden reasoning."
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
        if response_model.__name__ == "ManagerRouting" and self._routing_error is not None:
            raise self._routing_error
        payload = self._by_model.get(response_model.__name__, _default_payload(response_model.__name__))
        return response_model.model_validate(payload)


def _default_payload(name: str) -> dict[str, Any]:
    if name == "ManagerRouting":
        return {
            "analysis_type": "stock_analysis",
            "required_agents": [MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT],
        }
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
    ) -> None:
        self._metadata = AgentMetadata(
            name=name, role=role, description=f"{name} test double"
        )
        self.calls: list[AgentInput] = []
        self._extras = extras or {}
        self._fail = fail
        self._findings = findings or [f"{name} finding"]

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def analyze(self, payload: AgentInput, runtime: Any) -> AgentAnalysis:
        self.calls.append(payload)
        if self._fail:
            raise AgentError(self._fail)
        symbol = payload.symbols[0] if payload.symbols else None
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
) -> dict[str, _RecordingAgent]:
    extras = extras or {}
    fail = fail or {}
    return {
        MARKET_AGENT: _RecordingAgent(
            MARKET_AGENT,
            "market-analyst",
            extras=extras.get(MARKET_AGENT, {"trend": "uptrend", "unavailable": []}),
            fail=fail.get(MARKET_AGENT),
        ),
        FUNDAMENTAL_AGENT: _RecordingAgent(
            FUNDAMENTAL_AGENT,
            "fundamental-analyst",
            extras=extras.get(
                FUNDAMENTAL_AGENT, {"financial_health": "healthy", "unavailable": []}
            ),
            fail=fail.get(FUNDAMENTAL_AGENT),
        ),
        RISK_AGENT: _RecordingAgent(
            RISK_AGENT,
            "risk-analyst",
            extras=extras.get(
                RISK_AGENT,
                {
                    "unavailable": [],
                    "risk_metrics": {"concentration": "moderate"},
                },
            ),
            fail=fail.get(RISK_AGENT),
        ),
        OPTIMIZATION_AGENT: _RecordingAgent(
            OPTIMIZATION_AGENT,
            "portfolio-optimizer",
            extras=extras.get(
                OPTIMIZATION_AGENT,
                {"feasible": True, "trade_execution": "not_implemented", "unavailable": []},
            ),
            fail=fail.get(OPTIMIZATION_AGENT),
        ),
    }


def _holding(symbol: str, quantity: float = 10.0) -> Holding:
    return Holding(
        symbol=symbol,
        quantity=quantity,
        average_cost=100.0,
        currency="USD",
        symbol_validation=SymbolValidation(
            input=symbol, normalized=symbol, status="valid"
        ),
    )


def _portfolio(*symbols: str) -> Portfolio:
    return Portfolio(
        id="pf-manager",
        holdings=[_holding(symbol) for symbol in symbols],
        base_currency="USD",
        source_filename="holdings.csv",
        source_format="csv",
        imported_at=IMPORTED_AT,
    )


def _context(
    llm: LLMProvider | None = None,
    specialists: dict[str, Agent] | None = None,
) -> AgentContext:
    bundle = build_providers(make_settings())
    if llm is not None:
        bundle = ProviderBundle(
            llm=llm,
            market_data=bundle.market_data,
            fundamentals=bundle.fundamentals,
            news=bundle.news,
        )
    extras: dict[str, Any] = {}
    if specialists is not None:
        extras["specialists"] = specialists
    return AgentContext(providers=bundle, extras=extras or None)


def _payload(**overrides: Any) -> AgentInput:
    values: dict[str, Any] = {
        "request_id": "mgr-1",
        "symbols": ["aapl"],
        "question": "Should I buy AAPL?",
        "extras": {"analysis_type": "stock_analysis"},
    }
    values.update(overrides)
    return AgentInput(**values)


def _invoked(specialists: dict[str, _RecordingAgent]) -> list[str]:
    return [name for name, agent in specialists.items() if agent.calls]


def test_stock_only_question_invokes_market_fundamental_and_risk() -> None:
    specialists = _specialists()
    llm = _FakeLLM()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(),
        _context(llm, specialists),
    )

    assert output.status == "succeeded"
    assert _invoked(specialists) == [MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT]
    assert not specialists[OPTIMIZATION_AGENT].calls
    assert output.extras["analysis_type"] == "stock_analysis"
    assert output.extras["used_synthetic_portfolio"] is True
    assert specialists[RISK_AGENT].calls[0].extras["portfolio"].id == "synthetic-unit-portfolio"


def test_portfolio_risk_question_invokes_risk_and_market_only() -> None:
    specialists = _specialists()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(
            symbols=[],
            question="How concentrated is my portfolio risk?",
            extras={
                "analysis_type": "portfolio_risk",
                "portfolio": _portfolio("AAPL", "MSFT"),
            },
        ),
        _context(_FakeLLM(), specialists),
    )

    assert output.status == "succeeded"
    assert _invoked(specialists) == [MARKET_AGENT, RISK_AGENT]
    assert not specialists[FUNDAMENTAL_AGENT].calls
    assert not specialists[OPTIMIZATION_AGENT].calls
    assert output.extras["analysis_type"] == "portfolio_risk"
    assert output.extras["used_synthetic_portfolio"] is False
    assert specialists[RISK_AGENT].calls[0].extras[MARKET_AGENT]["status"] == "succeeded"


def test_portfolio_rebalancing_invokes_market_fundamental_risk_and_optimizer() -> None:
    specialists = _specialists()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(
            symbols=[],
            question="Should I rebalance my portfolio?",
            extras={
                "analysis_type": "portfolio_rebalancing",
                "portfolio": _portfolio("AAPL", "MSFT"),
            },
        ),
        _context(_FakeLLM(), specialists),
    )

    assert _invoked(specialists) == [
        MARKET_AGENT,
        FUNDAMENTAL_AGENT,
        RISK_AGENT,
        OPTIMIZATION_AGENT,
    ]
    assert output.extras["trade_execution"] == "not_implemented"
    assert output.extras["analysis_type"] == "portfolio_rebalancing"
    opt_payload = specialists[OPTIMIZATION_AGENT].calls[0]
    assert RISK_AGENT in opt_payload.extras
    assert FUNDAMENTAL_AGENT in opt_payload.extras


def test_required_agents_override_selectively_invokes_specialists() -> None:
    specialists = _specialists()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(
            extras={
                "required_agents": ["Market Agent", "Risk Agent"],
                "portfolio": _portfolio("AAPL"),
            }
        ),
        _context(_FakeLLM(), specialists),
    )

    assert _invoked(specialists) == [MARKET_AGENT, RISK_AGENT]
    assert output.extras["requested_agents"] == [MARKET_AGENT, RISK_AGENT]


def test_manager_does_not_retrieve_market_or_fundamental_data() -> None:
    specialists = _specialists()
    context = _context(_FakeLLM(), specialists)
    execute_agent(PortfolioManagerAgent(), _payload(), context)

    with pytest.raises(Exception):
        context.providers.market_data.get_quote("AAPL")
    with pytest.raises(Exception):
        context.providers.fundamentals.get_company_profile("AAPL")


def test_structured_recommendation_contains_required_fields() -> None:
    specialists = _specialists()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(),
        _context(_FakeLLM(), specialists),
    )

    extras = output.extras
    assert extras["summary"] == SYNTHESIS["summary"]
    assert extras["findings"] == SYNTHESIS["findings"]
    assert extras["recommendation"] == SYNTHESIS["recommendation"]
    assert "A reversal would pressure the position." in extras["risks"]
    assert extras["assumptions"]
    assert extras["limitations"]
    assert extras["agent_results_used"]
    used_names = [item["agent"] for item in extras["agent_results_used"]]
    assert used_names == [MARKET_AGENT, FUNDAMENTAL_AGENT, RISK_AGENT]
    assert output.summary == extras["summary"]
    assert output.findings == extras["findings"]
    assert output.evidence
    assert any(item.field == "trade_execution" for item in output.evidence)
    assert "reasoning" not in extras
    assert "chain_of_thought" not in extras
    assert extras["trade_execution"] == "not_implemented"


def test_synthesis_uses_structured_llm_and_does_not_invent_figures() -> None:
    specialists = _specialists()
    llm = _FakeLLM()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(),
        _context(llm, specialists),
    )

    assert llm.complete_calls == []
    synthesis_calls = [call for call in llm.structured_calls if call["model"] == "ManagerSynthesis"]
    assert len(synthesis_calls) == 1
    system = synthesis_calls[0]["system"] or ""
    prompt = synthesis_calls[0]["prompt"]
    assert "Do not invent" in system
    assert "chain-of-thought" in system.lower()
    assert "not a trade" in system.lower() or "not a trade" in prompt.lower()
    evidence = json.loads(prompt.split("\n\n", 1)[1])
    assert evidence["trade_execution"] == "not_implemented"
    assert MARKET_AGENT in evidence["specialist_results"]
    assert output.llm_provider == "fake-llm"


def test_llm_routing_is_used_when_analysis_type_is_not_overridden() -> None:
    specialists = _specialists()
    llm = _FakeLLM(
        by_model={
            "ManagerRouting": {
                "analysis_type": "portfolio_risk",
                "required_agents": [RISK_AGENT, MARKET_AGENT],
            }
        }
    )
    output = execute_agent(
        PortfolioManagerAgent(),
        AgentInput(
            request_id="mgr-route",
            symbols=[],
            question="How risky is my book?",
            extras={"portfolio": _portfolio("AAPL", "MSFT")},
        ),
        _context(llm, specialists),
    )

    routing_calls = [call for call in llm.structured_calls if call["model"] == "ManagerRouting"]
    assert len(routing_calls) == 1
    assert "Do not include chain-of-thought" in (routing_calls[0]["system"] or "")
    assert output.extras["analysis_type"] == "portfolio_risk"
    assert _invoked(specialists) == [MARKET_AGENT, RISK_AGENT]


def test_routing_failure_falls_back_to_heuristic_rebalancing() -> None:
    specialists = _specialists()
    llm = _FakeLLM(routing_error=ProviderError("router unavailable"))
    output = execute_agent(
        PortfolioManagerAgent(),
        AgentInput(
            request_id="mgr-fallback",
            symbols=[],
            question="Should I rebalance my portfolio?",
            extras={"portfolio": _portfolio("AAPL", "MSFT")},
        ),
        _context(llm, specialists),
    )

    assert output.extras["analysis_type"] == "portfolio_rebalancing"
    assert OPTIMIZATION_AGENT in _invoked(specialists)


def test_follow_up_requests_fundamental_analysis_when_valuation_is_asked() -> None:
    specialists = _specialists()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(
            symbols=[],
            question="What is the valuation risk of my portfolio?",
            extras={
                "analysis_type": "portfolio_risk",
                "portfolio": _portfolio("AAPL", "MSFT"),
            },
        ),
        _context(_FakeLLM(), specialists),
    )

    assert MARKET_AGENT in _invoked(specialists)
    assert RISK_AGENT in _invoked(specialists)
    assert FUNDAMENTAL_AGENT in _invoked(specialists)
    assert output.extras["follow_up_agents"] == [FUNDAMENTAL_AGENT]
    assert specialists[FUNDAMENTAL_AGENT].calls[0].extras[RISK_AGENT]["status"] == "succeeded"


def test_missing_portfolio_skips_optimizer_and_records_gap() -> None:
    specialists = _specialists()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(
            question="Should I rebalance AAPL?",
            extras={"analysis_type": "portfolio_rebalancing"},
        ),
        _context(_FakeLLM(), specialists),
    )

    assert OPTIMIZATION_AGENT not in _invoked(specialists)
    assert RISK_AGENT not in _invoked(specialists)
    assert any("portfolio" in item.lower() for item in output.extras["missing_information"])
    assert any("not invoked" in item.lower() or "optimization" in item.lower() for item in output.extras["limitations"])


def test_failed_specialist_is_collected_as_conflict_and_caps_confidence() -> None:
    specialists = _specialists(fail={MARKET_AGENT: "quote feed down"})
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(),
        _context(_FakeLLM(), specialists),
    )

    assert output.status == "succeeded"
    assert any("market-analysis failed" in item for item in output.extras["conflicts"])
    assert output.confidence == 0.45
    used = {item["agent"]: item["status"] for item in output.extras["agent_results_used"]}
    assert used[MARKET_AGENT] == "failed"
    assert used[FUNDAMENTAL_AGENT] == "succeeded"


def test_conflicting_market_and_fundamental_views_are_surfaced() -> None:
    specialists = _specialists(
        extras={
            MARKET_AGENT: {"trend": "uptrend", "unavailable": []},
            FUNDAMENTAL_AGENT: {"financial_health": "stressed", "unavailable": []},
        }
    )
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(),
        _context(_FakeLLM(), specialists),
    )

    assert any("uptrend" in item and "stressed" in item for item in output.extras["conflicts"])
    assert output.confidence <= 0.55


def test_infeasible_optimizer_is_a_conflict() -> None:
    specialists = _specialists(
        extras={OPTIMIZATION_AGENT: {"feasible": False, "unavailable": []}}
    )
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(
            extras={
                "analysis_type": "portfolio_rebalancing",
                "portfolio": _portfolio("AAPL", "MSFT"),
            }
        ),
        _context(_FakeLLM(), specialists),
    )
    assert any("feasible" in item.lower() for item in output.extras["conflicts"])


def test_missing_symbols_and_portfolio_fails_without_llm() -> None:
    llm = _FakeLLM()
    output = execute_agent(
        PortfolioManagerAgent(),
        AgentInput(request_id="mgr-empty", extras={}),
        _context(llm, _specialists()),
    )
    assert output.status == "failed"
    assert output.error_message == "Portfolio manager requires symbols or an uploaded portfolio."
    assert llm.structured_calls == []


def test_run_writes_structured_result_into_board_state() -> None:
    specialists = _specialists()
    state: BoardState = {
        "request_id": "mgr-state",
        "messages": [],
        "artifacts": {
            "symbols": ["msft"],
            "question": "Analyze MSFT",
            "analysis_type": "stock_analysis",
        },
    }
    updated = PortfolioManagerAgent().run(state, _context(_FakeLLM(), specialists))
    artifact = updated["artifacts"]["portfolio-manager"]
    assert artifact["status"] == "succeeded"
    assert artifact["extras"]["recommendation"]
    assert updated["errors"] == []


def test_manager_synthesis_schema_rejects_blank_summary() -> None:
    with pytest.raises(ValidationError):
        ManagerSynthesis(
            summary=" ",
            findings=[],
            recommendation="Hold",
            risks=[],
            assumptions=[],
            limitations=[],
            confidence=0.4,
        )


def test_invalid_analysis_type_fails_before_delegation() -> None:
    specialists = _specialists()
    output = execute_agent(
        PortfolioManagerAgent(),
        _payload(extras={"analysis_type": "astrology"}),
        _context(_FakeLLM(), specialists),
    )
    assert output.status == "failed"
    assert "analysis_type" in (output.error_message or "")
    assert _invoked(specialists) == []


def test_manager_module_orchestrates_without_data_providers_or_vendors() -> None:
    text = Path("app/agents/manager.py").read_text(encoding="utf-8")
    for token in (
        "get_quote",
        "get_historical_ohlc",
        "get_key_metrics",
        "MarketDataProvider",
        "FundamentalDataProvider",
        "NewsDataProvider",
        "StubLLMProvider",
        "build_llm_provider",
        "yfinance",
        "openai",
        "groq",
        "langgraph",
        "chain_of_thought",
    ):
        assert token not in text, token
    assert "complete_structured" in text
    assert "execute_agent" in text
    assert "trade_execution" in text
    assert "not_implemented" in text
