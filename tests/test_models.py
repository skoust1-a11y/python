from datetime import date, datetime, timezone
from math import inf, nan

import pytest
from pydantic import ValidationError

from app.models.common import DataSourceMetadata, Evidence, MarketObservation
from app.models.fundamentals import CompanyProfile, FinancialMetrics, FinancialStatement
from app.models.market import HistoricalPrice, InstrumentMatch, MarketIndex, MarketQuote, OhlcSeries
from app.models.news import NewsArticle
from app.workflow.graph import build_strategy_graph

UTC = timezone.utc


def _now() -> datetime:
    return datetime(2024, 6, 15, 14, 30, tzinfo=UTC)


def _source(**overrides) -> DataSourceMetadata:
    payload = {
        "provider": "stub",
        "source": "unit-test",
        "timestamp": _now(),
    }
    payload.update(overrides)
    return DataSourceMetadata(**payload)


def test_data_source_metadata_normalizes_and_requires_aware_timestamp() -> None:
    metadata = DataSourceMetadata(
        provider="  yahoo  ",
        source="exchange-feed",
        timestamp=_now(),
        url="https://example.com/quote",
    )
    assert metadata.provider == "yahoo"
    assert metadata.source == "exchange-feed"
    with pytest.raises(ValidationError):
        DataSourceMetadata(provider="stub", source="unit-test", timestamp=datetime(2024, 1, 1))
    with pytest.raises(ValidationError):
        DataSourceMetadata(provider=" ", source="unit-test", timestamp=_now())


def test_evidence_requires_source_and_validates_symbol_period_and_value() -> None:
    evidence = Evidence(
        source=_source(),
        symbol="aapl",
        period="1D",
        field="price",
        value=190.25,
    )
    assert evidence.symbol == "AAPL"
    assert evidence.period == "1d"
    assert evidence.source.provider == "stub"
    with pytest.raises(ValidationError):
        Evidence(symbol="AAPL", value=1.0)
    with pytest.raises(ValidationError):
        Evidence(source=_source(), symbol="AAPL US")
    with pytest.raises(ValidationError):
        Evidence(source=_source(), value=nan)


def test_market_observation_requires_evidence() -> None:
    observation = MarketObservation(
        symbol="AAPL",
        field="price",
        value=1.0,
        evidence=Evidence(source=_source(), symbol="AAPL", field="price", value=1.0),
    )
    assert observation.evidence.source.source == "unit-test"
    with pytest.raises(ValidationError):
        MarketObservation(symbol="AAPL", field="price", value=1.0)


def test_market_quote_accepts_normalized_fields() -> None:
    quote = MarketQuote(
        symbol=" aapl ",
        value=190.25,
        timestamp=_now(),
        currency="usd",
        exchange="nasdaq",
        bid=190.2,
        ask=190.3,
        change=-1.5,
        volume=1_000_000,
        source=_source(),
    )
    assert quote.symbol == "AAPL"
    assert quote.currency == "USD"
    assert quote.exchange == "NASDAQ"
    assert quote.value == 190.25


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"symbol": "AAPL", "value": 1.0, "timestamp": datetime(2024, 1, 1)},
        {"symbol": "AAPL", "timestamp": datetime(2024, 1, 1, tzinfo=UTC)},
        {"value": 1.0, "timestamp": datetime(2024, 1, 1, tzinfo=UTC), "source": None},
    ],
)
def test_market_quote_requires_core_fields(payload: dict) -> None:
    with pytest.raises(ValidationError):
        MarketQuote(**payload)


@pytest.mark.parametrize("symbol", ["", "   ", "AAPL US", "$$", "^"])
def test_symbols_are_rejected_when_invalid(symbol: str) -> None:
    with pytest.raises(ValidationError):
        MarketQuote(symbol=symbol, value=1.0, timestamp=_now(), source=_source())


@pytest.mark.parametrize("symbol, expected", [("aapl", "AAPL"), ("^gspc", "^GSPC"), ("brk.b", "BRK.B")])
def test_symbols_are_normalized(symbol: str, expected: str) -> None:
    quote = MarketQuote(symbol=symbol, value=1.0, timestamp=_now(), source=_source())
    assert quote.symbol == expected


@pytest.mark.parametrize("currency", ["US", "DOLLAR", "USDT", "usd1", ""])
def test_currencies_must_be_iso_4217_codes(currency: str) -> None:
    with pytest.raises(ValidationError):
        MarketQuote(symbol="AAPL", value=1.0, timestamp=_now(), currency=currency, source=_source())


@pytest.mark.parametrize("value", [nan, inf, -inf, -0.01])
def test_market_quote_rejects_invalid_numeric_values(value: float) -> None:
    with pytest.raises(ValidationError):
        MarketQuote(symbol="AAPL", value=value, timestamp=_now(), source=_source())


def test_market_quote_rejects_bid_greater_than_ask() -> None:
    with pytest.raises(ValidationError, match="bid"):
        MarketQuote(
            symbol="AAPL",
            value=10.0,
            timestamp=_now(),
            bid=10.2,
            ask=10.1,
            source=_source(),
        )


def test_market_quote_rejects_provider_specific_fields() -> None:
    with pytest.raises(ValidationError):
        MarketQuote(
            symbol="AAPL",
            value=1.0,
            timestamp=_now(),
            source=_source(),
            regularMarketPrice=1.0,
        )


