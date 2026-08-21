"""Unit and integration tests for the Fundamental Analysis Agent."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.base import AgentContext
from app.agents.contracts import AgentInput
from app.agents.execution import execute_agent
from app.agents.fundamental import FundamentalAnalysisAgent, FundamentalInterpretation
from app.exceptions import ProviderError
from app.models.common import DataSourceMetadata
from app.models.fundamentals import (
    CompanyProfile,
    FinancialMetrics,
    FinancialStatement,
    ReportingPeriod,
    StatementType,
    ValuationMetrics,
)
from app.providers.contracts import FundamentalDataProvider, LLMProvider, TModel
from app.providers.registry import ProviderBundle, build_providers
from app.tools.fundamentals import growth_rate
from app.workflow.state import BoardState
from tests.helpers import make_settings

UTC = timezone.utc
RETRIEVED_AT = datetime(2024, 11, 2, 15, 0, tzinfo=UTC)
VALUATION_AT = datetime(2024, 11, 15, 14, 30, tzinfo=UTC)


class _FakeLLM(LLMProvider):
    def __init__(self, structured: dict[str, Any] | None = None) -> None:
        self._structured = structured or {
            "fundamental_assessment": "Profitable latest period with moderate leverage.",
            "strengths": ["Positive reported earnings and cash flow."],
            "weaknesses": ["Revenue growth depends on a single prior filing."],
            "valuation_observations": ["Current PE is above book value multiples."],
            "financial_risks": ["A drop in margins would pressure returns."],
            "confidence": 0.74,
        }
        self.complete_calls: list[dict[str, Any]] = []
        self.structured_calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "fake-llm"

    @property
    def model(self) -> str:
        return "fake-fundamental-model"

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
            "Fundamental analysis must not use free-form complete() for numbers."
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
            {"prompt": prompt, "system": system, "metadata": metadata}
        )
        return response_model.model_validate(self._structured)


class _ControlledFundamentals(FundamentalDataProvider):
    def __init__(
        self,
        *,
        profiles: dict[str, CompanyProfile] | None = None,
        statements: dict[tuple[str, str, str], list[FinancialStatement]] | None = None,
        metrics: dict[str, FinancialMetrics] | None = None,
        valuations: dict[str, ValuationMetrics] | None = None,
        errors: dict[str, Exception] | None = None,
        name: str = "controlled-fundamentals",
    ) -> None:
        self._profiles = profiles or {}
        self._statements = statements or {}
        self._metrics = metrics or {}
        self._valuations = valuations or {}
        self._errors = errors or {}
        self._name = name
        self.calls: list[tuple] = []

    @property
    def name(self) -> str:
        return self._name

    def get_company_profile(self, instrument: str) -> CompanyProfile:
        return self._take("get_company_profile", instrument, self._profiles)

    def get_financial_statements(
        self,
        instrument: str,
        *,
        statement_type: StatementType = "income",
        period: ReportingPeriod = "annual",
    ) -> list[FinancialStatement]:
        self.calls.append(("get_financial_statements", instrument, statement_type, period))
        method = "get_financial_statements"
        if method in self._errors:
            raise self._errors[method]
        for key in (
            f"{method}:{instrument}:{statement_type}:{period}",
            f"{method}:{instrument}:{statement_type}",
            f"{method}:{instrument}",
        ):
            if key in self._errors:
                raise self._errors[key]
        return list(self._statements.get((instrument, statement_type, period), []))

    def get_key_metrics(self, instrument: str) -> FinancialMetrics:
        return self._take("get_key_metrics", instrument, self._metrics)

    def get_valuation_metrics(self, instrument: str) -> ValuationMetrics:
        return self._take("get_valuation_metrics", instrument, self._valuations)

    def _take(self, method: str, instrument: str, store: dict[str, Any]) -> Any:
        self.calls.append((method, instrument))
        if method in self._errors:
            raise self._errors[method]
        key = f"{method}:{instrument}"
        if key in self._errors:
            raise self._errors[key]
        try:
            return store[instrument]
        except KeyError as exc:
            raise ProviderError(f"{method} has no fixture for {instrument}") from exc


def _source(provider: str = "controlled-fundamentals", symbol: str = "AAPL") -> DataSourceMetadata:
    return DataSourceMetadata(
        provider=provider,
        source="unit-test-fundamentals",
        timestamp=RETRIEVED_AT,
        raw_reference=symbol,
    )


def _valuation_source(provider: str = "controlled-fundamentals") -> DataSourceMetadata:
    return DataSourceMetadata(
        provider=provider,
        source="unit-test-valuation",
        timestamp=VALUATION_AT,
        raw_reference="AAPL",
    )


def _income(period_end: date, revenue: float, earnings: float, *, cadence: str = "annual") -> FinancialStatement:
    year = period_end.year
    return FinancialStatement(
        symbol="AAPL",
        statement_type="income",
        period=cadence,  # type: ignore[arg-type]
        currency="USD",
        period_end=period_end,
        fiscal_period=f"FY{year}" if cadence == "annual" else f"Q{year}",
        timestamp=RETRIEVED_AT,
        line_items={
            "revenue": revenue,
            "net_income": earnings,
            "eps": earnings / 4,
            "operating_income": earnings + 5,
        },
        source=_source(),
    )


def _balance(period_end: date, *, cadence: str = "annual") -> FinancialStatement:
    return FinancialStatement(
        symbol="AAPL",
        statement_type="balance_sheet",
        period=cadence,  # type: ignore[arg-type]
        currency="USD",
        period_end=period_end,
        fiscal_period=f"FY{period_end.year}",
        timestamp=RETRIEVED_AT,
        line_items={
            "total_debt": 120.0,
            "shareholders_equity": 80.0,
            "current_assets": 60.0,
            "current_liabilities": 30.0,
        },
        source=_source(),
    )


def _cash(period_end: date, *, cadence: str = "annual") -> FinancialStatement:
    return FinancialStatement(
        symbol="AAPL",
        statement_type="cash_flow",
        period=cadence,  # type: ignore[arg-type]
        currency="USD",
        period_end=period_end,
        fiscal_period=f"FY{period_end.year}",
        timestamp=RETRIEVED_AT,
        line_items={"operating_cash_flow": 40.0, "free_cash_flow": 28.0},
        source=_source(),
    )


def _full_fundamentals(*, name: str = "controlled-fundamentals") -> _ControlledFundamentals:
    fy2023 = date(2023, 9, 30)
    fy2024 = date(2024, 9, 28)
    source = _source(name)
    return _ControlledFundamentals(
        name=name,
        profiles={
            "AAPL": CompanyProfile(
                symbol="AAPL",
                name="Fixture Apple",
                sector="Technology",
                industry="Consumer Electronics",
                currency="USD",
                exchange="NASDAQ",
                timestamp=RETRIEVED_AT,
                source=source,
            )
        },
        statements={
            ("AAPL", "income", "annual"): [
                _income(fy2023, 90.0, 18.0),
                _income(fy2024, 100.0, 25.0),
            ],
            ("AAPL", "balance_sheet", "annual"): [_balance(fy2024)],
            ("AAPL", "cash_flow", "annual"): [_cash(fy2024)],
        },
        metrics={
            "AAPL": FinancialMetrics(
                symbol="AAPL",
                period="TTM",
                timestamp=RETRIEVED_AT,
                currency="USD",
                revenue=100.0,
                net_income=25.0,
                eps=6.25,
                operating_margin=0.30,
                profit_margin=0.25,
                roe=0.3125,
                debt_to_equity=1.5,
                current_ratio=2.0,
                pe_ratio=99.0,
                market_cap=1.0,
                source=source,
            )
        },
        valuations={
            "AAPL": ValuationMetrics(
                symbol="AAPL",
                timestamp=VALUATION_AT,
                currency="USD",
                pe_ratio=28.5,
                pb_ratio=8.1,
                ps_ratio=7.4,
                market_cap=3_000.0,
                enterprise_value=3_100.0,
                source=_valuation_source(name),
            )
        },
    )


def _context(
    fundamentals: FundamentalDataProvider, llm: LLMProvider | None = None
) -> AgentContext:
    bundle = build_providers(make_settings())
    return AgentContext(
        providers=ProviderBundle(
            llm=llm or _FakeLLM(),
            market_data=bundle.market_data,
            fundamentals=fundamentals,
            news=bundle.news,
        )
    )


def _payload(**overrides: Any) -> AgentInput:
    values: dict[str, Any] = {
        "request_id": "fun-1",
        "symbols": ["aapl"],
        "question": "How do the fundamentals look?",
        "extras": {"statement_period": "annual"},
    }
    values.update(overrides)
    return AgentInput(**values)


def test_agent_computes_reported_historical_and_current_metrics() -> None:
    fundamentals = _full_fundamentals()
    llm = _FakeLLM()
    output = execute_agent(FundamentalAnalysisAgent(), _payload(), _context(fundamentals, llm))

    assert output.status == "succeeded"
    assert output.agent == "fundamental-analysis"
    assert output.role == "fundamental-analyst"
    extras = output.extras
    metrics = extras["supporting_metrics"]
    reported = metrics["latest_reported"]
    historical = metrics["historical"]
    current = metrics["current_market"]

    assert extras["fundamental_assessment"] == "Profitable latest period with moderate leverage."
    assert extras["strengths"][0] == "Positive reported earnings and cash flow."
    assert extras["weaknesses"]
    assert extras["valuation_observations"]
    assert extras["financial_risks"]
    assert extras["reporting_period"]
    assert extras["timestamp"]
    assert extras["source"]["source"] == "unit-test-fundamentals"
    assert extras["sources"]
    assert extras["fundamental_data_provider"] == "controlled-fundamentals"
    assert extras["analyzed_at"]
    assert extras["unavailable"] == []

    assert reported["as_of_kind"] == "latest_reported"
    assert reported["revenue"] == 100.0
    assert reported["earnings"] == 25.0
    assert reported["eps"] == 6.25
    assert reported["operating_margin"] == 0.30
    assert reported["profit_margin"] == 0.25
    assert reported["roe"] == 0.3125
    assert reported["debt_to_equity"] == 1.5
    assert reported["operating_cash_flow"] == 40.0
    assert reported["period_end"] == "2024-09-28"
    assert historical["as_of_kind"] == "historical"
    assert historical["revenue"] == 90.0
    assert historical["growth_basis"] == "year_over_year"
    assert metrics["revenue_growth"] == growth_rate(100.0, 90.0)
    assert metrics["earnings_growth"] == growth_rate(25.0, 18.0)
    assert current["as_of_kind"] == "current_market"
    assert current["pe_ratio"] == 28.5
    assert current["market_cap"] == 3_000.0
    assert current["timestamp"].startswith("2024-11-15")
    assert current["pe_ratio"] != 99.0
    assert metrics["profitability"] == "profitable"
    assert metrics["financial_health"] == "healthy"

    assert any(item.field == "revenue" for item in output.evidence)
    assert any(item.field == "revenue_growth" for item in output.evidence)
    assert any(item.field == "pe_ratio" and item.value == 28.5 for item in output.evidence)


def test_llm_receives_structured_evidence_and_does_not_supply_metrics() -> None:
    fundamentals = _full_fundamentals()
    llm = _FakeLLM()
    execute_agent(FundamentalAnalysisAgent(), _payload(), _context(fundamentals, llm))

    assert llm.complete_calls == []
    assert len(llm.structured_calls) == 1
    prompt = llm.structured_calls[0]["prompt"]
    system = llm.structured_calls[0]["system"]
    assert "Do not invent" in (system or "")
    assert "Never describe a filed financial as current" in (system or "")
    evidence = json.loads(prompt.split("\n\n", 1)[1])
    metrics = evidence["analyses"][0]["supporting_metrics"]
    assert metrics["latest_reported"]["revenue"] == 100.0
    assert metrics["historical"]["revenue"] == 90.0
    assert metrics["current_market"]["pe_ratio"] == 28.5
    assert "filed figure, not a current market metric" in " ".join(
        evidence["analyses"][0]["factual_observations"]
    )
    assert llm.structured_calls[0]["metadata"]["task"] == "fundamental-interpretation"
    assert llm.structured_calls[0]["metadata"]["agent"] == "fundamental-analysis"


def test_stale_filings_are_not_presented_as_current_market_data() -> None:
    fundamentals = _full_fundamentals()
    output = execute_agent(FundamentalAnalysisAgent(), _payload(), _context(fundamentals))
    metrics = output.extras["supporting_metrics"]
    reported = metrics["latest_reported"]
    historical = metrics["historical"]
    current = metrics["current_market"]

    assert reported["as_of_kind"] == "latest_reported"
    assert historical["as_of_kind"] == "historical"
    assert current["as_of_kind"] == "current_market"
    assert reported["revenue"] != historical["revenue"]
    assert reported["period_end"] != historical["period_end"]
    assert current["timestamp"] != reported["timestamp"]
    assert "current revenue" not in output.summary.lower()
    observations = " ".join(output.extras["analyses"][0]["factual_observations"])
    assert "latest reported revenue" in observations
    assert "historical revenue" in observations
    assert "current market capitalization" in observations
    assert "current market PE" in observations


def test_more_recent_quarter_is_latest_reported_not_current() -> None:
    fundamentals = _full_fundamentals()
    fundamentals._metrics.pop("AAPL")
    fundamentals._errors["get_key_metrics"] = ProviderError("metrics unavailable")
    fundamentals._statements[("AAPL", "income", "quarterly")] = [
        _income(date(2025, 3, 29), 28.0, 7.0, cadence="quarterly")
    ]
    output = execute_agent(
        FundamentalAnalysisAgent(),
        _payload(extras={}),
        _context(fundamentals),
    )
    reported = output.extras["supporting_metrics"]["latest_reported"]
    assert reported["period_end"] == "2025-03-29"
    assert reported["revenue"] == 28.0
    assert reported["as_of_kind"] == "latest_reported"
    assert output.extras["supporting_metrics"]["current_market"]["as_of_kind"] == "current_market"


def test_missing_valuation_and_cash_flow_are_listed_not_invented() -> None:
    fundamentals = _full_fundamentals()
    fundamentals._errors["get_valuation_metrics"] = ProviderError("valuation unavailable")
    fundamentals._errors["get_financial_statements:AAPL:cash_flow"] = ProviderError(
        "cash flow unavailable"
    )
    output = execute_agent(FundamentalAnalysisAgent(), _payload(), _context(fundamentals))

    metrics = output.extras["supporting_metrics"]
    assert metrics["current_market"]["pe_ratio"] == 99.0
    assert metrics["current_market"]["as_of_kind"] == "current_market"
    assert metrics["latest_reported"]["operating_cash_flow"] is None
    assert "cash_flow" in output.extras["unavailable"]
    assert any("Unavailable inputs were not estimated" in risk for risk in output.extras["financial_risks"])
    assert metrics["latest_reported"]["revenue"] == 100.0


def test_missing_core_reported_data_caps_confidence() -> None:
    fundamentals = _full_fundamentals()
    fundamentals._errors["get_key_metrics"] = ProviderError("metrics unavailable")
    fundamentals._errors["get_financial_statements:AAPL:income"] = ProviderError(
        "income unavailable"
    )
    output = execute_agent(FundamentalAnalysisAgent(), _payload(), _context(fundamentals))
    assert output.extras["supporting_metrics"]["latest_reported"]["revenue"] is None
    assert output.extras["supporting_metrics"]["latest_reported"]["earnings"] is None
    assert "revenue" in output.extras["unavailable"]
    assert "earnings" in output.extras["unavailable"]
    assert output.confidence == 0.5


def test_empty_symbols_fails_without_calling_fundamentals() -> None:
    fundamentals = _full_fundamentals()
    output = execute_agent(
        FundamentalAnalysisAgent(),
        _payload(symbols=[]),
        _context(fundamentals),
    )
    assert output.status == "failed"
    assert output.error_code == "agent_error"
    assert fundamentals.calls == []


def test_run_writes_structured_fundamental_artifact_into_board_state() -> None:
    fundamentals = _full_fundamentals()
    state: BoardState = {
        "request_id": "fun-state",
        "messages": [],
        "artifacts": {
            "symbols": ["AAPL"],
            "question": "Review filings",
            "statement_period": "annual",
        },
    }
    updated = FundamentalAnalysisAgent().run(state, _context(fundamentals))
    artifact = updated["artifacts"]["fundamental-analysis"]
    assert artifact["status"] == "succeeded"
    assert artifact["extras"]["supporting_metrics"]["latest_reported"]["revenue"] == 100.0
    assert artifact["extras"]["source"]
    assert artifact["extras"]["reporting_period"]
    assert updated["messages"][0]["name"] == "fundamental-analysis"


def test_agent_accepts_any_fundamental_data_provider_implementation() -> None:
    first = execute_agent(
        FundamentalAnalysisAgent(),
        _payload(),
        _context(_full_fundamentals(name="alpha-fundamentals")),
    )
    second = execute_agent(
        FundamentalAnalysisAgent(),
        _payload(),
        _context(_full_fundamentals(name="beta-fundamentals")),
    )
    assert first.extras["fundamental_data_provider"] == "alpha-fundamentals"
    assert second.extras["fundamental_data_provider"] == "beta-fundamentals"
    assert (
        first.extras["supporting_metrics"]["latest_reported"]["revenue"]
        == second.extras["supporting_metrics"]["latest_reported"]["revenue"]
    )


def test_stub_fundamentals_do_not_invent_metrics() -> None:
    bundle = build_providers(make_settings())
    llm = _FakeLLM(
        structured={
            "fundamental_assessment": "No retrieved fundamental data is available.",
            "strengths": [],
            "weaknesses": ["Filings were unavailable."],
            "valuation_observations": [],
            "financial_risks": ["Analysis cannot proceed without a fundamentals feed."],
            "confidence": 0.9,
        }
    )
    output = execute_agent(
        FundamentalAnalysisAgent(),
        _payload(),
        AgentContext(
            providers=ProviderBundle(
                llm=llm,
                market_data=bundle.market_data,
                fundamentals=bundle.fundamentals,
                news=bundle.news,
            )
        ),
    )
    assert output.status == "succeeded"
    reported = output.extras["supporting_metrics"]["latest_reported"]
    current = output.extras["supporting_metrics"]["current_market"]
    assert reported["revenue"] is None
    assert reported["earnings"] is None
    assert reported["eps"] is None
    assert current["pe_ratio"] is None
    assert current["market_cap"] is None
    assert output.extras["supporting_metrics"]["revenue_growth"] is None
    assert output.extras["supporting_metrics"]["profitability"] == "insufficient_data"
    assert output.extras["supporting_metrics"]["financial_health"] == "insufficient_data"
    assert "revenue" in output.extras["unavailable"]
    assert "valuation" in output.extras["unavailable"]
    assert output.confidence == 0.5
    assert "100.0" not in output.summary


def test_statement_period_is_forwarded_to_the_provider() -> None:
    fundamentals = _full_fundamentals()
    execute_agent(
        FundamentalAnalysisAgent(),
        _payload(extras={"statement_period": "annual"}),
        _context(fundamentals),
    )
    statement_calls = [call for call in fundamentals.calls if call[0] == "get_financial_statements"]
    assert ("get_financial_statements", "AAPL", "income", "annual") in statement_calls
    assert ("get_financial_statements", "AAPL", "income", "quarterly") not in statement_calls


def test_derived_margins_come_from_statements_when_metrics_omit_them() -> None:
    fundamentals = _full_fundamentals()
    metrics = fundamentals._metrics["AAPL"]
    fundamentals._metrics["AAPL"] = metrics.model_copy(
        update={
            "operating_margin": None,
            "profit_margin": None,
            "roe": None,
            "debt_to_equity": None,
            "current_ratio": None,
        }
    )
    output = execute_agent(FundamentalAnalysisAgent(), _payload(), _context(fundamentals))
    reported = output.extras["supporting_metrics"]["latest_reported"]
    assert reported["profit_margin"] == pytest.approx(0.25)
    assert reported["operating_margin"] == pytest.approx(30.0 / 100.0)
    assert reported["debt_to_equity"] == pytest.approx(120.0 / 80.0)
    assert reported["current_ratio"] == pytest.approx(2.0)
    assert reported["as_of_kind"] == "latest_reported"


def test_unprofitable_negative_cash_is_stressed_not_estimated() -> None:
    fundamentals = _full_fundamentals()
    fundamentals._metrics["AAPL"] = fundamentals._metrics["AAPL"].model_copy(
            update={
                "net_income": -12.0,
                "revenue": 80.0,
                "profit_margin": -0.15,
                "roe": None,
                "current_ratio": 0.5,
            }
    )
    fy2024 = date(2024, 9, 28)
    fundamentals._statements[("AAPL", "income", "annual")] = [
        _income(date(2023, 9, 30), 90.0, 18.0),
        _income(fy2024, 80.0, -12.0),
    ]
    fundamentals._statements[("AAPL", "cash_flow", "annual")] = [
        FinancialStatement(
            symbol="AAPL",
            statement_type="cash_flow",
            period="annual",
            currency="USD",
            period_end=fy2024,
            timestamp=RETRIEVED_AT,
            line_items={"operating_cash_flow": -4.0, "free_cash_flow": -8.0},
            source=_source(),
        )
    ]
    fundamentals._statements[("AAPL", "balance_sheet", "annual")] = [
        FinancialStatement(
            symbol="AAPL",
            statement_type="balance_sheet",
            period="annual",
            currency="USD",
            period_end=fy2024,
            timestamp=RETRIEVED_AT,
            line_items={
                "total_debt": 200.0,
                "shareholders_equity": 40.0,
                "current_assets": 20.0,
                "current_liabilities": 40.0,
            },
            source=_source(),
        )
    ]
    output = execute_agent(FundamentalAnalysisAgent(), _payload(), _context(fundamentals))
    metrics = output.extras["supporting_metrics"]
    assert metrics["profitability"] == "unprofitable"
    assert metrics["liquidity"] == "tight"
    assert metrics["cash_generation"] == "negative"
    assert metrics["financial_health"] == "stressed"


def test_fundamental_interpretation_schema_rejects_blank_assessment() -> None:
    with pytest.raises(ValidationError):
        FundamentalInterpretation(
            fundamental_assessment=" ",
            strengths=[],
            weaknesses=[],
            valuation_observations=[],
            financial_risks=[],
            confidence=0.4,
        )


def test_fundamental_agent_module_depends_on_provider_contract_only() -> None:
    text = Path("app/agents/fundamental.py").read_text(encoding="utf-8")
    for token in (
        "StubFundamentalDataProvider",
        "build_fundamental_data_provider",
        "FUNDAMENTAL_DATA_ADAPTERS",
        "MarketDataProvider",
        "MarketAnalysisAgent",
        "yfinance",
        "fmp",
        "financialmodelingprep",
        "polygon",
    ):
        assert token not in text
    assert "FundamentalDataProvider" in text
    assert "complete_structured" in text
    assert "app/agents/market.py" not in text
