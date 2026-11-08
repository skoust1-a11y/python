"""Unit and integration tests for the Portfolio Optimization Agent."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.agents.base import AgentContext
from app.agents.contracts import AgentInput
from app.agents.execution import execute_agent
from app.agents.optimization import PortfolioOptimizationAgent
from app.exceptions import ProviderError
from app.models.common import DataSourceMetadata
from app.models.fundamentals import CompanyProfile
from app.models.market import HistoricalPrice, MarketQuote, OhlcSeries
from app.models.portfolio import Holding, Portfolio, SymbolValidation
from app.providers.contracts import FundamentalDataProvider, LLMProvider, MarketDataProvider, TModel
from app.providers.registry import ProviderBundle, build_providers
from tests.helpers import make_settings

UTC = timezone.utc
START = datetime(2024, 1, 2, 14, 30, tzinfo=UTC)
IMPORTED_AT = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)


class _FakeLLM(LLMProvider):
    def __init__(self, structured: dict[str, Any] | None = None) -> None:
        self._structured = structured or {
            "allocation_assessment": "The candidate reduces concentration versus the current book.",
            "comparison_findings": ["Proposed SAFE weight is higher than the current sleeve."],
            "constraint_findings": ["Maximum position cap was applied."],
            "manager_notes": ["Evaluate the optimized candidate before any later decision."],
            "limitations": ["Interpretation is limited to the supplied optimizer output."],
            "confidence": 0.71,
        }
        self.complete_calls: list[dict[str, Any]] = []
        self.structured_calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "fake-llm"

    @property
    def model(self) -> str:
        return "fake-opt-model"

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
        raise AssertionError("Portfolio optimization must not use free-form complete() for numbers.")

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
        errors: dict[str, Exception] | None = None,
        name: str = "controlled-market",
    ) -> None:
        self._quotes = quotes or {}
        self._histories = histories or {}
        self._errors = errors or {}
        self._name = name
        self.calls: list[tuple] = []

    @property
    def name(self) -> str:
        return self._name

    def search_instruments(self, query: str, *, limit: int = 10) -> list:
        raise ProviderError("search is not used by portfolio optimization")

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

    def get_index(self, symbol: str) -> Any:
        raise ProviderError("index is not used by portfolio optimization")

    def get_volume(self, instrument: str) -> Any:
        raise ProviderError("volume is not used by portfolio optimization")

    def get_market_info(self, instrument: str) -> Any:
        raise ProviderError("market info is not used by portfolio optimization")

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
        raise ProviderError("statements are not required for portfolio optimization")

    def get_key_metrics(self, instrument: str) -> Any:
        raise ProviderError("key metrics are not required for portfolio optimization")

    def get_valuation_metrics(self, instrument: str) -> Any:
        raise ProviderError("valuation is not required for portfolio optimization")

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


def _source(provider: str = "controlled-market", symbol: str = "SAFE") -> DataSourceMetadata:
    return DataSourceMetadata(
        provider=provider,
        source="unit-test-feed",
        timestamp=START + timedelta(days=20),
        raw_reference=symbol,
    )


def _series(symbol: str, values: list[float], provider: str = "controlled-market") -> OhlcSeries:
    prices = [
        HistoricalPrice(
            symbol=symbol,
            timestamp=START + timedelta(days=index),
            open=close,
            high=close + 1,
            low=max(close - 1, 0.01),
            close=close,
            period="1d",
            volume=1000,
            source=_source(provider, symbol),
        )
        for index, close in enumerate(values)
    ]
    return OhlcSeries(symbol=symbol, period="1d", prices=prices, source=_source(provider, symbol))


def _prices(start: float, returns: list[float]) -> list[float]:
    prices = [start]
    for change in returns:
        prices.append(prices[-1] * (1.0 + change))
    return prices


def _holding(symbol: str, quantity: float, *, average_cost: float | None = None) -> Holding:
    return Holding(
        symbol=symbol,
        quantity=quantity,
        average_cost=average_cost,
        currency="USD",
        symbol_validation=SymbolValidation(
            input=symbol, normalized=symbol, status="valid"
        ),
    )


def _portfolio(*holdings: Holding, portfolio_id: str = "pf-opt") -> Portfolio:
    return Portfolio(
        id=portfolio_id,
        holdings=list(holdings),
        base_currency="USD",
        source_filename="holdings.csv",
        source_format="csv",
        imported_at=IMPORTED_AT,
    )


def _sample_portfolio() -> Portfolio:
    return _portfolio(
        _holding("SAFE", 10, average_cost=90.0),
        _holding("RISKY", 10, average_cost=40.0),
    )


def _full_market(*, name: str = "controlled-market") -> _ControlledMarketData:
    safe = _prices(100.0, [0.001] * 20)
    risky = _prices(50.0, [0.05, -0.04] * 10)
    return _ControlledMarketData(
        name=name,
        quotes={
            "SAFE": MarketQuote(
                symbol="SAFE",
                value=safe[-1],
                timestamp=START + timedelta(days=20, hours=1),
                currency="USD",
                source=_source(name, "SAFE"),
            ),
            "RISKY": MarketQuote(
                symbol="RISKY",
                value=risky[-1],
                timestamp=START + timedelta(days=20, hours=1),
                currency="USD",
                source=_source(name, "RISKY"),
            ),
        },
        histories={
            "SAFE": _series("SAFE", safe, provider=name),
            "RISKY": _series("RISKY", risky, provider=name),
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
            "SAFE": CompanyProfile(
                symbol="SAFE",
                name="Fixture Safe",
                sector="Technology",
                industry="Software",
                currency="USD",
                timestamp=START,
                source=source,
            ),
            "RISKY": CompanyProfile(
                symbol="RISKY",
                name="Fixture Risky",
                sector="Health",
                industry="Biotech",
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
    extras = {
        "portfolio": _sample_portfolio(),
        "optimization_objective": "minimum_volatility",
        "max_weight": 0.7,
        "min_weight": 0.1,
        "sector_limits": {"Technology": 0.8},
        "target_risk": 1.0,
        "min_effective_n": 1.1,
    }
    extras.update(overrides.pop("extras", {}))
    values: dict[str, Any] = {
        "request_id": "opt-1",
        "symbols": ["safe", "risky"],
        "question": "Propose a calmer allocation.",
        "extras": extras,
    }
    values.update(overrides)
    return AgentInput(**values)


def test_agent_returns_optimizer_payload_without_trade_execution() -> None:
    llm = _FakeLLM()
    output = execute_agent(
        PortfolioOptimizationAgent(),
        _payload(),
        _context(_full_market(), llm=llm),
    )

    assert output.status == "succeeded"
    assert output.agent == "portfolio-optimization"
    assert output.role == "portfolio-optimizer"
    extras = output.extras
    assert extras["current_allocation"]
    assert extras["proposed_allocation"]
    assert extras["optimization_objective"] == "minimum_volatility"
    assert extras["constraints"]["max_weight"] == 0.7
    assert extras["constraints"]["min_weight"] == 0.1
    assert extras["constraints"]["sector_limits"]["Technology"] == 0.8
    assert extras["constraints"]["target_risk"] == 1.0
    assert extras["calculated_metrics"]["proposed"]["volatility"] is not None
    assert extras["warnings"] is not None
    assert extras["limitations"]
    assert extras["trade_execution"] == "not_implemented"
    assert extras["candidate_allocations"]
    assert extras["proposed_allocation"]["SAFE"] <= 0.7 + 1e-6
    assert extras["proposed_allocation"]["SAFE"] >= extras["proposed_allocation"]["RISKY"]
    assert extras["weight_basis"] == "market_value"
    assert extras["portfolio_id"] == "pf-opt"
    assert any(item.field == "proposed_weight" and item.symbol == "SAFE" for item in output.evidence)


def test_llm_interprets_computed_allocation_and_does_not_supply_weights() -> None:
    llm = _FakeLLM()
    output = execute_agent(
        PortfolioOptimizationAgent(),
        _payload(),
        _context(_full_market(), llm=llm),
    )

    assert llm.complete_calls == []
    assert len(llm.structured_calls) == 1
    system = llm.structured_calls[0]["system"] or ""
    prompt = llm.structured_calls[0]["prompt"]
    assert "Do not invent" in system
    assert "not a trade" in system.lower() or "not a trade" in prompt.lower()
    evidence = json.loads(prompt.split("\n\n", 1)[1])
    computed = evidence["computed"]
    assert computed["proposed_allocation"] == output.extras["proposed_allocation"]
    assert computed["optimization_objective"] == "minimum_volatility"
    assert computed["trade_execution"] == "not_implemented"
    assert output.extras["allocation_assessment"].startswith("The candidate reduces")
    assert output.summary == output.extras["allocation_assessment"]


def test_missing_portfolio_fails_without_calling_llm() -> None:
    llm = _FakeLLM()
    output = execute_agent(
        PortfolioOptimizationAgent(),
        AgentInput(request_id="opt-missing", symbols=["SAFE"], extras={}),
        _context(_full_market(), llm=llm),
    )
    assert output.status == "failed"
    assert output.error_message == "Portfolio optimization requires uploaded portfolio data."
    assert llm.structured_calls == []


def test_risk_adjusted_objective_is_passed_through() -> None:
    llm = _FakeLLM()
    output = execute_agent(
        PortfolioOptimizationAgent(),
        _payload(extras={"optimization_objective": "risk_adjusted_return", "max_weight": 1.0}),
        _context(_full_market(), llm=llm),
    )
    assert output.status == "succeeded"
    assert output.extras["optimization_objective"] == "risk_adjusted_return"
    assert output.extras["proposed_allocation"]["SAFE"] >= 0


def test_missing_history_does_not_invent_prices() -> None:
    market = _ControlledMarketData(
        quotes={
            "SAFE": MarketQuote(
                symbol="SAFE",
                value=100.0,
                timestamp=START,
                currency="USD",
                source=_source("controlled-market", "SAFE"),
            ),
            "RISKY": MarketQuote(
                symbol="RISKY",
                value=50.0,
                timestamp=START,
                currency="USD",
                source=_source("controlled-market", "RISKY"),
            ),
        },
        histories={
            "SAFE": _series("SAFE", _prices(100.0, [0.001] * 20)),
        },
        errors={"get_historical_ohlc:RISKY": ProviderError("missing history")},
    )
    output = execute_agent(
        PortfolioOptimizationAgent(),
        _payload(extras={"max_weight": 1.0, "min_weight": 0.0}),
        _context(market),
    )
    assert output.status == "succeeded"
    assert any("frozen" in warning.lower() for warning in output.extras["warnings"]) or (
        output.extras["proposed_allocation"] == output.extras["current_allocation"]
    )
    assert output.extras["warnings"] or output.extras["unavailable"]
