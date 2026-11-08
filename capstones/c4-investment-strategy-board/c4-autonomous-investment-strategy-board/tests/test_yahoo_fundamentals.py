"""Yahoo Finance fundamental-data adapter tests. Network calls are mocked."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.exceptions import ConfigurationError, ProviderError
from app.main import create_app
from app.providers.fundamentals.factory import FUNDAMENTAL_DATA_ADAPTERS, build_fundamental_data_provider
from app.providers.fundamentals.yahoo import YahooFundamentalDataProvider
from tests.helpers import make_settings

UTC = timezone.utc
NOW = datetime(2024, 6, 15, 10, 0, tzinfo=UTC)


class _FakeStatementsFrame:
    def __init__(self, data: dict[str, dict[str, float]] | None = None) -> None:
        # data format: {"2024-03-31": {"Total Revenue": 100000.0, "Net Income": 20000.0}}
        self._data = data or {}

    @property
    def empty(self) -> bool:
        return not self._data

    @property
    def columns(self) -> list[date]:
        return [date.fromisoformat(k) for k in self._data.keys()]

    def __getitem__(self, item: Any) -> dict[str, float]:
        key = item.isoformat() if isinstance(item, date) else str(item)
        return self._data.get(key, {})


class _FakeTicker:
    def __init__(
        self,
        symbol: str,
        *,
        info: dict | None = None,
        income_stmt=None,
        balance_sheet=None,
        cashflow=None,
    ) -> None:
        self.symbol = symbol
        payload = {
            "shortName": "Reliance Industries Limited",
            "longName": "Reliance Industries Limited",
            "sector": "Energy",
            "industry": "Oil & Gas Refining & Marketing",
            "longBusinessSummary": "Reliance Industries engages in energy, petrochemicals, retail, and telecom.",
            "country": "India",
            "currency": "INR",
            "financialCurrency": "INR",
            "exchange": "NSI",
            "website": "https://www.ril.com",
            "fullTimeEmployees": 389000,
            "totalRevenue": 9000000000000.0,
            "netIncomeToCommon": 700000000000.0,
            "trailingEps": 100.5,
            "forwardEps": 120.0,
            "ebitda": 1500000000000.0,
            "operatingMargins": 0.15,
            "profitMargins": 0.08,
            "returnOnEquity": 0.12,
            "returnOnAssets": 0.06,
            "debtToEquity": 45.2,
            "currentRatio": 1.25,
            "trailingPE": 25.5,
            "forwardPE": 22.0,
            "priceToBook": 2.1,
            "priceToSalesTrailing12Months": 1.8,
            "pegRatio": 1.5,
            "enterpriseToEbitda": 12.0,
            "marketCap": 20000000000000.0,
            "enterpriseValue": 22000000000000.0,
            "dividendYield": 0.005,
        }
        payload.update(info or {})
        self.info = payload
        self.fast_info = SimpleNamespace(
            market_cap=payload.get("marketCap"),
            currency=payload.get("currency"),
            exchange=payload.get("exchange"),
        )
        self.income_stmt = income_stmt or _FakeStatementsFrame(
            {"2024-03-31": {"Total Revenue": 9000000000000.0, "Net Income": 700000000000.0}}
        )
        self.quarterly_income_stmt = _FakeStatementsFrame(
            {"2024-06-30": {"Total Revenue": 2300000000000.0, "Net Income": 180000000000.0}}
        )
        self.balance_sheet = balance_sheet or _FakeStatementsFrame(
            {"2024-03-31": {"Total Assets": 15000000000000.0, "Total Liabilities Net Minority Interest": 7000000000000.0}}
        )
        self.quarterly_balance_sheet = _FakeStatementsFrame()
        self.cashflow = cashflow or _FakeStatementsFrame(
            {"2024-03-31": {"Operating Cash Flow": 1200000000000.0, "Free Cash Flow": 600000000000.0}}
        )
        self.quarterly_cashflow = _FakeStatementsFrame()


class _FakeYahoo:
    def __init__(self, tickers: dict[str, _FakeTicker] | None = None) -> None:
        self.tickers = tickers or {"RELIANCE.NS": _FakeTicker("RELIANCE.NS")}

    def Ticker(self, symbol: str) -> _FakeTicker:
        if symbol in self.tickers:
            return self.tickers[symbol]
        empty = _FakeTicker(
            symbol,
            info={
                "shortName": None,
                "longName": None,
                "sector": None,
                "industry": None,
                "totalRevenue": None,
                "netIncomeToCommon": None,
                "trailingPE": None,
                "currency": None,
                "exchange": None,
            },
        )
        empty.fast_info = SimpleNamespace(market_cap=None, currency=None, exchange=None)
        empty.income_stmt = _FakeStatementsFrame()
        empty.quarterly_income_stmt = _FakeStatementsFrame()
        empty.balance_sheet = _FakeStatementsFrame()
        empty.quarterly_balance_sheet = _FakeStatementsFrame()
        empty.cashflow = _FakeStatementsFrame()
        empty.quarterly_cashflow = _FakeStatementsFrame()
        return empty


def test_yahoo_is_a_registered_fundamentals_adapter() -> None:
    assert "yahoo" in FUNDAMENTAL_DATA_ADAPTERS
    provider = build_fundamental_data_provider(make_settings(fundamental_data_provider="yahoo"))
    assert isinstance(provider, YahooFundamentalDataProvider)
    assert provider.name == "yahoo"


def test_yfinance_alias_selects_yahoo_fundamentals_adapter() -> None:
    provider = build_fundamental_data_provider(make_settings(fundamental_data_provider="yfinance"))
    assert provider.name == "yahoo"


def test_create_app_accepts_yahoo_fundamentals_provider() -> None:
    application = create_app(make_settings(app_env="test", fundamental_data_provider="yahoo"))
    assert application.state.providers.fundamentals.name == "yahoo"


def test_yahoo_get_company_profile() -> None:
    provider = YahooFundamentalDataProvider(client=_FakeYahoo())
    profile = provider.get_company_profile("RELIANCE")
    assert profile.symbol == "RELIANCE"
    assert profile.name == "Reliance Industries Limited"
    assert profile.sector == "Energy"
    assert profile.industry == "Oil & Gas Refining & Marketing"
    assert profile.country == "India"
    assert profile.exchange == "NSE"
    assert profile.currency == "INR"
    assert profile.website == "https://www.ril.com"
    assert profile.employees == 389000
    assert profile.source.provider == "yahoo"
    assert profile.source.raw_reference == "RELIANCE.NS"


def test_yahoo_get_key_metrics() -> None:
    provider = YahooFundamentalDataProvider(client=_FakeYahoo())
    metrics = provider.get_key_metrics("RELIANCE")
    assert metrics.symbol == "RELIANCE"
    assert metrics.revenue == 9000000000000.0
    assert metrics.net_income == 700000000000.0
    assert metrics.pe_ratio == 25.5
    assert metrics.operating_margin == 0.15
    assert metrics.debt_to_equity == 45.2
    assert metrics.current_ratio == 1.25


def test_yahoo_get_valuation_metrics() -> None:
    provider = YahooFundamentalDataProvider(client=_FakeYahoo())
    val = provider.get_valuation_metrics("RELIANCE")
    assert val.symbol == "RELIANCE"
    assert val.pe_ratio == 25.5
    assert val.forward_pe == 22.0
    assert val.pb_ratio == 2.1
    assert val.ps_ratio == 1.8
    assert val.peg_ratio == 1.5


def test_yahoo_get_financial_statements() -> None:
    provider = YahooFundamentalDataProvider(client=_FakeYahoo())
    statements = provider.get_financial_statements("RELIANCE", statement_type="income", period="annual")
    assert len(statements) == 1
    assert statements[0].statement_type == "income"
    assert statements[0].period == "annual"
    assert statements[0].period_end == date(2024, 3, 31)
    assert statements[0].line_items.get("total_revenue") == 9000000000000.0


def test_yahoo_missing_instrument_raises_error() -> None:
    provider = YahooFundamentalDataProvider(client=_FakeYahoo())
    with pytest.raises(ProviderError, match="was not found"):
        provider.get_company_profile("MISSING")


def test_unknown_fundamental_data_provider_rejected() -> None:
    with pytest.raises(ConfigurationError, match="FUNDAMENTAL_DATA_PROVIDER"):
        build_fundamental_data_provider(make_settings(fundamental_data_provider="unknown-provider"))
