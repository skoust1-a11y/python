"""Tests for external-data provider contracts, factories, and selection."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.exceptions import ConfigurationError, ProviderNotImplementedError
from app.main import create_app
from app.models.common import DataSourceMetadata
from app.models.fundamentals import (
    CompanyProfile,
    FinancialMetrics,
    FinancialStatement,
    ReportingPeriod,
    StatementType,
    ValuationMetrics,
)
from app.models.market import (
    InstrumentMatch,
    MarketIndex,
    MarketInfo,
    MarketQuote,
    OhlcSeries,
    VolumeSnapshot,
)
from app.models.news import NewsArticle
from app.providers.contracts import (
    FundamentalDataProvider,
    MarketDataProvider,
    NewsDataProvider,
)
from app.providers.fundamentals.factory import (
    FUNDAMENTAL_DATA_ADAPTERS,
    build_fundamental_data_provider,
)
from app.providers.market_data.factory import MARKET_DATA_ADAPTERS, build_market_data_provider
from app.providers.news.factory import NEWS_ADAPTERS, build_news_data_provider
from app.providers.registry import build_providers
from tests.helpers import make_settings


def _source(provider: str, symbol: str | None = "AAPL") -> DataSourceMetadata:
    return DataSourceMetadata(
        provider=provider,
        source="unit-test",
        timestamp=datetime.now(timezone.utc),
        raw_reference=symbol,
    )


class _FakeMarketDataProvider(MarketDataProvider):
    def __init__(self, settings=None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "fake-market"

    def search_instruments(self, query: str, *, limit: int = 10) -> list[InstrumentMatch]:
        token = query.strip()
        hits = [
            InstrumentMatch(
                symbol="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                source=_source(self.name, "AAPL"),
            ),
            InstrumentMatch(
                symbol="MSFT",
                name="Microsoft Corporation",
                exchange="NASDAQ",
                source=_source(self.name, "MSFT"),
            ),
        ]
        matched = [
            item
            for item in hits
            if token.lower() in item.symbol.lower()
            or (item.name is not None and token.lower() in item.name.lower())
        ]
        return matched[:limit]

    def get_quote(self, instrument: str) -> MarketQuote:
        now = datetime.now(timezone.utc)
        return MarketQuote(
            symbol=instrument,
            value=100.0,
            timestamp=now,
            source=_source(self.name, instrument),
        )

    def get_historical_ohlc(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        interval: str = "1d",
    ) -> OhlcSeries:
        return OhlcSeries(
            symbol=instrument,
            period=interval,
            start=start,
            end=end,
            source=_source(self.name, instrument),
        )

    def get_index(self, symbol: str) -> MarketIndex:
        return MarketIndex(
            symbol=symbol,
            value=5000.0,
            timestamp=datetime.now(timezone.utc),
            source=_source(self.name, symbol),
        )

    def get_volume(self, instrument: str) -> VolumeSnapshot:
        return VolumeSnapshot(
            symbol=instrument,
            value=1_000_000,
            timestamp=datetime.now(timezone.utc),
            source=_source(self.name, instrument),
        )

    def get_market_info(self, instrument: str) -> MarketInfo:
        return MarketInfo(
            symbol=instrument,
            exchange="NYSE",
            source=_source(self.name, instrument),
        )


class _FakeFundamentalDataProvider(FundamentalDataProvider):
    def __init__(self, settings=None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "fake-fundamentals"

    def get_company_profile(self, instrument: str) -> CompanyProfile:
        return CompanyProfile(
            symbol=instrument,
            name="Test Corp",
            source=_source(self.name, instrument),
        )

    def get_financial_statements(
        self,
        instrument: str,
        *,
        statement_type: StatementType = "income",
        period: ReportingPeriod = "annual",
    ) -> list[FinancialStatement]:
        return [
            FinancialStatement(
                symbol=instrument,
                statement_type=statement_type,
                period=period,
                line_items={"revenue": 1.0},
                source=_source(self.name, instrument),
            )
        ]

    def get_key_metrics(self, instrument: str) -> FinancialMetrics:
        return FinancialMetrics(
            symbol=instrument,
            revenue=1.0,
            source=_source(self.name, instrument),
        )

    def get_valuation_metrics(self, instrument: str) -> ValuationMetrics:
        return ValuationMetrics(
            symbol=instrument,
            pe_ratio=10.0,
            source=_source(self.name, instrument),
        )


class _FakeNewsDataProvider(NewsDataProvider):
    def __init__(self, settings=None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "fake-news"

    def get_company_news(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        return [
            NewsArticle(
                headline=f"{instrument} update",
                timestamp=datetime.now(timezone.utc),
                symbol=instrument,
                source=_source(self.name, instrument),
            )
        ]

    def get_market_news(
        self,
        *,
        query: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        return [
            NewsArticle(
                headline=query or "market update",
                timestamp=datetime.now(timezone.utc),
                source=_source(self.name, None),
            )
        ]


def test_build_providers_uses_configured_stub_adapters() -> None:
    providers = build_providers(make_settings())
    assert providers.llm.name == "stub"
    assert providers.market_data.name == "stub"
    assert providers.fundamentals.name == "stub"
    assert providers.news.name == "stub"


def test_unknown_llm_provider_is_rejected() -> None:
    settings = make_settings(llm_provider="not-registered")
    with pytest.raises(ConfigurationError, match="LLM_PROVIDER"):
        build_providers(settings)


def test_unknown_market_data_provider_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="MARKET_DATA_PROVIDER"):
        build_market_data_provider(make_settings(market_data_provider="yahoo-hardcoded"))


def test_unknown_fundamental_data_provider_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="FUNDAMENTAL_DATA_PROVIDER"):
        build_fundamental_data_provider(make_settings(fundamental_data_provider="fmp-hardcoded"))


def test_unknown_news_provider_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="NEWS_PROVIDER"):
        build_news_data_provider(make_settings(news_provider="newsapi-hardcoded"))


def test_unknown_provider_prevents_app_startup() -> None:
    with pytest.raises(ConfigurationError, match="MARKET_DATA_PROVIDER"):
        create_app(make_settings(market_data_provider="yahoo-hardcoded"))


def test_empty_provider_name_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="NEWS_PROVIDER"):
        build_news_data_provider(make_settings(news_provider="   "))


def test_stub_adapters_do_not_invent_external_data() -> None:
    providers = build_providers(make_settings())
    with pytest.raises(ProviderNotImplementedError):
        providers.market_data.search_instruments("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.market_data.get_quote("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.market_data.get_historical_ohlc("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.market_data.get_index("^GSPC")
    with pytest.raises(ProviderNotImplementedError):
        providers.market_data.get_volume("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.market_data.get_market_info("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.fundamentals.get_company_profile("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.fundamentals.get_financial_statements("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.fundamentals.get_key_metrics("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.fundamentals.get_valuation_metrics("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.news.get_company_news("AAPL")
    with pytest.raises(ProviderNotImplementedError):
        providers.news.get_market_news()


def test_provider_selection_is_case_insensitive() -> None:
    providers = build_providers(
        make_settings(
            market_data_provider="STUB",
            fundamental_data_provider="Stub",
            news_provider="stub",
        )
    )
    assert providers.market_data.name == "stub"
    assert providers.fundamentals.name == "stub"
    assert providers.news.name == "stub"


def test_hyphenated_provider_names_normalize_to_registry_keys() -> None:
    providers = build_providers(make_settings(market_data_provider="stub"))
    assert providers.market_data.name == "stub"
    with pytest.raises(ConfigurationError, match="MARKET_DATA_PROVIDER"):
        build_market_data_provider(make_settings(market_data_provider="not-a-vendor"))


def test_environment_variables_select_data_providers(monkeypatch) -> None:
    monkeypatch.setitem(MARKET_DATA_ADAPTERS, "fake_market", _FakeMarketDataProvider)
    monkeypatch.setitem(FUNDAMENTAL_DATA_ADAPTERS, "fake_fundamentals", _FakeFundamentalDataProvider)
    monkeypatch.setitem(NEWS_ADAPTERS, "fake_news", _FakeNewsDataProvider)
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "fake-market")
    monkeypatch.setenv("FUNDAMENTAL_DATA_PROVIDER", "fake-fundamentals")
    monkeypatch.setenv("NEWS_PROVIDER", "fake-news")

    settings = Settings(_env_file=None)
    providers = build_providers(settings)
    assert settings.market_data_provider == "fake-market"
    assert settings.fundamental_data_provider == "fake-fundamentals"
    assert settings.news_provider == "fake-news"
    assert providers.market_data.name == "fake-market"
    assert providers.fundamentals.name == "fake-fundamentals"
    assert providers.news.name == "fake-news"


def test_independent_market_adapter_can_be_registered(monkeypatch) -> None:
    monkeypatch.setitem(MARKET_DATA_ADAPTERS, "fake_market", _FakeMarketDataProvider)
    provider = build_market_data_provider(make_settings(market_data_provider="fake-market"))
    assert provider.name == "fake-market"
    quote = provider.get_quote("AAPL")
    assert quote.value == 100.0
    assert quote.source.provider == "fake-market"


def test_independent_fundamental_adapter_can_be_registered(monkeypatch) -> None:
    monkeypatch.setitem(FUNDAMENTAL_DATA_ADAPTERS, "fake_fundamentals", _FakeFundamentalDataProvider)
    provider = build_fundamental_data_provider(
        make_settings(fundamental_data_provider="fake_fundamentals")
    )
    assert provider.name == "fake-fundamentals"
    profile = provider.get_company_profile("AAPL")
    assert profile.name == "Test Corp"


def test_independent_news_adapter_can_be_registered(monkeypatch) -> None:
    monkeypatch.setitem(NEWS_ADAPTERS, "fake_news", _FakeNewsDataProvider)
    provider = build_news_data_provider(make_settings(news_provider="fake-news"))
    assert provider.name == "fake-news"
    items = provider.get_company_news("MSFT")
    assert items[0].headline == "MSFT update"


def test_build_providers_selects_independently_registered_adapters(monkeypatch) -> None:
    monkeypatch.setitem(MARKET_DATA_ADAPTERS, "fake_market", _FakeMarketDataProvider)
    monkeypatch.setitem(FUNDAMENTAL_DATA_ADAPTERS, "fake_fundamentals", _FakeFundamentalDataProvider)
    monkeypatch.setitem(NEWS_ADAPTERS, "fake_news", _FakeNewsDataProvider)
    providers = build_providers(
        make_settings(
            market_data_provider="fake-market",
            fundamental_data_provider="fake-fundamentals",
            news_provider="fake-news",
        )
    )
    assert providers.market_data.name == "fake-market"
    assert providers.fundamentals.name == "fake-fundamentals"
    assert providers.news.name == "fake-news"
    assert providers.llm.name == "stub"


def test_create_app_instantiates_configured_data_providers(monkeypatch) -> None:
    monkeypatch.setitem(MARKET_DATA_ADAPTERS, "fake_market", _FakeMarketDataProvider)
    application = create_app(
        make_settings(app_env="test", market_data_provider="fake-market")
    )
    assert application.state.providers.market_data.name == "fake-market"
    assert application.state.providers.fundamentals.name == "stub"


def test_market_data_contract_exposes_provider_independent_operations() -> None:
    assert MarketDataProvider.search_instruments.__isabstractmethod__
    assert MarketDataProvider.get_quote.__isabstractmethod__
    assert MarketDataProvider.get_historical_ohlc.__isabstractmethod__
    assert MarketDataProvider.get_index.__isabstractmethod__
    assert MarketDataProvider.get_volume.__isabstractmethod__
    assert MarketDataProvider.get_market_info.__isabstractmethod__


def test_fundamental_data_contract_exposes_provider_independent_operations() -> None:
    assert FundamentalDataProvider.get_company_profile.__isabstractmethod__
    assert FundamentalDataProvider.get_financial_statements.__isabstractmethod__
    assert FundamentalDataProvider.get_key_metrics.__isabstractmethod__
    assert FundamentalDataProvider.get_valuation_metrics.__isabstractmethod__


def test_news_data_contract_exposes_provider_independent_operations() -> None:
    assert NewsDataProvider.get_company_news.__isabstractmethod__
    assert NewsDataProvider.get_market_news.__isabstractmethod__


def test_contracts_do_not_expose_vendor_api_details() -> None:
    source = Path("app/providers/contracts.py").read_text(encoding="utf-8").lower()
    for token in (
        "yfinance",
        "alpha_vantage",
        "polygon",
        "finnhub",
        "newsapi",
        "api_key",
        "base_url",
        "/v1/",
    ):
        assert token not in source


def test_agents_depend_on_injected_bundle_not_concrete_data_adapters() -> None:
    agents_root = Path("app/agents")
    forbidden = (
        "StubMarketDataProvider",
        "StubFundamentalDataProvider",
        "StubNewsDataProvider",
        "StubNewsProvider",
        "yfinance",
        "alpha_vantage",
        "polygon",
        "finnhub",
        "newsapi",
        "MARKET_DATA_ADAPTERS",
        "FUNDAMENTAL_DATA_ADAPTERS",
        "NEWS_ADAPTERS",
    )
    for path in agents_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text
    assert "from app.providers.registry import ProviderBundle" in (
        agents_root / "base.py"
    ).read_text(encoding="utf-8")