def test_historical_price_validates_ohlc_and_exposes_close_as_value() -> None:
    price = HistoricalPrice(
        symbol="MSFT",
        timestamp=_now(),
        open=10.0,
        high=12.0,
        low=9.5,
        close=11.0,
        period="1D",
        volume=1000,
        currency="USD",
        exchange="NASDAQ",
        source=_source(),
    )
    assert price.period == "1d"
    assert price.value == 11.0
    with pytest.raises(ValidationError):
        HistoricalPrice(
            symbol="MSFT",
            timestamp=_now(),
            open=10.0,
            high=9.0,
            low=9.5,
            close=11.0,
            period="1d",
            source=_source(),
        )


def test_ohlc_series_requires_matching_symbol_and_period() -> None:
    bar = HistoricalPrice(
        symbol="AAPL",
        timestamp=_now(),
        open=1.0,
        high=1.0,
        low=1.0,
        close=1.0,
        period="1d",
        source=_source(),
    )
    series = OhlcSeries(symbol="AAPL", period="1d", prices=[bar], source=_source())
    assert series.prices[0].value == 1.0
    with pytest.raises(ValidationError):
        OhlcSeries(symbol="MSFT", period="1d", prices=[bar], source=_source())


def test_market_index_requires_value_timestamp_and_source() -> None:
    index = MarketIndex(
        symbol="^gspc",
        value=5300.0,
        timestamp=_now(),
        currency="USD",
        source=_source(),
    )
    assert index.symbol == "^GSPC"
    with pytest.raises(ValidationError):
        MarketIndex(symbol="^GSPC", value=5300.0, timestamp=_now())


def test_company_profile_validates_website_employees_and_currency() -> None:
    profile = CompanyProfile(
        symbol="AAPL",
        name="Apple Inc.",
        currency="usd",
        exchange="nasdaq",
        website="https://www.apple.com",
        employees=150000,
        source=_source(),
    )
    assert profile.currency == "USD"
    with pytest.raises(ValidationError):
        CompanyProfile(symbol="AAPL", website="apple.com", source=_source())
    with pytest.raises(ValidationError):
        CompanyProfile(symbol="AAPL", employees=-1, source=_source())


def test_financial_metrics_allow_negative_earnings_but_not_nan() -> None:
    metrics = FinancialMetrics(
        symbol="AAPL",
        period="TTM",
        timestamp=_now(),
        currency="USD",
        net_income=-10.0,
        market_cap=3e12,
        source=_source(),
    )
    assert metrics.period == "ttm"
    with pytest.raises(ValidationError):
        FinancialMetrics(symbol="AAPL", revenue=inf, source=_source())
    with pytest.raises(ValidationError):
        FinancialMetrics(symbol="AAPL", market_cap=-1, source=_source())


def test_financial_statement_validates_period_and_numeric_line_items() -> None:
    statement = FinancialStatement(
        symbol="AAPL",
        statement_type="income",
        period="annual",
        currency="USD",
        period_end=date(2024, 9, 28),
        fiscal_period="FY2024",
        line_items={"revenue": 100.0, "net_income": "see notes"},
        source=_source(),
    )
    assert statement.fiscal_period == "fy2024"
    with pytest.raises(ValidationError):
        FinancialStatement(
            symbol="AAPL",
            statement_type="income",
            period="monthly",
            source=_source(),
        )
    with pytest.raises(ValidationError):
        FinancialStatement(
            symbol="AAPL",
            statement_type="income",
            period="annual",
            line_items={"revenue": nan},
            source=_source(),
        )


def test_news_article_requires_headline_timestamp_and_source() -> None:
    article = NewsArticle(
        headline="  Apple reports earnings  ",
        timestamp=_now(),
        publisher="Reuters",
        symbol="aapl",
        url="https://example.com/news",
        source=_source(source="Reuters"),
    )
    assert article.headline == "Apple reports earnings"
    assert article.symbol == "AAPL"
    with pytest.raises(ValidationError):
        NewsArticle(headline="headline", timestamp=_now())
    with pytest.raises(ValidationError):
        NewsArticle(headline=" ", timestamp=_now(), source=_source())
    with pytest.raises(ValidationError):
        NewsArticle(headline="headline", timestamp=datetime(2024, 1, 1), source=_source())


def test_models_do_not_expose_provider_specific_field_names() -> None:
    forbidden = {
        "regularMarketPrice",
        "adjClose",
        "fiftyTwoWeekHigh",
        "longBusinessSummary",
        "formType",
        "newsapi_id",
        "yfinance",
    }
    for model in (
        MarketQuote,
        HistoricalPrice,
        MarketIndex,
        InstrumentMatch,
        CompanyProfile,
        FinancialMetrics,
        FinancialStatement,
        NewsArticle,
        Evidence,
        DataSourceMetadata,
    ):
        overlap = forbidden.intersection(model.model_fields)
        assert not overlap, f"{model.__name__} leaked {overlap}"


def test_langgraph_builder_compiles() -> None:
    from app.agents.base import AgentContext
    from app.providers.registry import build_providers
    from tests.helpers import make_settings

    graph = build_strategy_graph(AgentContext(providers=build_providers(make_settings())))
    assert "plan" in graph.nodes
    assert "synthesize" in graph.nodes
