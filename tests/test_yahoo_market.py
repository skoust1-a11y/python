"""Yahoo Finance market-data adapter tests. Network calls are mocked."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.exceptions import ConfigurationError, ProviderError
from app.main import create_app
from app.providers.market_data.factory import MARKET_DATA_ADAPTERS, build_market_data_provider
from app.providers.market_data.yahoo import YahooMarketDataProvider, _vendor_candidates
from tests.helpers import make_settings

UTC = timezone.utc
NOW = datetime(2024, 6, 15, 10, 0, tzinfo=UTC)


class _FakeFrame:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self._rows = rows or []

    @property
    def empty(self) -> bool:
        return not self._rows

    def get(self, column: str):
        return [row.get(column) for row in self._rows]

    def iterrows(self):
        for index, row in enumerate(self._rows):
            yield row.get("timestamp", index), row


class _FakeTicker:
    def __init__(self, symbol: str, *, info: dict | None = None, history=None) -> None:
        self.symbol = symbol
        payload = {
            "shortName": "NIFTY 50",
            "regularMarketPrice": 23500.0,
            "regularMarketPreviousClose": 23374.6,
            "regularMarketChange": 125.4,
            "regularMarketChangePercent": 0.54,
            "regularMarketTime": NOW.timestamp(),
            "regularMarketVolume": 1_000_000,
            "currency": "INR",
            "exchange": "NSI",
            "quoteType": "INDEX",
            "marketState": "REGULAR",
            "exchangeTimezoneName": "Asia/Kolkata",
        }
        payload.update(info or {})
        self.info = payload
        self.fast_info = SimpleNamespace(
            last_price=payload["regularMarketPrice"],
            previous_close=payload["regularMarketPreviousClose"],
            last_volume=payload["regularMarketVolume"],
            currency=payload["currency"],
            exchange=payload["exchange"],
            timezone=payload["exchangeTimezoneName"],
        )
        self._history = history

    def history(self, **kwargs):
        if self._history is not None:
            return self._history
        return _FakeFrame(
            [
                {
                    "timestamp": NOW,
                    "Open": 23400.0,
                    "High": 23600.0,
                    "Low": 23300.0,
                    "Close": 23500.0,
                    "Volume": 1_000_000,
                }
            ]
        )


class _FakeSearch:
    def __init__(self, query: str, max_results: int = 10) -> None:
        self.query = query
        self.max_results = max_results
        self.quotes = [
            {
                "symbol": "RELIANCE.NS",
                "shortname": "Reliance Industries Limited",
                "exchange": "NSI",
                "currency": "INR",
                "quoteType": "EQUITY",
            }
        ][:max_results]


class _FakeYahoo:
    def __init__(self, tickers: dict[str, _FakeTicker] | None = None) -> None:
        self.tickers = tickers or {"^NSEI": _FakeTicker("^NSEI")}
        self.Search = _FakeSearch

    def Ticker(self, symbol: str) -> _FakeTicker:
        if symbol in self.tickers:
            return self.tickers[symbol]
        empty = _FakeTicker(
            symbol,
            info={
                "shortName": None,
                "regularMarketPrice": None,
                "regularMarketPreviousClose": None,
                "regularMarketChange": None,
                "regularMarketChangePercent": None,
                "regularMarketVolume": None,
                "currency": None,
                "exchange": None,
                "quoteType": None,
                "marketState": None,
                "exchangeTimezoneName": None,
            },
        )
        empty.fast_info = SimpleNamespace(
            last_price=None,
            previous_close=None,
            last_volume=None,
            currency=None,
            exchange=None,
            timezone=None,
        )
        empty._history = _FakeFrame()
        return empty


def test_yahoo_is_a_registered_market_adapter() -> None:
    assert "yahoo" in MARKET_DATA_ADAPTERS
    provider = build_market_data_provider(make_settings(market_data_provider="yahoo"))
    assert isinstance(provider, YahooMarketDataProvider)
    assert provider.name == "yahoo"


def test_yfinance_alias_selects_yahoo_adapter() -> None:
    provider = build_market_data_provider(make_settings(market_data_provider="yfinance"))
    assert provider.name == "yahoo"


def test_create_app_accepts_yahoo_market_provider() -> None:
    application = create_app(make_settings(app_env="test", market_data_provider="yahoo"))
    assert application.state.providers.market_data.name == "yahoo"


def test_index_aliases_map_nifty50_to_vendor_ticker() -> None:
    assert _vendor_candidates("NIFTY50") == ["^NSEI"]
    assert _vendor_candidates("SENSEX") == ["^BSESN"]
    assert _vendor_candidates("RELIANCE", country="GLOBAL")[0] == "RELIANCE"
    assert "RELIANCE.NS" in _vendor_candidates("RELIANCE")
    assert _vendor_candidates("RELIANCE", country="IN")[0] == "RELIANCE.NS"


def test_yahoo_get_index_maps_vendor_payload() -> None:
    provider = YahooMarketDataProvider(client=_FakeYahoo())
    index = provider.get_index("NIFTY50")
    assert index.symbol == "NIFTY50"
    assert index.value == 23500.0
    assert index.change_percent == 0.54
    assert index.name == "NIFTY 50"
    assert index.exchange == "NSE"
    assert index.source.provider == "yahoo"
    assert index.source.source == "yahoo-finance"
    assert index.source.timestamp is not None
    assert index.source.url == "https://finance.yahoo.com/quote/^NSEI"
    assert index.source.raw_reference == "^NSEI"


def test_yahoo_market_info_exposes_session_without_vendor_field_names_on_contract() -> None:
    provider = YahooMarketDataProvider(client=_FakeYahoo())
    info = provider.get_market_info("NIFTY50")
    assert info.session == "open"
    assert info.timezone == "Asia/Kolkata"
    assert info.trading_hours is None


def test_yahoo_passes_through_vendor_trading_hours_without_nse_default() -> None:
    tickers = {
        "^NSEI": _FakeTicker(
            "^NSEI",
            info={"tradingHours": "09:15-15:30"},
        )
    }
    provider = YahooMarketDataProvider(client=_FakeYahoo(tickers))
    info = provider.get_market_info("NIFTY50")
    assert info.trading_hours == "09:15-15:30"


def test_yahoo_search_returns_provider_independent_matches() -> None:
    provider = YahooMarketDataProvider(client=_FakeYahoo())
    matches = provider.search_instruments("reliance")
    assert matches[0].symbol == "RELIANCE.NS"
    assert matches[0].name == "Reliance Industries Limited"
    assert matches[0].exchange == "NSE"


def test_yahoo_quote_for_nse_equity_tries_suffix() -> None:
    tickers = {
        "RELIANCE.NS": _FakeTicker(
            "RELIANCE.NS",
            info={
                "shortName": "Reliance Industries Limited",
                "regularMarketPrice": 2900.0,
                "regularMarketPreviousClose": 2880.0,
                "regularMarketChange": 20.0,
                "regularMarketChangePercent": 0.69,
                "currency": "INR",
                "exchange": "NSI",
                "quoteType": "EQUITY",
                "marketState": "CLOSED",
            },
        )
    }
    provider = YahooMarketDataProvider(client=_FakeYahoo(tickers))
    quote = provider.get_quote("RELIANCE")
    assert quote.value == 2900.0
    assert quote.symbol == "RELIANCE"
    assert quote.extra["vendor_symbol"] == "RELIANCE.NS"


def test_yahoo_missing_instrument_is_a_provider_error() -> None:
    provider = YahooMarketDataProvider(client=_FakeYahoo())
    with pytest.raises(ProviderError, match="was not found"):
        provider.get_quote("MISSING")


def test_yahoo_does_not_use_previous_close_or_history_as_current_price() -> None:
    tickers = {
        "STALE.NS": _FakeTicker(
            "STALE.NS",
            info={
                "shortName": "Stale Co",
                "regularMarketPrice": None,
                "currentPrice": None,
                "regularMarketPreviousClose": 100.0,
                "previousClose": 100.0,
                "regularMarketChange": None,
                "regularMarketChangePercent": None,
                "regularMarketVolume": None,
                "currency": "INR",
                "exchange": "NSI",
                "quoteType": "EQUITY",
            },
            history=_FakeFrame(
                [
                    {
                        "timestamp": NOW,
                        "Open": 99.0,
                        "High": 101.0,
                        "Low": 98.0,
                        "Close": 100.0,
                        "Volume": 1_000,
                    }
                ]
            ),
        )
    }
    provider = YahooMarketDataProvider(client=_FakeYahoo(tickers))
    with pytest.raises(ProviderError, match="Quote is unavailable"):
        provider.get_quote("STALE")


def test_yahoo_does_not_stamp_quotes_with_retrieval_time() -> None:
    tickers = {
        "NOTIME.NS": _FakeTicker(
            "NOTIME.NS",
            info={
                "shortName": "No Time Co",
                "regularMarketPrice": 12.5,
                "regularMarketTime": None,
                "currency": "INR",
                "exchange": "NSI",
                "quoteType": "EQUITY",
            },
        )
    }
    provider = YahooMarketDataProvider(client=_FakeYahoo(tickers))
    with pytest.raises(ProviderError, match="Quote timestamp is unavailable"):
        provider.get_quote("NOTIME")


def test_unknown_yahoo_hardcoded_name_is_still_rejected() -> None:
    with pytest.raises(ConfigurationError, match="MARKET_DATA_PROVIDER"):
        build_market_data_provider(make_settings(market_data_provider="yahoo-hardcoded"))
