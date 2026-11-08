from datetime import datetime, timedelta, timezone

from app.current import _news_from_search, _quote_from_chart, resolve_symbols


def test_resolve_seeded_and_indian_names():
    symbols = resolve_symbols(
        "What is Apple and RELIANCE trading at on NSE?",
        [{"rows": [{"asset_name": "Tesla"}, {"asset_name": "Gold ETF"}]}],
    )
    assert "AAPL" in symbols
    assert "RELIANCE.NS" in symbols
    assert "TSLA" in symbols
    assert "GLD" in symbols
    assert "^NSEI" in symbols


def test_quote_and_news_parsers():
    as_of = datetime.now(timezone.utc) - timedelta(seconds=30)
    quote = _quote_from_chart(
        "AAPL",
        {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "symbol": "AAPL",
                            "regularMarketPrice": 190.25,
                            "regularMarketTime": int(as_of.timestamp()),
                        }
                    }
                ]
            }
        },
        stale_after=900,
    )
    assert quote is not None
    assert quote["symbol"] == "AAPL"
    assert quote["price"] == 190.25
    assert quote["provider_id"] == "yahoo"
    assert quote["stale"] is False

    news = _news_from_search(
        {
            "news": [
                {
                    "title": "Apple reports",
                    "link": "https://example.test/aapl",
                    "publisher": "Yahoo Finance",
                    "providerPublishTime": int(as_of.timestamp()),
                }
            ]
        },
        max_age=timedelta(hours=48),
        limit=4,
    )
    assert news[0]["headline"] == "Apple reports"
    assert news[0]["url"] == "https://example.test/aapl"
