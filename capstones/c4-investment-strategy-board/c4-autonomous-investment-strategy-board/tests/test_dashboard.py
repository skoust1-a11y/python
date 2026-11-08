"""Dashboard overview HTTP API tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.exceptions import ProviderError, ProviderNotImplementedError
from app.main import create_app
from app.models.common import DataSourceMetadata
from app.models.market import (
    InstrumentMatch,
    MarketIndex,
    MarketInfo,
    MarketQuote,
    OhlcSeries,
    VolumeSnapshot,
)
from app.providers.contracts import MarketDataProvider
from app.providers.registry import ProviderBundle
from tests.helpers import make_settings
from tests.test_portfolio_analysis import _import_portfolio
from tests.test_stocks import _FakeFundamentalDataProvider, _FakeLLM

UTC = timezone.utc
NOW = datetime(2024, 6, 15, 10, 0, tzinfo=UTC)


def _source(provider: str, symbol: str) -> DataSourceMetadata:
    return DataSourceMetadata(
        provider=provider,
        source="unit-test",
        timestamp=NOW,
        raw_reference=symbol,
    )


class _DashboardMarketDataProvider(MarketDataProvider):
    def __init__(self) -> None:
        self.index_calls: list[str] = []
        self.quote_calls: list[str] = []
        self.fail_indices = False
        self.unimplemented = False
        self.quotes: dict[str, MarketQuote] = {}

    @property
    def name(self) -> str:
        return "fake-market"

    def search_instruments(self, query: str, *, limit: int = 10) -> list[InstrumentMatch]:
        return []

    def get_quote(self, instrument: str) -> MarketQuote:
        self.quote_calls.append(instrument)
        if self.unimplemented:
            raise ProviderNotImplementedError("Quotes are not implemented.")
        if instrument in self.quotes:
            return self.quotes[instrument]
        return MarketQuote(
            symbol=instrument,
            value=100.0,
            timestamp=NOW,
            currency="INR",
            exchange="NSE",
            change=1.5,
            change_percent=1.5,
            source=_source(self.name, instrument),
        )

    def get_historical_ohlc(self, instrument: str, **kwargs: Any) -> OhlcSeries:
        raise ProviderError("history is not used by the dashboard")

    def get_index(self, symbol: str) -> MarketIndex:
        self.index_calls.append(symbol)
        if self.unimplemented:
            raise ProviderNotImplementedError("Index information is not implemented.")
        if self.fail_indices:
            raise ProviderError("index unavailable")
        catalog = {
            "NIFTY50": ("NIFTY 50", 23500.0, 125.4, 0.54),
            "SENSEX": ("SENSEX", 77200.0, 310.0, 0.40),
            "NIFTYBANK": ("NIFTY Bank", 51200.0, -80.0, -0.16),
            "NIFTYIT": ("NIFTY IT", 42100.0, 210.0, 0.50),
        }
        name, value, change, change_percent = catalog.get(
            symbol.upper(), (symbol, 1000.0, 0.0, 0.0)
        )
        return MarketIndex(
            symbol=symbol,
            name=name,
            value=value,
            change=change,
            change_percent=change_percent,
            timestamp=NOW,
            currency="INR",
            exchange="NSE",
            source=_source(self.name, symbol),
        )

    def get_volume(self, instrument: str) -> VolumeSnapshot:
        raise ProviderError("volume is not used by the dashboard")

    def get_market_info(self, instrument: str) -> MarketInfo:
        if self.unimplemented:
            raise ProviderNotImplementedError("Market information is not implemented.")
        if self.fail_indices:
            raise ProviderError("market info unavailable")
        return MarketInfo(
            symbol=instrument,
            name="NIFTY 50",
            exchange="NSE",
            currency="INR",
            asset_class="index",
            timezone="Asia/Kolkata",
            trading_hours="09:15-15:30 IST",
            session="open",
            source=_source(self.name, instrument),
        )


def _dashboard_app(*, market: MarketDataProvider | None = None):
    application = create_app(make_settings(app_env="test", log_level="WARNING"))
    bundle = application.state.providers
    application.state.providers = ProviderBundle(
        llm=_FakeLLM(),
        market_data=market or _DashboardMarketDataProvider(),
        fundamentals=_FakeFundamentalDataProvider(),
        news=bundle.news,
    )
    return application


def test_dashboard_returns_nifty_major_indices_and_market_status() -> None:
    market = _DashboardMarketDataProvider()
    with TestClient(_dashboard_app(market=market)) as client:
        response = client.get("/dashboard")
        assert response.status_code == 200
        body = response.json()
        assert body["portfolio"] is None
        snapshot = body["market"]
        assert snapshot["session"] == "open"
        assert snapshot["timezone"] == "Asia/Kolkata"
        assert snapshot["trading_hours"] == "09:15-15:30 IST"
        assert snapshot["nifty50"]["name"] == "NIFTY 50"
        assert snapshot["nifty50"]["value"] == 23500.0
        assert snapshot["nifty50"]["change_percent"] == 0.54
        names = [item["name"] for item in snapshot["indices"]]
        assert names == ["SENSEX", "NIFTY Bank", "NIFTY IT"]
        assert snapshot["as_of"]
        assert snapshot["provider"] == "fake-market"
        assert snapshot["evidence"]
        assert snapshot["evidence"][0]["source"]["provider"] == "fake-market"
        assert snapshot["evidence"][0]["source"]["timestamp"]
        assert snapshot["unavailable"] == []
        assert "NIFTY50" in market.index_calls
        assert set(body.keys()) == {"market", "portfolio"}
        assert "specialists" not in body
        assert "recommendation" not in body


def test_dashboard_stub_provider_does_not_invent_market_data() -> None:
    application = create_app(make_settings(app_env="test", log_level="WARNING"))
    with TestClient(application) as client:
        response = client.get("/dashboard")
        assert response.status_code == 200
        body = response.json()
        assert body["market"]["nifty50"] is None
        assert body["market"]["indices"] == []
        assert body["market"]["session"] == "unknown"
        assert "nifty50" in body["market"]["unavailable"]
        assert body["portfolio"] is None


def test_dashboard_includes_portfolio_overview_without_running_analysis() -> None:
    market = _DashboardMarketDataProvider()
    market.quotes = {
        "AAPL": MarketQuote(
            symbol="AAPL",
            value=200.0,
            timestamp=NOW,
            currency="USD",
            change=2.0,
            change_percent=1.0,
            source=_source(market.name, "AAPL"),
        ),
        "MSFT": MarketQuote(
            symbol="MSFT",
            value=400.0,
            timestamp=NOW,
            currency="USD",
            change=-1.0,
            change_percent=-0.25,
            source=_source(market.name, "MSFT"),
        ),
    }
    with TestClient(_dashboard_app(market=market)) as client:
        portfolio_id = _import_portfolio(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        body = response.json()
        portfolio = body["portfolio"]
        assert portfolio["id"] == portfolio_id
        assert portfolio["holding_count"] == 2
        assert portfolio["market_value"] == 4000.0
        assert portfolio["day_change"] == 15.0
        assert portfolio["risk"]["weight_basis"] == "market_value"
        symbols = [row["symbol"] for row in portfolio["allocation"]]
        assert symbols[0] == "AAPL"
        assert "concentration" in portfolio["risk"]
        assert "specialists" not in body
        assert market.quote_calls == ["AAPL", "MSFT"]


def test_dashboard_records_missing_quotes_instead_of_inventing_value() -> None:
    market = _DashboardMarketDataProvider()

    def _missing_msft(instrument: str) -> MarketQuote:
        if instrument == "MSFT":
            raise ProviderError("quote unavailable")
        return MarketQuote(
            symbol=instrument,
            value=200.0,
            timestamp=NOW,
            currency="USD",
            source=_source(market.name, instrument),
        )

    market.get_quote = _missing_msft  # type: ignore[method-assign]
    with TestClient(_dashboard_app(market=market)) as client:
        _import_portfolio(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        portfolio = response.json()["portfolio"]
        assert portfolio["holding_count"] == 2
        assert portfolio["market_value"] is None
        assert "quote:MSFT" in portfolio["unavailable"]
        assert portfolio["quoted_holding_count"] == 1
