"""Unit and integration tests for the Market Analysis Agent."""

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
from app.agents.market import MarketAnalysisAgent, MarketInterpretation
from app.exceptions import ProviderError
from app.models.common import DataSourceMetadata
from app.models.market import (
    HistoricalPrice,
    MarketIndex,
    MarketInfo,
    MarketQuote,
    OhlcSeries,
    VolumeSnapshot,
)
from app.providers.contracts import LLMProvider, MarketDataProvider, TModel
from app.providers.registry import ProviderBundle, build_providers
from app.tools.market import (
    classify_trend,
    price_momentum,
    realized_volatility,
    relative_performance,
    simple_moving_average,
    total_return,
)
from app.workflow.state import BoardState
from tests.helpers import make_settings

UTC = timezone.utc
START = datetime(2024, 1, 2, 14, 30, tzinfo=UTC)


class _FakeLLM(LLMProvider):
    def __init__(self, structured: dict[str, Any] | None = None) -> None:
        self._structured = structured or {
            "market_assessment": "Uptrend with benchmark outperformance.",
            "risks": ["A reversal would invalidate the short-term trend."],
            "key_observations": ["Price sits above the long moving average."],
            "confidence": 0.72,
        }
        self.complete_calls: list[dict[str, Any]] = []
        self.structured_calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "fake-llm"

    @property
    def model(self) -> str:
        return "fake-market-model"

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
        raise AssertionError("Market analysis must not use free-form complete() for numbers.")

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
        volumes: dict[str, VolumeSnapshot] | None = None,
        indices: dict[str, MarketIndex] | None = None,
        infos: dict[str, MarketInfo] | None = None,
        errors: dict[str, Exception] | None = None,
        name: str = "controlled-market",
    ) -> None:
        self._quotes = quotes or {}
        self._histories = histories or {}
        self._volumes = volumes or {}
        self._indices = indices or {}
        self._infos = infos or {}
        self._errors = errors or {}
        self._name = name
        self.calls: list[tuple] = []

    @property
    def name(self) -> str:
        return self._name

    def search_instruments(self, query: str, *, limit: int = 10) -> list:
        raise ProviderError("search is not used by market analysis")

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

    def get_volume(self, instrument: str) -> VolumeSnapshot:
        return self._take("get_volume", instrument, self._volumes)

    def get_market_info(self, instrument: str) -> MarketInfo:
        return self._take("get_market_info", instrument, self._infos)

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


def _bars(
    symbol: str,
    close_values: list[float],
    *,
    start: datetime = START,
    high_offset: float = 0.0,
    low_offset: float = 0.0,
    volume: float = 1_000.0,
    provider: str = "controlled-market",
) -> list[HistoricalPrice]:
    source = _source(provider, symbol)
    return [
        HistoricalPrice(
            symbol=symbol,
            timestamp=start + timedelta(days=index),
            open=close,
            high=close + high_offset,
            low=close - low_offset,
            close=close,
            period="1d",
            volume=volume,
            currency="USD",
            exchange="NASDAQ",
            source=source,
        )
        for index, close in enumerate(close_values)
    ]


def _series(symbol: str, close_values: list[float], **kwargs: Any) -> OhlcSeries:
    prices = _bars(symbol, close_values, **kwargs)
    provider = kwargs.get("provider", "controlled-market")
    return OhlcSeries(
        symbol=symbol,
        period="1d",
        start=prices[0].timestamp,
        end=prices[-1].timestamp,
        prices=prices,
        source=_source(provider, symbol),
    )


ASSET_CLOSES = [100.0 + index for index in range(21)]
INDEX_CLOSES = [1000.0 + 0.5 * index for index in range(21)]


