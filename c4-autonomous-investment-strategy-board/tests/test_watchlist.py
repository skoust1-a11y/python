"""Watchlist HTTP API tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.exceptions import ProviderError, ProviderNotImplementedError
from app.main import create_app
from app.models.fundamentals import CompanyProfile, FinancialMetrics, ValuationMetrics
from app.models.market import InstrumentMatch, MarketInfo, MarketQuote, OhlcSeries, VolumeSnapshot
from tests.helpers import make_settings
from tests.test_portfolio_analysis import _import_portfolio
from tests.test_stocks import (
    _FakeFundamentalDataProvider,
    _FakeMarketDataProvider,
    _stock_app,
)


class _ToggleMarketDataProvider(_FakeMarketDataProvider):
    def __init__(self) -> None:
        super().__init__()
        self.fail_all = False

    def _reject_unknown(self, instrument: str) -> None:
        if self.fail_all:
            raise ProviderError("temporarily unavailable")
        super()._reject_unknown(instrument)


class _ToggleFundamentalDataProvider(_FakeFundamentalDataProvider):
    def __init__(self) -> None:
        super().__init__()
        self.fail_all = False

    def get_company_profile(self, instrument: str) -> CompanyProfile:
        if self.fail_all:
            raise ProviderError("temporarily unavailable")
        return super().get_company_profile(instrument)

    def get_key_metrics(self, instrument: str) -> FinancialMetrics:
        if self.fail_all:
            raise ProviderError("temporarily unavailable")
        return super().get_key_metrics(instrument)

    def get_valuation_metrics(self, instrument: str) -> ValuationMetrics:
        if self.fail_all:
            raise ProviderError("temporarily unavailable")
        return super().get_valuation_metrics(instrument)


class _UnimplementedAfterAddMarket(_FakeMarketDataProvider):
    def __init__(self) -> None:
        super().__init__()
        self.unimplemented = False

    def search_instruments(self, query: str, *, limit: int = 10) -> list[InstrumentMatch]:
        if self.unimplemented:
            raise ProviderNotImplementedError("Instrument search is not implemented.")
        return super().search_instruments(query, limit=limit)

    def get_quote(self, instrument: str) -> MarketQuote:
        if self.unimplemented:
            raise ProviderNotImplementedError("Quotes are not implemented.")
        return super().get_quote(instrument)

    def get_historical_ohlc(self, instrument: str, **kwargs: Any) -> OhlcSeries:
        if self.unimplemented:
            raise ProviderNotImplementedError("Historical OHLC data is not implemented.")
        return super().get_historical_ohlc(instrument, **kwargs)

    def get_volume(self, instrument: str) -> VolumeSnapshot:
        if self.unimplemented:
            raise ProviderNotImplementedError("Volume is not implemented.")
        return super().get_volume(instrument)

    def get_market_info(self, instrument: str) -> MarketInfo:
        if self.unimplemented:
            raise ProviderNotImplementedError("Market information is not implemented.")
        return super().get_market_info(instrument)


class _UnimplementedAfterAddFundamentals(_FakeFundamentalDataProvider):
    def __init__(self) -> None:
        super().__init__()
        self.unimplemented = False

    def get_company_profile(self, instrument: str) -> CompanyProfile:
        if self.unimplemented:
            raise ProviderNotImplementedError("Company profile is not implemented.")
        return super().get_company_profile(instrument)


def test_add_list_current_info_and_remove() -> None:
    application = _stock_app()
    with TestClient(application) as client:
        empty = client.get("/watchlist")
        assert empty.status_code == 200
        assert empty.json() == []

        added = client.post("/watchlist", json={"symbol": "aapl"})
        assert added.status_code == 200
        body = added.json()
        assert body["symbol"] == "AAPL"
        assert body["name"] == "Apple Inc."
        assert body["quote"]["value"] == 190.25
        assert body["quote"]["source"]["provider"] == "fake-market"
        assert body["analyzer_path"] == "/stocks/AAPL"
        assert body["added_at"]
        assert "recommendation" not in body
        assert "specialist_results" not in body

        duplicate = client.post("/watchlist", json={"symbol": "AAPL"})
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "conflict"

        listed = client.get("/watchlist")
        assert listed.status_code == 200
        assert [item["symbol"] for item in listed.json()] == ["AAPL"]
        assert listed.json()[0]["quote"]["value"] == 190.25

        current = client.get("/watchlist/aapl")
        assert current.status_code == 200
        assert current.json()["symbol"] == "AAPL"
        assert current.json()["volume"]["value"] == 50_000_000
        assert current.json()["evidence"]

        missing_item = client.get("/watchlist/MSFT")
        assert missing_item.status_code == 404
        assert missing_item.json()["error"]["code"] == "not_found"

        removed = client.delete("/watchlist/AAPL")
        assert removed.status_code == 200
        assert removed.json() == {"symbol": "AAPL", "removed": True}
        assert client.get("/watchlist").json() == []
        assert client.get("/watchlist/AAPL").status_code == 404
        assert client.delete("/watchlist/AAPL").status_code == 404


def test_watchlist_rejects_invalid_and_unknown_symbols() -> None:
    application = _stock_app()
    with TestClient(application) as client:
        invalid = client.post("/watchlist", json={"symbol": "AAPL_US"})
        assert invalid.status_code == 422
        unknown = client.post("/watchlist", json={"symbol": "MISSING"})
        assert unknown.status_code == 404
        blank = client.post("/watchlist", json={"symbol": "   "})
        assert blank.status_code == 422
        assert client.get("/watchlist").json() == []
        assert client.get("/watchlist/AAPL_US").status_code == 422


def test_watchlist_does_not_invent_data_with_stub_providers() -> None:
    application = create_app(make_settings(app_env="test", log_level="WARNING"))
    with TestClient(application) as client:
        added = client.post("/watchlist", json={"symbol": "AAPL"})
        assert added.status_code == 501
        assert added.json()["error"]["code"] == "provider_not_implemented"
        assert client.get("/watchlist").json() == []


def test_open_uses_stock_analyzer_selection_without_running_analysis() -> None:
    application = _stock_app()
    with TestClient(application) as client:
        client.post("/watchlist", json={"symbol": "AAPL"})
        opened = client.post("/watchlist/AAPL/open")
        assert opened.status_code == 200
        body = opened.json()
        assert body["symbol"] == "AAPL"
        assert body["analyzer_path"] == "/stocks/AAPL"
        assert body["selected"]["symbol"] == "AAPL"
        assert body["overview"]["quote"]["value"] == 190.25
        assert body["overview"]["profile"]["sector"] == "Technology"
        assert "recommendation" not in body
        assert "analysis_type" not in body
        assert client.get("/stocks/AAPL/analysis").json() == []
        analyzer = client.get("/stocks/AAPL")
        assert analyzer.status_code == 200
        assert analyzer.json()["quote"]["value"] == 190.25
        assert client.post("/watchlist/MSFT/open").status_code == 404
        assert client.post("/watchlist/AAPL/analysis", json={"question": "Review AAPL"}).status_code == 404


def test_list_and_current_info_survive_unavailable_symbols() -> None:
    market = _ToggleMarketDataProvider()
    fundamentals = _ToggleFundamentalDataProvider()
    application = _stock_app(market=market, fundamentals=fundamentals)
    with TestClient(application) as client:
        first = client.post("/watchlist", json={"symbol": "AAPL"})
        second = client.post("/watchlist", json={"symbol": "MSFT"})
        assert first.status_code == 200
        assert second.status_code == 200

        market.fail_all = True
        fundamentals.fail_all = True
        listed = client.get("/watchlist")
        assert listed.status_code == 200
        symbols = [item["symbol"] for item in listed.json()]
        assert symbols == ["MSFT", "AAPL"]
        for item in listed.json():
            assert item["quote"] is None
            assert "current_information" in item["unavailable"]
            assert item["analyzer_path"].startswith("/stocks/")

        current = client.get("/watchlist/AAPL")
        assert current.status_code == 200
        assert current.json()["symbol"] == "AAPL"
        assert current.json()["name"] == "Apple Inc."
        assert "current_information" in current.json()["unavailable"]


def test_unimplemented_adapter_is_recorded_on_list_not_invented() -> None:
    market = _UnimplementedAfterAddMarket()
    fundamentals = _UnimplementedAfterAddFundamentals()
    application = _stock_app(market=market, fundamentals=fundamentals)
    with TestClient(application) as client:
        added = client.post("/watchlist", json={"symbol": "AAPL"})
        assert added.status_code == 200
        market.unimplemented = True
        fundamentals.unimplemented = True
        listed = client.get("/watchlist")
        assert listed.status_code == 200
        assert listed.json()[0]["symbol"] == "AAPL"
        assert listed.json()[0]["quote"] is None
        assert "current_information" in listed.json()[0]["unavailable"]


def test_watchlist_is_independent_of_uploaded_portfolio() -> None:
    application = _stock_app()
    with TestClient(application) as client:
        portfolio_id = _import_portfolio(client)
        added = client.post("/watchlist", json={"symbol": "MSFT"})
        assert added.status_code == 200
        assert added.json()["symbol"] == "MSFT"
        listed = client.get("/watchlist")
        assert listed.status_code == 200
        assert listed.json()[0]["symbol"] == "MSFT"
        assert "portfolio_id" not in listed.json()[0]
        portfolio = client.get(f"/portfolios/{portfolio_id}")
        assert portfolio.status_code == 200
        assert portfolio.json()["holding_count"] == 2
        assert client.get("/watchlist").json()[0]["symbol"] == "MSFT"


def test_watchlist_service_depends_on_contracts_not_vendor_or_analysis() -> None:
    text = Path("app/services/watchlist.py").read_text(encoding="utf-8")
    for token in (
        "StubMarketDataProvider",
        "yfinance",
        "alpha_vantage",
        "polygon",
        "finnhub",
        "analyze_stock",
        "invoke_strategy_board",
        "StockAnalysisRequest",
    ):
        assert token not in text
