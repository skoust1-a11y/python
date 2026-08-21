"""Yahoo Finance news adapter tests. Network calls are mocked."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.exceptions import ConfigurationError
from app.main import create_app
from app.providers.news.factory import NEWS_ADAPTERS, build_news_data_provider
from app.providers.news.yahoo import YahooNewsDataProvider
from tests.helpers import make_settings

UTC = timezone.utc
NOW = datetime(2024, 6, 15, 10, 0, tzinfo=UTC)


class _FakeNewsTicker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.news = [
            {
                "id": "item-1",
                "title": "Reliance Expands Clean Energy Operations",
                "pubDate": "2024-06-15T09:00:00Z",
                "summary": "Reliance Industries announces new green initiative.",
                "link": "https://finance.yahoo.com/news/reliance-expands-clean-energy.html",
                "publisher": "Reuters",
            }
        ]


class _FakeNewsSearch:
    def __init__(self, query: str, news_count: int = 20) -> None:
        self.query = query
        self.news = [
            {
                "content": {
                    "id": "item-market-1",
                    "title": "Global Markets Rally Following Policy Announcement",
                    "pubDate": "2024-06-15T08:30:00Z",
                    "summary": "Major indices hit fresh milestones.",
                    "canonicalUrl": {"url": "https://finance.yahoo.com/news/global-markets-rally.html"},
                    "provider": {"displayName": "Bloomberg"},
                }
            }
        ][:news_count]


class _FakeNewsYahoo:
    def __init__(self, tickers: dict[str, _FakeNewsTicker] | None = None) -> None:
        self.tickers = tickers or {"RELIANCE.NS": _FakeNewsTicker("RELIANCE.NS")}
        self.Search = _FakeNewsSearch

    def Ticker(self, symbol: str) -> _FakeNewsTicker:
        return self.tickers.get(symbol, _FakeNewsTicker(symbol))


def test_yahoo_is_a_registered_news_adapter() -> None:
    assert "yahoo" in NEWS_ADAPTERS
    provider = build_news_data_provider(make_settings(news_provider="yahoo"))
    assert isinstance(provider, YahooNewsDataProvider)
    assert provider.name == "yahoo"


def test_yfinance_alias_selects_yahoo_news_adapter() -> None:
    provider = build_news_data_provider(make_settings(news_provider="yfinance"))
    assert provider.name == "yahoo"


def test_create_app_accepts_yahoo_news_provider() -> None:
    application = create_app(make_settings(app_env="test", news_provider="yahoo"))
    assert application.state.providers.news.name == "yahoo"


def test_yahoo_get_company_news() -> None:
    provider = YahooNewsDataProvider(client=_FakeNewsYahoo())
    articles = provider.get_company_news("RELIANCE", limit=5)
    assert len(articles) == 1
    assert articles[0].headline == "Reliance Expands Clean Energy Operations"
    assert articles[0].publisher == "Reuters"
    assert articles[0].symbol == "RELIANCE"
    assert articles[0].source.provider == "yahoo"


def test_yahoo_get_market_news() -> None:
    provider = YahooNewsDataProvider(client=_FakeNewsYahoo())
    articles = provider.get_market_news(query="markets", limit=5)
    assert len(articles) == 1
    assert articles[0].headline == "Global Markets Rally Following Policy Announcement"
    assert articles[0].publisher == "Bloomberg"
    assert articles[0].source.provider == "yahoo"


def test_unknown_news_data_provider_rejected() -> None:
    with pytest.raises(ConfigurationError, match="NEWS_PROVIDER"):
        build_news_data_provider(make_settings(news_provider="unknown-provider"))
