"""Unit and integration tests for the Risk Assessment Agent."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.base import AgentContext
from app.agents.contracts import AgentInput
from app.agents.execution import execute_agent
from app.agents.risk import RiskAssessmentAgent, RiskInterpretation
from app.exceptions import ProviderError
from app.models.common import DataSourceMetadata
from app.models.fundamentals import CompanyProfile
from app.models.market import HistoricalPrice, MarketIndex, MarketQuote, OhlcSeries
from app.models.portfolio import Holding, Portfolio, SymbolValidation
from app.providers.contracts import FundamentalDataProvider, LLMProvider, MarketDataProvider, TModel
from app.providers.registry import ProviderBundle, build_providers
from app.tools.market import realized_volatility
from app.tools.risk import (
    aligned_portfolio_values,
    close_map,
    herfindahl_hirschman_index,
    max_drawdown,
    mean_pairwise_correlation,
)
from app.workflow.state import BoardState
from tests.helpers import make_settings

UTC = timezone.utc
START = datetime(2024, 1, 2, 14, 30, tzinfo=UTC)
IMPORTED_AT = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)


class _FakeLLM(LLMProvider):
    def __init__(self, structured: dict[str, Any] | None = None) -> None:
        self._structured = structured or {
            "overall_risk_assessment": "Concentrated technology book with elevated single-name risk.",
            "major_risks": ["AAPL is half of portfolio market value."],
            "concentration_findings": ["HHI indicates high name concentration."],
            "diversification_findings": ["Effective N is well below holding count."],
            "limitations": ["Interpretation is limited to the supplied metrics."],
            "confidence": 0.73,
        }
        self.complete_calls: list[dict[str, Any]] = []
        self.structured_calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "fake-llm"

    @property
    def model(self) -> str:
        return "fake-risk-model"

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
        raise AssertionError("Risk assessment must not use free-form complete() for numbers.")

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


class _ControlledMarketData(MarketDataProvider):
    def __init__(
        self,
        *,
        quotes: dict[str, MarketQuote] | None = None,
        histories: dict[str, OhlcSeries] | None = None,
        indices: dict[str, MarketIndex] | None = None,
        errors: dict[str, Exception] | None = None,
        name: str = "controlled-market",
    ) -> None:
        self._quotes = quotes or {}
        self._histories = histories or {}
        self._indices = indices or {}
        self._errors = errors or {}
        self._name = name
        self.calls: list[tuple] = []

    @property
    def name(self) -> str:
        return self._name

    def search_instruments(self, query: str, *, limit: int = 10) -> list:
        raise ProviderError("search is not used by risk assessment")

    def get_quote(self, instrument: str) -> MarketQuote:
        return self._take("get_quote", instrument, self._quotes)

    def get_historical_ohlc(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        interval: str = "1d",
    ) -> OhlcSeries:
        self.calls.append(("get_historical_ohlc", instrument, start, end, interval))
        if "get_historical_ohlc" in self._errors:
            raise self._errors["get_historical_ohlc"]
        key = f"get_historical_ohlc:{instrument}"
        if key in self._errors:
            raise self._errors[key]
        try:
            return self._histories[instrument]
        except KeyError as exc:
            raise ProviderError(f"get_historical_ohlc has no fixture for {instrument}") from exc

    def get_index(self, symbol: str) -> MarketIndex:
        return self._take("get_index", symbol, self._indices)

    def get_volume(self, instrument: str) -> Any:
        raise ProviderError("volume is not used by risk assessment")

    def get_market_info(self, instrument: str) -> Any:
        raise ProviderError("market info is not used by risk assessment")

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


class _ControlledFundamentals(FundamentalDataProvider):
    def __init__(
        self,
        *,
        profiles: dict[str, CompanyProfile] | None = None,
        errors: dict[str, Exception] | None = None,
        name: str = "controlled-fundamentals",
    ) -> None:
        self._profiles = profiles or {}
        self._errors = errors or {}
        self._name = name
        self.calls: list[tuple] = []

    @property
    def name(self) -> str:
        return self._name

    def get_company_profile(self, instrument: str) -> CompanyProfile:
        return self._take("get_company_profile", instrument, self._profiles)

    def get_financial_statements(self, instrument: str, **kwargs: Any) -> list:
        raise ProviderError("statements are not required for risk assessment")

    def get_key_metrics(self, instrument: str) -> Any:
        raise ProviderError("key metrics are not required for risk assessment")

    def get_valuation_metrics(self, instrument: str) -> Any:
        raise ProviderError("valuation is not required for risk assessment")

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


def _source(provider: str = "controlled-market", symbol: str = "AAPL") -> DataSourceMetadata:
    return DataSourceMetadata(
        provider=provider,
        source="unit-test-feed",
        timestamp=START + timedelta(days=20),
        raw_reference=symbol,
    )


def _bars(symbol: str, close_values: list[float], *, provider: str = "controlled-market") -> list[HistoricalPrice]:
    source = _source(provider, symbol)
    return [
        HistoricalPrice(
            symbol=symbol,
            timestamp=START + timedelta(days=index),
            open=close,
            high=close + 1.0,
            low=max(close - 1.0, 0.01),
            close=close,
            period="1d",
            volume=1_000.0,
            currency="USD",
            source=source,
        )
        for index, close in enumerate(close_values)
    ]


def _series(symbol: str, close_values: list[float], *, provider: str = "controlled-market") -> OhlcSeries:
    prices = _bars(symbol, close_values, provider=provider)
    return OhlcSeries(
        symbol=symbol,
        period="1d",
        start=prices[0].timestamp,
        end=prices[-1].timestamp,
        prices=prices,
        source=_source(provider, symbol),
    )


def _holding(
    symbol: str,
    quantity: float,
    *,
    average_cost: float | None = None,
    weight: float | None = None,
    currency: str | None = "USD",
) -> Holding:
    return Holding(
        symbol=symbol,
        quantity=quantity,
        average_cost=average_cost,
        currency=currency,
        weight=weight,
        symbol_validation=SymbolValidation(
            input=symbol, normalized=symbol, status="valid"
        ),
    )


def _portfolio(*holdings: Holding, portfolio_id: str = "pf-1") -> Portfolio:
    return Portfolio(
        id=portfolio_id,
        holdings=list(holdings),
        base_currency="USD",
        source_filename="holdings.csv",
        source_format="csv",
        imported_at=IMPORTED_AT,
    )


AAPL_CLOSES = [100.0 + index for index in range(21)]
MSFT_CLOSES = [80.0 + 0.4 * index for index in range(21)]
GOOG_CLOSES = [200.0 + 0.8 * index for index in range(21)]
INDEX_CLOSES = [1000.0 + index for index in range(21)]


def _sample_portfolio() -> Portfolio:
    return _portfolio(
        _holding("AAPL", 10, average_cost=90.0),
        _holding("MSFT", 5, average_cost=70.0),
        _holding("GOOG", 3, average_cost=180.0),
    )


def _full_market(*, name: str = "controlled-market") -> _ControlledMarketData:
    return _ControlledMarketData(
        name=name,
        quotes={
            "AAPL": MarketQuote(
                symbol="AAPL",
                value=100.0,
                timestamp=START + timedelta(days=20, hours=1),
                currency="USD",
                source=_source(name, "AAPL"),
            ),
            "MSFT": MarketQuote(
                symbol="MSFT",
                value=80.0,
                timestamp=START + timedelta(days=20, hours=1),
                currency="USD",
                source=_source(name, "MSFT"),
            ),
            "GOOG": MarketQuote(
                symbol="GOOG",
                value=200.0,
                timestamp=START + timedelta(days=20, hours=1),
                currency="USD",
                source=_source(name, "GOOG"),
            ),
        },
        histories={
            "AAPL": _series("AAPL", AAPL_CLOSES, provider=name),
            "MSFT": _series("MSFT", MSFT_CLOSES, provider=name),
            "GOOG": _series("GOOG", GOOG_CLOSES, provider=name),
            "^TEST": _series("^TEST", INDEX_CLOSES, provider=name),
        },
        indices={
            "^TEST": MarketIndex(
                symbol="^TEST",
                value=5050.0,
                timestamp=START + timedelta(days=20),
                name="Test Composite",
                change_percent=0.25,
                source=_source(name, "^TEST"),
            )
        },
    )


def _full_fundamentals(*, name: str = "controlled-fundamentals") -> _ControlledFundamentals:
    source = DataSourceMetadata(
        provider=name,
        source="unit-test-fundamentals",
        timestamp=START,
    )
    return _ControlledFundamentals(
        name=name,
        profiles={
            "AAPL": CompanyProfile(
                symbol="AAPL",
                name="Fixture Apple",
                sector="Technology",
                industry="Consumer Electronics",
                currency="USD",
                timestamp=START,
                source=source,
            ),
            "MSFT": CompanyProfile(
                symbol="MSFT",
                name="Fixture Microsoft",
                sector="Technology",
                industry="Software",
                currency="USD",
                timestamp=START,
                source=source,
            ),
            "GOOG": CompanyProfile(
                symbol="GOOG",
                name="Fixture Google",
                sector="Communication Services",
                industry="Internet",
                currency="USD",
                timestamp=START,
                source=source,
            ),
        },
    )


def _context(
    market: MarketDataProvider,
    fundamentals: FundamentalDataProvider | None = None,
    llm: LLMProvider | None = None,
) -> AgentContext:
    bundle = build_providers(make_settings())
    return AgentContext(
        providers=ProviderBundle(
            llm=llm or _FakeLLM(),
            market_data=market,
            fundamentals=fundamentals or _full_fundamentals(),
            news=bundle.news,
        )
    )


def _payload(**overrides: Any) -> AgentInput:
    values: dict[str, Any] = {
        "request_id": "risk-1",
        "symbols": ["aapl", "msft", "goog"],
        "question": "Where is the risk in this book?",
        "extras": {"portfolio": _sample_portfolio(), "index_symbol": "^TEST"},
    }
    values.update(overrides)
    return AgentInput(**values)


def _expected_value_series() -> tuple[list[datetime], list[float]]:
    quantities = {"AAPL": 10.0, "MSFT": 5.0, "GOOG": 3.0}
    closes = {
        "AAPL": close_map(_series("AAPL", AAPL_CLOSES)),
        "MSFT": close_map(_series("MSFT", MSFT_CLOSES)),
        "GOOG": close_map(_series("GOOG", GOOG_CLOSES)),
    }
    result = aligned_portfolio_values(quantities, closes)
    assert result is not None
    return result


def test_agent_computes_risk_metrics_from_portfolio_and_history() -> None:
    market = _full_market()
    llm = _FakeLLM()
    output = execute_agent(RiskAssessmentAgent(), _payload(), _context(market, llm=llm))

    assert output.status == "succeeded"
    assert output.agent == "risk-assessment"
    assert output.role == "risk-analyst"
    extras = output.extras
    metrics = extras["risk_metrics"]
    timestamps, values = _expected_value_series()

    assert extras["overall_risk_assessment"] == (
        "Concentrated technology book with elevated single-name risk."
    )
    assert extras["major_risks"][0] == "AAPL is half of portfolio market value."
    assert extras["concentration_findings"]
    assert extras["diversification_findings"]
    assert extras["limitations"]
    assert extras["as_of"].startswith("2024-01-")
    assert extras["analyzed_at"]
    assert extras["market_data_provider"] == "controlled-market"
    assert extras["fundamental_data_provider"] == "controlled-fundamentals"
    assert extras["portfolio_id"] == "pf-1"
    assert extras["weight_basis"] == "market_value"
    assert extras["unavailable"] == []

    assert metrics["holding_count"] == 3
    assert metrics["total_market_value"] == pytest.approx(2000.0)
    assert metrics["largest_symbol"] == "AAPL"
    assert metrics["largest_weight"] == pytest.approx(0.5)
    assert metrics["hhi"] == pytest.approx(herfindahl_hirschman_index([0.5, 0.2, 0.3]))
    assert metrics["concentration"] == "high"
    assert metrics["sector_weights"]["Technology"] == pytest.approx(0.7)
    assert metrics["sector_weights"]["Communication Services"] == pytest.approx(0.3)
    assert metrics["largest_sector"] == "Technology"
    assert metrics["portfolio_volatility"] == pytest.approx(realized_volatility(values))
    assert metrics["max_drawdown"] == pytest.approx(max_drawdown(values))
    assert metrics["average_pairwise_correlation"] == pytest.approx(
        mean_pairwise_correlation(
            {
                "AAPL": close_map(_series("AAPL", AAPL_CLOSES)),
                "MSFT": close_map(_series("MSFT", MSFT_CLOSES)),
                "GOOG": close_map(_series("GOOG", GOOG_CLOSES)),
            }
        )
    )
    assert metrics["beta"] is not None
    assert metrics["index_symbol"] == "^TEST"
    assert sorted(metrics["oversized_symbols"]) == ["AAPL", "GOOG", "MSFT"]
    assert metrics["history_bar_count"] == len(timestamps)

    aapl = next(item for item in metrics["positions"] if item["symbol"] == "AAPL")
    assert aapl["price"] == 100.0
    assert aapl["market_value"] == 1000.0
    assert aapl["weight"] == pytest.approx(0.5)
    assert aapl["bar_count"] == 21
    assert aapl["price"] != AAPL_CLOSES[-1]

    assert any(item.field == "hhi" for item in output.evidence)
    assert any(item.field == "weight" and item.symbol == "AAPL" for item in output.evidence)
    assert any(item.field == "portfolio_volatility" for item in output.evidence)
    assert any(item.field == "max_drawdown" for item in output.evidence)


def test_llm_receives_structured_evidence_and_does_not_supply_metrics() -> None:
    market = _full_market()
    llm = _FakeLLM()
    execute_agent(RiskAssessmentAgent(), _payload(), _context(market, llm=llm))

    assert llm.complete_calls == []
    assert len(llm.structured_calls) == 1
    prompt = llm.structured_calls[0]["prompt"]
    system = llm.structured_calls[0]["system"]
    assert "Do not invent" in (system or "")
    evidence = json.loads(prompt.split("\n\n", 1)[1])
    metrics = evidence["computed"]["metrics"]
    assert metrics["largest_weight"] == pytest.approx(0.5)
    assert metrics["hhi"] == pytest.approx(0.38)
    assert metrics["weight_basis"] == "market_value"
    assert llm.structured_calls[0]["metadata"]["task"] == "risk-interpretation"
    assert llm.structured_calls[0]["metadata"]["agent"] == "risk-assessment"


def test_missing_quote_is_not_replaced_with_last_close() -> None:
    market = _full_market()
    market._errors["get_quote"] = ProviderError("quote feed down")
    output = execute_agent(RiskAssessmentAgent(), _payload(), _context(market))

    assert output.status == "succeeded"
    metrics = output.extras["risk_metrics"]
    assert output.extras["weight_basis"] == "cost_value"
    assert metrics["total_market_value"] is None
    aapl = next(item for item in metrics["positions"] if item["symbol"] == "AAPL")
    assert aapl["price"] is None
    assert aapl["market_value"] is None
    assert aapl["bar_count"] == 21
    assert "current_price" in output.extras["unavailable"]
    assert "market_value_weights" in output.extras["unavailable"]
    assert any("cost basis" in note.lower() for note in output.extras["limitations"])
    assert any("Unavailable inputs were not estimated" in risk for risk in output.extras["major_risks"])
    assert output.confidence == pytest.approx(0.6)


def test_short_history_does_not_invent_volatility_drawdown_or_correlation() -> None:
    market = _full_market()
    market._histories["AAPL"] = _series("AAPL", [100.0, 101.0, 102.0])
    market._histories["MSFT"] = _series("MSFT", [80.0, 80.4, 80.8])
    market._histories["GOOG"] = _series("GOOG", [200.0, 200.8, 201.6])
    market._histories["^TEST"] = _series("^TEST", [1000.0, 1001.0, 1002.0])
    output = execute_agent(RiskAssessmentAgent(), _payload(), _context(market))

    metrics = output.extras["risk_metrics"]
    assert metrics["portfolio_volatility"] is None
    assert metrics["average_pairwise_correlation"] is None
    assert metrics["beta"] is None
    series = aligned_portfolio_values(
        {"AAPL": 10.0, "MSFT": 5.0, "GOOG": 3.0},
        {
            "AAPL": close_map(market._histories["AAPL"]),
            "MSFT": close_map(market._histories["MSFT"]),
            "GOOG": close_map(market._histories["GOOG"]),
        },
    )
    assert series is not None
    assert metrics["max_drawdown"] == pytest.approx(max_drawdown(series[1]))
    assert "volatility" in output.extras["unavailable"]
    assert "correlation" in output.extras["unavailable"]
    assert "beta" in output.extras["unavailable"]
    assert any("Insufficient historical data" in note for note in output.extras["limitations"])
    assert output.confidence == pytest.approx(0.5)
    assert metrics["largest_weight"] == pytest.approx(0.5)


def test_missing_history_for_one_name_is_excluded_not_filled() -> None:
    market = _full_market()
    market._errors["get_historical_ohlc:MSFT"] = ProviderError("history unavailable")
    output = execute_agent(RiskAssessmentAgent(), _payload(), _context(market))
    metrics = output.extras["risk_metrics"]
    assert "historical_ohlc" in output.extras["unavailable"]
    assert "complete_price_history" in output.extras["unavailable"]
    msft = next(item for item in metrics["positions"] if item["symbol"] == "MSFT")
    assert msft["bar_count"] is None
    assert msft["volatility"] is None
    assert msft["weight"] == pytest.approx(0.2)
    assert any("MSFT" in note for note in output.extras["limitations"])
    assert output.confidence == pytest.approx(0.5)


def test_empty_payload_symbols_still_uses_portfolio_holdings() -> None:
    market = _full_market()
    output = execute_agent(
        RiskAssessmentAgent(),
        _payload(symbols=[]),
        _context(market),
    )
    assert output.status == "succeeded"
    assert output.extras["risk_metrics"]["holding_count"] == 3
    assert {item["symbol"] for item in output.extras["risk_metrics"]["positions"]} == {
        "AAPL",
        "MSFT",
        "GOOG",
    }


def test_missing_portfolio_fails_without_calling_providers() -> None:
    market = _full_market()
    fundamentals = _full_fundamentals()
    output = execute_agent(
        RiskAssessmentAgent(),
        _payload(extras={"index_symbol": "^TEST"}),
        _context(market, fundamentals),
    )
    assert output.status == "failed"
    assert output.error_code == "agent_error"
    assert market.calls == []
    assert fundamentals.calls == []


def test_run_writes_structured_risk_artifact_into_board_state() -> None:
    market = _full_market()
    state: BoardState = {
        "request_id": "risk-state",
        "messages": [],
        "artifacts": {
            "symbols": ["AAPL", "MSFT", "GOOG"],
            "question": "Review risk",
            "index_symbol": "^TEST",
            "portfolio": _sample_portfolio().model_dump(mode="json"),
        },
    }
    updated = RiskAssessmentAgent().run(state, _context(market))
    artifact = updated["artifacts"]["risk-assessment"]
    assert artifact["status"] == "succeeded"
    assert artifact["extras"]["risk_metrics"]["largest_symbol"] == "AAPL"
    assert artifact["extras"]["sources"]
    assert updated["messages"][0]["name"] == "risk-assessment"


def test_agent_consumes_prior_market_and_fundamental_evidence() -> None:
    market = _full_market()
    llm = _FakeLLM()
    prior = {
        "portfolio": _sample_portfolio(),
        "index_symbol": "^TEST",
        "market-analysis": {
            "summary": "Uptrend with benchmark outperformance.",
            "findings": ["Price sits above the long moving average."],
            "status": "succeeded",
            "extras": {
                "market_assessment": "Uptrend with benchmark outperformance.",
                "trend": "uptrend",
                "risks": ["A reversal would invalidate the short-term trend."],
            },
        },
        "fundamental-analysis": {
            "summary": "Profitable latest period with moderate leverage.",
            "findings": ["Positive reported earnings and cash flow."],
            "status": "succeeded",
            "extras": {
                "fundamental_assessment": "Profitable latest period with moderate leverage.",
                "financial_risks": ["A drop in margins would pressure returns."],
                "analyses": [
                    {"supporting_metrics": {"symbol": "AAPL", "sector": "Technology"}}
                ],
            },
        },
    }
    output = execute_agent(RiskAssessmentAgent(), _payload(extras=prior), _context(market, llm=llm))
    prompt = json.loads(llm.structured_calls[0]["prompt"].split("\n\n", 1)[1])
    assert "market-analysis" in prompt["prior_evidence"]
    assert "fundamental-analysis" in prompt["prior_evidence"]
    assert prompt["prior_evidence"]["market-analysis"]["extras"]["trend"] == "uptrend"
    assert output.extras["prior_agent_artifacts"] == ["market-analysis", "fundamental-analysis"]


def test_sector_falls_back_to_fundamental_evidence_when_profile_is_missing() -> None:
    market = _full_market()
    fundamentals = _full_fundamentals()
    fundamentals._errors["get_company_profile"] = ProviderError("profile unavailable")
    extras = {
        "portfolio": _sample_portfolio(),
        "index_symbol": "^TEST",
        "fundamental-analysis": {
            "summary": "Sector map from prior specialist.",
            "status": "succeeded",
            "extras": {
                "analyses": [
                    {"supporting_metrics": {"symbol": "AAPL", "sector": "Technology"}},
                    {"supporting_metrics": {"symbol": "MSFT", "sector": "Technology"}},
                    {"supporting_metrics": {"symbol": "GOOG", "sector": "Communication Services"}},
                ]
            },
        },
    }
    output = execute_agent(
        RiskAssessmentAgent(),
        _payload(extras=extras),
        _context(market, fundamentals),
    )
    metrics = output.extras["risk_metrics"]
    assert metrics["sector_weights"]["Technology"] == pytest.approx(0.7)
    assert "company_profile" in output.extras["unavailable"]
    assert "sector" not in output.extras["unavailable"]


def test_mixed_currency_does_not_combine_market_values() -> None:
    market = _full_market()
    portfolio = _portfolio(
        _holding("AAPL", 10, average_cost=90.0, weight=0.5, currency="USD"),
        _holding("MSFT", 5, average_cost=70.0, weight=0.2, currency="EUR"),
        _holding("GOOG", 3, average_cost=180.0, weight=0.3, currency="USD"),
    )
    output = execute_agent(
        RiskAssessmentAgent(),
        _payload(extras={"portfolio": portfolio, "index_symbol": "^TEST"}),
        _context(market),
    )
    assert output.extras["weight_basis"] == "uploaded_weight"
    assert output.extras["risk_metrics"]["total_market_value"] is None
    assert "fx_conversion" in output.extras["unavailable"]
    assert any("more than one currency" in note for note in output.extras["limitations"])
    assert output.extras["risk_metrics"]["largest_weight"] == pytest.approx(0.5)


def test_agent_accepts_any_market_data_provider_implementation() -> None:
    first = execute_agent(
        RiskAssessmentAgent(),
        _payload(),
        _context(_full_market(name="alpha-feed")),
    )
    second = execute_agent(
        RiskAssessmentAgent(),
        _payload(),
        _context(_full_market(name="beta-feed")),
    )
    assert first.extras["market_data_provider"] == "alpha-feed"
    assert second.extras["market_data_provider"] == "beta-feed"
    assert (
        first.extras["risk_metrics"]["largest_weight"]
        == second.extras["risk_metrics"]["largest_weight"]
    )


def test_stub_providers_do_not_invent_risk_metrics() -> None:
    bundle = build_providers(make_settings())
    llm = _FakeLLM(
        structured={
            "overall_risk_assessment": "No retrieved market history is available.",
            "major_risks": ["Analysis cannot proceed without a market-data feed."],
            "concentration_findings": [],
            "diversification_findings": [],
            "limitations": ["Every requested series was unavailable."],
            "confidence": 0.9,
        }
    )
    output = execute_agent(
        RiskAssessmentAgent(),
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
    metrics = output.extras["risk_metrics"]
    assert metrics["portfolio_volatility"] is None
    assert metrics["max_drawdown"] is None
    assert metrics["average_pairwise_correlation"] is None
    assert metrics["beta"] is None
    assert metrics["total_market_value"] is None
    assert output.extras["weight_basis"] == "cost_value"
    assert "current_price" in output.extras["unavailable"]
    assert "historical_ohlc" in output.extras["unavailable"]
    assert output.confidence <= 0.5
    assert "2000" not in output.summary


def test_interval_and_history_bounds_are_forwarded_to_the_provider() -> None:
    market = _full_market()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 2, 1, tzinfo=UTC)
    execute_agent(
        RiskAssessmentAgent(),
        _payload(
            extras={
                "portfolio": _sample_portfolio(),
                "index_symbol": "^TEST",
                "interval": "1D",
                "start": start,
                "end": end,
            }
        ),
        _context(market),
    )
    history_args = [call for call in market.calls if call[0] == "get_historical_ohlc"]
    assert ("get_historical_ohlc", "AAPL", start, end, "1d") in history_args
    assert ("get_historical_ohlc", "^TEST", start, end, "1d") in history_args


def test_risk_interpretation_schema_rejects_blank_assessment() -> None:
    with pytest.raises(ValidationError):
        RiskInterpretation(
            overall_risk_assessment=" ",
            major_risks=[],
            concentration_findings=[],
            diversification_findings=[],
            limitations=[],
            confidence=0.4,
        )


def test_risk_agent_module_depends_on_provider_contracts_only() -> None:
    text = Path("app/agents/risk.py").read_text(encoding="utf-8")
    for token in (
        "StubMarketDataProvider",
        "build_market_data_provider",
        "MarketAnalysisAgent",
        "FundamentalAnalysisAgent",
        "yfinance",
        "yahoo",
        "polygon",
        "alphavantage",
        "MARKET_DATA_ADAPTERS",
    ):
        assert token not in text
    assert "MarketDataProvider" in text
    assert "FundamentalDataProvider" in text
    assert "complete_structured" in text
    assert "app/agents/market.py" not in text
    assert "app/agents/fundamental.py" not in text


def test_single_holding_portfolio_does_not_mark_correlation_unavailable() -> None:
    market = _full_market()
    single_portfolio = _portfolio(_holding("AAPL", 10.0, average_cost=150.0, weight=1.0))
    output = execute_agent(
        RiskAssessmentAgent(),
        _payload(
            symbols=["AAPL"],
            extras={"portfolio": single_portfolio, "index_symbol": "^TEST"},
        ),
        _context(market),
    )
    assert output.status == "succeeded"
    assert "correlation" not in output.extras["unavailable"]
    metrics = output.extras["risk_metrics"]
    assert metrics["average_pairwise_correlation"] is None
    assert metrics["benchmark_correlation"] is not None
    assert isinstance(metrics["benchmark_correlation"], float)
    assert metrics["positions"][0]["benchmark_correlation"] is not None
    assert not any("Pairwise correlations were not computed" in note for note in output.extras["limitations"])



