"""End-to-end HTTP journeys used by the frontend screens."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agents.manager import FUNDAMENTAL_AGENT, MARKET_AGENT
from app.main import FRONTEND_CORS_ORIGINS, create_app
from app.providers.market_data.yahoo import YahooMarketDataProvider
from app.providers.registry import ProviderBundle
from tests.helpers import csv_bytes, make_settings
from tests.test_portfolio import VALID_HEADERS, VALID_ROWS, _upload
from tests.test_portfolio_analysis import _import_portfolio
from tests.test_stocks import _FakeFundamentalDataProvider, _FakeLLM, _stock_app
from tests.test_workflow import _specialists
from tests.test_yahoo_market import _FakeTicker, _FakeYahoo, NOW


def _journey_app():
    specialists = _specialists(
        extras={
            MARKET_AGENT: {"trend": "uptrend", "unavailable": []},
            FUNDAMENTAL_AGENT: {"financial_health": "stressed", "unavailable": []},
        }
    )
    return _stock_app(specialists=specialists, llm=_FakeLLM()), specialists


def test_frontend_can_call_api_from_vite_origin() -> None:
    application = create_app(make_settings(app_env="test", log_level="WARNING"))
    with TestClient(application) as client:
        origin = FRONTEND_CORS_ORIGINS[0]
        response = client.options(
            "/dashboard",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in {200, 204}
        assert response.headers["access-control-allow-origin"] == origin


def test_journeys_upload_analyze_stock_watchlist_and_dashboard() -> None:
    application, specialists = _journey_app()
    with TestClient(application) as client:
        preview = _upload(client, "holdings.csv", csv_bytes(VALID_HEADERS, VALID_ROWS)).json()
        assert preview["status"] in {"valid", "valid_with_warnings"}
        assert preview["can_confirm"] is True
        assert preview["upload_id"]

        confirmed = client.post(
            f"/portfolios/uploads/{preview['upload_id']}/confirm",
            json={"name": "Core holdings"},
        )
        assert confirmed.status_code == 200
        portfolio = confirmed.json()
        portfolio_id = portfolio["id"]
        assert portfolio["holding_count"] == 2
        assert client.get("/portfolios").json()[0]["id"] == portfolio_id
        detail = client.get(f"/portfolios/{portfolio_id}")
        assert detail.status_code == 200
        assert [item["symbol"] for item in detail.json()["holdings"]] == ["AAPL", "MSFT"]

        analysis = client.post(
            f"/portfolios/{portfolio_id}/analysis",
            json={
                "question": "Review this portfolio using current market and fundamental information.",
                "analysis_type": "portfolio_review",
            },
        )
        assert analysis.status_code == 200
        report = analysis.json()
        agents = [item["agent"] for item in report["specialist_results"]]
        assert "market-analysis" in agents
        assert "fundamental-analysis" in agents
        assert "portfolio-manager" in agents
        assert report["recommendation"]["summary"]
        assert report["critiques"]
        assert report["critiques"][0]["author"]
        assert report["critiques"][0]["message"]
        assert report["evidence"][0]["source"]["provider"]
        assert report["evidence"][0]["source"]["source"]
        assert report["evidence"][0]["source"]["timestamp"]
        assert specialists[MARKET_AGENT].calls
        assert specialists[FUNDAMENTAL_AGENT].calls

        holding = client.get("/stocks/AAPL")
        assert holding.status_code == 200
        assert holding.json()["symbol"] == "AAPL"

        stock_report = client.post(
            "/stocks/AAPL/analysis",
            json={"question": "What is the current market trend for AAPL?", "analysis_type": "stock_analysis"},
        )
        assert stock_report.status_code == 200
        assert stock_report.json()["symbol"] == "AAPL"
        assert "critiques" in stock_report.json()

        added = client.post("/watchlist", json={"symbol": "AAPL"})
        assert added.status_code == 200
        watched = added.json()
        assert watched["symbol"] == "AAPL"
        assert watched["analyzer_path"] == "/stocks/AAPL"
        assert watched["quote"]["timestamp"]
        assert watched["quote"]["source"]["provider"]
        assert client.get("/watchlist").json()[0]["symbol"] == "AAPL"

        opened = client.post("/watchlist/AAPL/open")
        assert opened.status_code == 200
        assert opened.json()["symbol"] == "AAPL"
        assert opened.json()["analyzer_path"] == "/stocks/AAPL"
        assert opened.json()["overview"]["symbol"] == "AAPL"

        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        overview = dashboard.json()
        assert overview["portfolio"]["id"] == portfolio_id
        assert overview["portfolio"]["imported_at"]
        assert overview["market"]["provider"]


def test_yahoo_market_adapter_feeds_dashboard_timestamps_and_sources() -> None:
    tickers = {
        "^NSEI": _FakeTicker("^NSEI"),
        "^BSESN": _FakeTicker(
            "^BSESN",
            info={
                "shortName": "SENSEX",
                "regularMarketPrice": 77200.0,
                "regularMarketPreviousClose": 76890.0,
                "regularMarketChange": 310.0,
                "regularMarketChangePercent": 0.40,
                "regularMarketTime": NOW.timestamp(),
                "currency": "INR",
                "exchange": "BSE",
                "quoteType": "INDEX",
                "marketState": "REGULAR",
                "exchangeTimezoneName": "Asia/Kolkata",
            },
        ),
        "^NSEBANK": _FakeTicker(
            "^NSEBANK",
            info={
                "shortName": "NIFTY Bank",
                "regularMarketPrice": 51200.0,
                "regularMarketPreviousClose": 51280.0,
                "regularMarketChange": -80.0,
                "regularMarketChangePercent": -0.16,
                "regularMarketTime": NOW.timestamp(),
                "currency": "INR",
                "exchange": "NSI",
                "quoteType": "INDEX",
                "marketState": "REGULAR",
                "exchangeTimezoneName": "Asia/Kolkata",
            },
        ),
        "^CNXIT": _FakeTicker(
            "^CNXIT",
            info={
                "shortName": "NIFTY IT",
                "regularMarketPrice": 42100.0,
                "regularMarketPreviousClose": 41890.0,
                "regularMarketChange": 210.0,
                "regularMarketChangePercent": 0.50,
                "regularMarketTime": NOW.timestamp(),
                "currency": "INR",
                "exchange": "NSI",
                "quoteType": "INDEX",
                "marketState": "REGULAR",
                "exchangeTimezoneName": "Asia/Kolkata",
            },
        ),
        "AAPL": _FakeTicker(
            "AAPL",
            info={
                "shortName": "Apple Inc.",
                "regularMarketPrice": 190.25,
                "regularMarketPreviousClose": 188.0,
                "regularMarketChange": 2.25,
                "regularMarketChangePercent": 1.2,
                "regularMarketTime": NOW.timestamp(),
                "currency": "USD",
                "exchange": "NMS",
                "quoteType": "EQUITY",
                "marketState": "REGULAR",
            },
        ),
        "MSFT": _FakeTicker(
            "MSFT",
            info={
                "shortName": "Microsoft Corporation",
                "regularMarketPrice": 420.0,
                "regularMarketPreviousClose": 418.0,
                "regularMarketChange": 2.0,
                "regularMarketChangePercent": 0.48,
                "regularMarketTime": NOW.timestamp(),
                "currency": "USD",
                "exchange": "NMS",
                "quoteType": "EQUITY",
                "marketState": "REGULAR",
            },
        ),
    }
    for ticker in tickers.values():
        ticker.fast_info = SimpleNamespace(
            last_price=ticker.info["regularMarketPrice"],
            previous_close=ticker.info["regularMarketPreviousClose"],
            last_volume=1_000_000,
            currency=ticker.info["currency"],
            exchange=ticker.info["exchange"],
            timezone=ticker.info.get("exchangeTimezoneName"),
        )
    application = create_app(
        make_settings(app_env="test", log_level="WARNING", market_data_provider="yahoo")
    )
    bundle = application.state.providers
    application.state.providers = ProviderBundle(
        llm=_FakeLLM(),
        market_data=YahooMarketDataProvider(client=_FakeYahoo(tickers)),
        fundamentals=_FakeFundamentalDataProvider(),
        news=bundle.news,
    )
    with TestClient(application) as client:
        _import_portfolio(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        market = response.json()["market"]
        assert market["provider"] == "yahoo"
        assert market["nifty50"]["value"] == 23500.0
        assert market["nifty50"]["timestamp"]
        assert market["as_of"]
        assert market["evidence"]
        sources = {item["source"]["source"] for item in market["evidence"]}
        assert sources == {"yahoo-finance"}
        providers = {item["source"]["provider"] for item in market["evidence"]}
        assert providers == {"yahoo"}
        assert all(item["source"]["timestamp"] for item in market["evidence"])
        urls = {item["source"]["url"] for item in market["evidence"] if item["source"]["url"]}
        assert any("finance.yahoo.com/quote/" in url for url in urls)
        portfolio = response.json()["portfolio"]
        assert portfolio["quoted_holding_count"] == 2
        assert portfolio["evidence"][0]["source"]["provider"] == "yahoo"
        quote = client.get("/stocks/AAPL")
        assert quote.status_code == 200
        assert quote.json()["quote"]["source"]["provider"] == "yahoo"
        assert quote.json()["quote"]["source"]["source"] == "yahoo-finance"
        assert quote.json()["quote"]["timestamp"]


def test_stock_analyzer_add_and_open_watchlist_stay_independent_of_portfolio() -> None:
    application = _stock_app()
    with TestClient(application) as client:
        selected = client.post("/stocks/select", json={"symbol": "AAPL"})
        assert selected.status_code == 200
        added = client.post("/watchlist", json={"symbol": "AAPL"})
        assert added.status_code == 200
        opened = client.post("/watchlist/AAPL/open")
        assert opened.status_code == 200
        assert opened.json()["analyzer_path"] == "/stocks/AAPL"
        assert client.get("/portfolios").json() == []