def _full_market(*, name: str = "controlled-market") -> _ControlledMarketData:
    source = _source(name, "AAPL")
    return _ControlledMarketData(
        name=name,
        quotes={
            "AAPL": MarketQuote(
                symbol="AAPL",
                value=120.5,
                timestamp=START + timedelta(days=20, hours=1),
                currency="USD",
                exchange="NASDAQ",
                change=0.5,
                change_percent=0.4167,
                volume=2_000_000,
                source=source,
            )
        },
        histories={
            "AAPL": _series("AAPL", ASSET_CLOSES, high_offset=2.0, low_offset=1.0, provider=name),
            "^TEST": _series("^TEST", INDEX_CLOSES, provider=name),
        },
        volumes={
            "AAPL": VolumeSnapshot(
                symbol="AAPL",
                value=2_000_000,
                average_volume=1_000_000,
                timestamp=START + timedelta(days=20),
                source=source,
            )
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
        infos={
            "AAPL": MarketInfo(
                symbol="AAPL",
                name="Fixture Apple",
                exchange="NASDAQ",
                currency="USD",
                asset_class="equity",
                source=source,
            )
        },
    )


def _context(market: MarketDataProvider, llm: LLMProvider | None = None) -> AgentContext:
    bundle = build_providers(make_settings())
    return AgentContext(
        providers=ProviderBundle(
            llm=llm or _FakeLLM(),
            market_data=market,
            fundamentals=bundle.fundamentals,
            news=bundle.news,
        )
    )


def _payload(**overrides: Any) -> AgentInput:
    values: dict[str, Any] = {
        "request_id": "mkt-1",
        "symbols": ["aapl"],
        "question": "How is this name trading?",
        "extras": {"index_symbol": "^TEST"},
    }
    values.update(overrides)
    return AgentInput(**values)


def test_agent_computes_indicators_from_controlled_series() -> None:
    market = _full_market()
    llm = _FakeLLM()
    output = execute_agent(MarketAnalysisAgent(), _payload(), _context(market, llm))

    assert output.status == "succeeded"
    assert output.agent == "market-analysis"
    assert output.role == "market-analyst"
    extras = output.extras
    metrics = extras["supporting_metrics"]

    assert extras["market_assessment"] == "Uptrend with benchmark outperformance."
    assert extras["trend"] == "uptrend"
    assert extras["risks"][0] == "A reversal would invalidate the short-term trend."
    assert extras["key_observations"]
    assert extras["as_of"].startswith("2024-01-")
    assert extras["analyzed_at"]
    assert extras["market_data_provider"] == "controlled-market"
    assert extras["sources"]
    assert extras["unavailable"] == []

    assert metrics["current_price"] == 120.5
    assert metrics["historical_start_price"] == 100.0
    assert metrics["historical_end_price"] == 120.0
    assert metrics["historical_return"] == total_return(ASSET_CLOSES)
    assert metrics["historical_high"] == 122.0
    assert metrics["historical_low"] == 99.0
    assert metrics["volume"] == 2_000_000
    assert metrics["volume_ratio"] == 2.0
    assert metrics["index_symbol"] == "^TEST"
    assert metrics["index_level"] == 5050.0
    assert metrics["short_sma"] == simple_moving_average(ASSET_CLOSES, 5)
    assert metrics["long_sma"] == simple_moving_average(ASSET_CLOSES, 20)
    assert metrics["volatility"] == realized_volatility(ASSET_CLOSES)
    assert metrics["momentum"] == price_momentum(ASSET_CLOSES, 10)
    assert metrics["relative_performance"] == pytest.approx(
        relative_performance(ASSET_CLOSES, INDEX_CLOSES)
    )
    assert extras["trend"] == classify_trend(ASSET_CLOSES)
    assert metrics["current_price"] != metrics["historical_end_price"]

    price_evidence = [item for item in output.evidence if item.field == "price"]
    assert price_evidence[0].value == 120.5
    assert price_evidence[0].source.source == "unit-test-feed"
    assert any(item.field == "volatility" for item in output.evidence)
    assert any(item.field == "trend" for item in output.evidence)


def test_llm_receives_structured_evidence_and_does_not_supply_metrics() -> None:
    market = _full_market()
    llm = _FakeLLM()
    execute_agent(MarketAnalysisAgent(), _payload(), _context(market, llm))

    assert llm.complete_calls == []
    assert len(llm.structured_calls) == 1
    prompt = llm.structured_calls[0]["prompt"]
    system = llm.structured_calls[0]["system"]
    assert "Do not invent" in (system or "")
    evidence = json.loads(prompt.split("\n\n", 1)[1])
    metrics = evidence["analyses"][0]["supporting_metrics"]
    assert metrics["current_price"] == 120.5
    assert metrics["historical_return"] == pytest.approx(0.2)
    assert metrics["volatility"] == pytest.approx(realized_volatility(ASSET_CLOSES))
    assert llm.structured_calls[0]["metadata"]["task"] == "market-interpretation"
    assert llm.structured_calls[0]["metadata"]["agent"] == "market-analysis"


def test_missing_quote_is_not_replaced_with_last_close() -> None:
    market = _full_market()
    market._errors["get_quote"] = ProviderError("quote feed down")
    output = execute_agent(MarketAnalysisAgent(), _payload(), _context(market))

    assert output.status == "succeeded"
    metrics = output.extras["supporting_metrics"]
    assert metrics["current_price"] is None
    assert metrics["historical_end_price"] == 120.0
    assert "current_price" in output.extras["unavailable"]
    assert any("Unavailable inputs were not estimated" in risk for risk in output.extras["risks"])
    assert output.confidence == 0.5


def test_missing_volume_and_index_are_listed_not_invented() -> None:
    market = _full_market()
    market._errors["get_volume"] = ProviderError("volume unavailable")
    market._errors["get_index"] = ProviderError("index unavailable")
    market._errors["get_historical_ohlc:^TEST"] = ProviderError("index history unavailable")
    output = execute_agent(MarketAnalysisAgent(), _payload(), _context(market))

    metrics = output.extras["supporting_metrics"]
    assert metrics["volume"] is None
    assert metrics["volume_ratio"] is None
    assert metrics["index_level"] is None
    assert metrics["relative_performance"] is None
    assert "volume" in output.extras["unavailable"]
    assert "market_index" in output.extras["unavailable"]
    assert "relative_performance" in output.extras["unavailable"]
    assert metrics["current_price"] == 120.5


def test_index_context_is_skipped_when_no_benchmark_is_provided() -> None:
    market = _full_market()
    output = execute_agent(
        MarketAnalysisAgent(),
        _payload(extras={}),
        _context(market),
    )
    assert ("get_index", "^TEST") not in [(c[0], c[1]) for c in market.calls if len(c) >= 2]
    assert "market_index" in output.extras["unavailable"]
    assert "relative_performance" in output.extras["unavailable"]
    assert output.extras["supporting_metrics"]["relative_performance"] is None


def test_short_history_does_not_invent_trend_or_volatility() -> None:
    market = _full_market()
    market._histories["AAPL"] = _series("AAPL", [100.0, 101.0, 102.0])
    market._histories["^TEST"] = _series("^TEST", [1000.0, 1000.5, 1001.0])
    output = execute_agent(MarketAnalysisAgent(), _payload(), _context(market))

    metrics = output.extras["supporting_metrics"]
    assert output.extras["trend"] == "insufficient_data"
    assert metrics["volatility"] is None
    assert metrics["momentum"] is None
    assert metrics["short_sma"] is None
    assert metrics["long_sma"] is None
    assert "volatility" in output.extras["unavailable"]
    assert "momentum" in output.extras["unavailable"]
    assert metrics["historical_return"] == pytest.approx(0.02)


def test_empty_symbols_fails_without_calling_market_data() -> None:
    market = _full_market()
    output = execute_agent(
        MarketAnalysisAgent(),
        _payload(symbols=[]),
        _context(market),
    )
    assert output.status == "failed"
    assert output.error_code == "agent_error"
    assert market.calls == []


def test_run_writes_structured_market_artifact_into_board_state() -> None:
    market = _full_market()
    state: BoardState = {
        "request_id": "mkt-state",
        "messages": [],
        "artifacts": {
            "symbols": ["AAPL"],
            "question": "Review tape",
            "index_symbol": "^TEST",
        },
    }
    updated = MarketAnalysisAgent().run(state, _context(market))
    artifact = updated["artifacts"]["market-analysis"]
    assert artifact["status"] == "succeeded"
    assert artifact["extras"]["trend"] == "uptrend"
    assert artifact["extras"]["supporting_metrics"]["current_price"] == 120.5
    assert artifact["extras"]["sources"]
    assert updated["messages"][0]["name"] == "market-analysis"


def test_agent_accepts_any_market_data_provider_implementation() -> None:
    first = execute_agent(
        MarketAnalysisAgent(),
        _payload(),
        _context(_full_market(name="alpha-feed")),
    )
    second = execute_agent(
        MarketAnalysisAgent(),
        _payload(),
        _context(_full_market(name="beta-feed")),
    )
    assert first.extras["market_data_provider"] == "alpha-feed"
    assert second.extras["market_data_provider"] == "beta-feed"
    assert (
        first.extras["supporting_metrics"]["current_price"]
        == second.extras["supporting_metrics"]["current_price"]
    )


def test_stub_market_data_does_not_invent_prices() -> None:
    bundle = build_providers(make_settings())
    llm = _FakeLLM(
        structured={
            "market_assessment": "No retrieved market data is available.",
            "risks": ["Analysis cannot proceed without a market-data feed."],
            "key_observations": ["Every requested series was unavailable."],
            "confidence": 0.9,
        }
    )
    output = execute_agent(
        MarketAnalysisAgent(),
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
    metrics = output.extras["supporting_metrics"]
    assert metrics["current_price"] is None
    assert metrics["historical_end_price"] is None
    assert metrics["volume"] is None
    assert metrics["volatility"] is None
    assert metrics["momentum"] is None
    assert metrics["relative_performance"] is None
    assert output.extras["trend"] == "insufficient_data"
    assert "current_price" in output.extras["unavailable"]
    assert "historical_ohlc" in output.extras["unavailable"]
    assert output.confidence == 0.5
    assert "120.5" not in output.summary


def test_interval_and_history_bounds_are_forwarded_to_the_provider() -> None:
    market = _full_market()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 2, 1, tzinfo=UTC)
    execute_agent(
        MarketAnalysisAgent(),
        _payload(
            extras={"index_symbol": "^TEST", "interval": "1D", "start": start, "end": end}
        ),
        _context(market),
    )
    history_args = [call for call in market.calls if call[0] == "get_historical_ohlc"]
    assert ("get_historical_ohlc", "AAPL", start, end, "1d") in history_args
    assert ("get_historical_ohlc", "^TEST", start, end, "1d") in history_args


def test_market_interpretation_schema_rejects_blank_assessment() -> None:
    with pytest.raises(ValidationError):
        MarketInterpretation(
            market_assessment=" ",
            risks=[],
            key_observations=[],
            confidence=0.4,
        )


def test_market_agent_module_depends_on_provider_contract_only() -> None:
    text = Path("app/agents/market.py").read_text(encoding="utf-8")
    for token in (
        "StubMarketDataProvider",
        "build_market_data_provider",
        "yfinance",
        "yahoo",
        "polygon",
        "alphavantage",
        "MARKET_DATA_ADAPTERS",
    ):
        assert token not in text
    assert "MarketDataProvider" in text
    assert "complete_structured" in text
