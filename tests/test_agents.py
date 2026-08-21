"""Agent execution wrapper, contracts, and error handling."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from app.agents.base import Agent, AgentContext, AgentMetadata, AgentRuntime
from app.agents.contracts import AgentAnalysis, AgentInput, AgentOutput
from app.agents.evidence import EvidenceCollector
from app.agents.execution import execute_agent, input_from_state, run_agent_on_state
from app.exceptions import AgentError, ProviderError
from app.models.common import DataSourceMetadata, Evidence, MarketObservation
from app.providers.contracts import LLMProvider, TModel
from app.providers.registry import ProviderBundle, build_providers
from app.workflow.state import BoardState
from tests.helpers import make_settings

UTC = timezone.utc


class _Thesis(BaseModel):
    stance: str
    confidence: float


class _FakeLLM(LLMProvider):
    def __init__(
        self,
        *,
        text: str = "interpreted",
        error: Exception | None = None,
        structured: dict[str, Any] | None = None,
    ) -> None:
        self._text = text
        self._error = error
        self._structured = structured or {"stance": "hold", "confidence": 0.5}
        self.complete_calls: list[dict[str, Any]] = []
        self.structured_calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-model"

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
        if self._error is not None:
            raise self._error
        return self._text

    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        self.structured_calls.append(
            {"prompt": prompt, "system": system, "metadata": metadata}
        )
        if self._error is not None:
            raise self._error
        return response_model.model_validate(self._structured)


class _FixtureAgent(Agent):
    def __init__(
        self,
        *,
        fail: Exception | None = None,
        collect: bool = True,
        use_llm: bool = True,
        result: AgentAnalysis | object | None = None,
    ) -> None:
        self._fail = fail
        self._collect = collect
        self._use_llm = use_llm
        self._result = result
        self.runtime_seen: AgentRuntime | None = None

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="fixture-agent",
            role="test-double",
            description="In-test agent used to exercise the execution wrapper.",
        )

    def analyze(self, payload: AgentInput, runtime: AgentRuntime) -> AgentAnalysis:
        self.runtime_seen = runtime
        if self._collect:
            runtime.evidence.add(_sample_evidence())
        if self._fail is not None:
            raise self._fail
        if self._result is not None:
            return self._result  # type: ignore[return-value]
        summary = "analyzed without llm"
        findings: list[str] = [f"symbols:{','.join(payload.symbols) or 'none'}"]
        if self._use_llm:
            summary = runtime.complete("summarize holdings", system="Be concise.")
            thesis = runtime.complete_structured("stance", _Thesis)
            findings.append(f"stance:{thesis.stance}")
        return AgentAnalysis(
            summary=summary,
            findings=findings,
            evidence=runtime.evidence.items(),
            confidence=0.4,
            extras={"request_id": payload.request_id},
        )


def _sample_evidence() -> Evidence:
    return Evidence(
        source=DataSourceMetadata(
            provider="unit-test",
            source="fixture",
            timestamp=datetime(2024, 6, 15, 14, 30, tzinfo=UTC),
        ),
        symbol="AAPL",
        field="price",
        value=190.25,
    )


def _context(llm: LLMProvider | None = None, extras: dict[str, Any] | None = None) -> AgentContext:
    bundle = build_providers(make_settings())
    if llm is not None:
        bundle = ProviderBundle(
            llm=llm,
            market_data=bundle.market_data,
            fundamentals=bundle.fundamentals,
            news=bundle.news,
        )
    return AgentContext(providers=bundle, extras=extras)


def _payload(**overrides: Any) -> AgentInput:
    values: dict[str, Any] = {
        "request_id": "req-1",
        "symbols": ["aapl"],
        "question": "What is the risk?",
    }
    values.update(overrides)
    return AgentInput(**values)


def test_agent_metadata_requires_name_role_and_description() -> None:
    meta = AgentMetadata(name="  risk  ", role="analyst", description="Scores holdings")
    assert meta.name == "risk"
    with pytest.raises(ValueError, match="name"):
        AgentMetadata(name=" ", role="analyst", description="Scores holdings")
    with pytest.raises(ValueError, match="role"):
        AgentMetadata(name="risk", role="", description="Scores holdings")


def test_agent_input_and_output_contracts_validate() -> None:
    payload = _payload()
    assert payload.symbols == ["AAPL"]
    with pytest.raises(ValidationError):
        AgentInput(request_id=" ")
    output = AgentOutput(
        agent="fixture-agent",
        role="test-double",
        status="succeeded",
        summary="ok",
        duration_ms=1.5,
    )
    assert output.status == "succeeded"
    with pytest.raises(ValidationError):
        AgentOutput(
            agent="fixture-agent",
            role="test-double",
            status="unknown",
            summary="ok",
            duration_ms=1.0,
        )


def test_execute_agent_succeeds_with_timing_evidence_and_llm(monkeypatch, caplog) -> None:
    times = iter([10.0, 10.25])
    monkeypatch.setattr("app.agents.execution.time.perf_counter", lambda: next(times))
    caplog.set_level(logging.INFO, logger="app.agents")
    llm = _FakeLLM()
    agent = _FixtureAgent()

    output = execute_agent(agent, _payload(), _context(llm))

    assert output.status == "succeeded"
    assert output.agent == "fixture-agent"
    assert output.role == "test-double"
    assert output.summary == "interpreted"
    assert output.findings == ["symbols:AAPL", "stance:hold"]
    assert output.duration_ms == 250.0
    assert output.llm_provider == "fake"
    assert output.llm_model == "fake-model"
    assert len(output.evidence) == 1
    assert output.evidence[0].symbol == "AAPL"
    assert output.error_code is None
    assert "agent.start" in caplog.text
    assert "agent.finish" in caplog.text
    assert llm.complete_calls[0]["metadata"] == {
        "agent": "fixture-agent",
        "request_id": "req-1",
    }
    assert llm.structured_calls[0]["metadata"]["agent"] == "fixture-agent"
    assert agent.runtime_seen is not None
    assert agent.runtime_seen.llm is llm


def test_execute_agent_uses_injected_llm_not_a_constructed_adapter() -> None:
    llm = _FakeLLM(text="from-injected-adapter")
    output = execute_agent(_FixtureAgent(), _payload(), _context(llm))
    assert output.summary == "from-injected-adapter"
    assert output.llm_provider == "fake"
    assert len(llm.complete_calls) == 1


def test_provider_error_becomes_failed_output_and_keeps_evidence() -> None:
    llm = _FakeLLM(error=ProviderError("upstream timeout"))
    output = execute_agent(_FixtureAgent(), _payload(), _context(llm))

    assert output.status == "failed"
    assert output.error_code == "provider_error"
    assert output.error_message == "upstream timeout"
    assert output.summary == "fixture-agent failed"
    assert output.duration_ms >= 0
    assert len(output.evidence) == 1
    assert output.llm_provider == "fake"


def test_unexpected_error_is_isolated_and_does_not_leak_detail(caplog) -> None:
    caplog.set_level(logging.ERROR, logger="app.agents")
    output = execute_agent(
        _FixtureAgent(fail=RuntimeError("internal secret")),
        _payload(),
        _context(_FakeLLM()),
    )

    assert output.status == "failed"
    assert output.error_code == "agent_error"
    assert output.error_message == "An unexpected agent error occurred."
    assert "internal secret" not in (output.error_message or "")
    assert "internal secret" in caplog.text
    assert "agent.crash" in caplog.text


def test_agent_error_from_invalid_analysis_return_type() -> None:
    output = execute_agent(
        _FixtureAgent(collect=False, result={"summary": "not-a-model"}),
        _payload(),
        _context(_FakeLLM()),
    )
    assert output.status == "failed"
    assert output.error_code == "agent_error"
    assert "AgentAnalysis" in (output.error_message or "")


def test_run_writes_structured_result_into_board_state() -> None:
    llm = _FakeLLM()
    agent = _FixtureAgent()
    state: BoardState = {
        "request_id": "req-9",
        "messages": [],
        "artifacts": {"symbols": ["msft"], "question": "Review concentration"},
    }

    updated = agent.run(state, _context(llm))

    assert updated["request_id"] == "req-9"
    assert updated["messages"][0]["name"] == "fixture-agent"
    assert updated["messages"][0]["status"] == "succeeded"
    artifact = updated["artifacts"]["fixture-agent"]
    assert artifact["status"] == "succeeded"
    assert artifact["llm_provider"] == "fake"
    assert updated["errors"] == []


def test_failed_run_records_error_on_board_state() -> None:
    state: BoardState = {"request_id": "req-err", "messages": []}
    updated = run_agent_on_state(
        _FixtureAgent(fail=ProviderError("no quote")),
        state,
        _context(_FakeLLM()),
    )
    assert updated["errors"] == ["fixture-agent: no quote"]
    assert updated["artifacts"]["fixture-agent"]["status"] == "failed"


def test_invalid_graph_state_is_handled_without_raising() -> None:
    updated = run_agent_on_state(
        _FixtureAgent(),
        {"messages": []},  # type: ignore[typeddict-item]
        _context(_FakeLLM()),
    )
    assert updated["artifacts"]["fixture-agent"]["status"] == "failed"
    assert updated["artifacts"]["fixture-agent"]["error_code"] == "agent_error"


def test_input_from_state_normalizes_symbols_and_question() -> None:
    payload = input_from_state(
        {
            "request_id": "req-2",
            "messages": [],
            "artifacts": {"symbols": "aapl", "question": "  "},
        }
    )
    assert payload.symbols == ["AAPL"]
    assert payload.question is None


def test_evidence_collector_records_observations_and_deduplicates() -> None:
    collector = EvidenceCollector()
    evidence = _sample_evidence()
    observation = MarketObservation(
        symbol="AAPL",
        field="price",
        value=190.25,
        evidence=evidence,
    )
    collector.add(evidence)
    collector.add_observation(observation)
    collector.extend([evidence])
    assert len(collector) == 1
    assert list(collector)[0].field == "price"


def test_agent_error_is_an_application_error() -> None:
    error = AgentError("specialist failed")
    assert error.error_code == "agent_error"
    assert error.status_code == 500


def test_agents_do_not_construct_llm_or_data_adapters() -> None:
    agents_root = Path("app/agents")
    forbidden = (
        "build_llm_provider",
        "LLM_ADAPTERS",
        "StubLLMProvider",
        "build_providers(",
        "build_market_data_provider",
        "MARKET_DATA_ADAPTERS",
        "StubMarketDataProvider",
        "build_fundamental_data_provider",
        "FUNDAMENTAL_DATA_ADAPTERS",
        "StubFundamentalDataProvider",
    )
    for path in agents_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} contains {token}"
    assert "from app.providers.registry import ProviderBundle" in (
        agents_root / "base.py"
    ).read_text(encoding="utf-8")
    assert "self.llm.complete" in (agents_root / "base.py").read_text(encoding="utf-8")
