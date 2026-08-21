"""Stock Analyzer HTTP API tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.exceptions import ProviderError, ProviderNotImplementedError
from app.main import create_app
from app.models.analysis import StockAnalysisResult
from app.models.common import DataSourceMetadata
from app.models.fundamentals import CompanyProfile, FinancialMetrics, ValuationMetrics
from app.models.market import (
    HistoricalPrice,
    InstrumentMatch,
    MarketInfo,
    MarketQuote,
    OhlcSeries,
    VolumeSnapshot,
)
from app.providers.contracts import FundamentalDataProvider, MarketDataProvider
from app.providers.registry import ProviderBundle
from app.services.analysis import public_stock_analysis_result
from app.workflow.state import (
    AgentResultSnapshot,
    ExecutionMetadata,
    FinalRecommendation,
    SelectedStock,
    UserRequest,
    create_investment_state,
)
from tests.helpers import make_settings
from tests.test_portfolio_analysis import HIDDEN_KEYS, _collect_keys, _import_portfolio
from tests.test_workflow import SYNTHESIS, _FakeLLM, _specialists

UTC = timezone.utc
NOW = datetime(2024, 6, 15, 14, 30, tzinfo=UTC)


def _source(provider: str, symbol: str | None = "AAPL") -> DataSourceMetadata:
    return DataSourceMetadata(
        provider=provider,
        source="unit-test",
        timestamp=NOW,
        raw_reference=symbol,
    )


class _FakeMarketDataProvider(MarketDataProvider):
    def __init__(self, settings=None) -> None:
        self._settings = settings
        self.search_queries: list[tuple[str, int]] = []

    @property
    def name(self) -> str:
        return "fake-market"

    def search_instruments(self, query: str, *, limit: int = 10) -> list[InstrumentMatch]:
        self.search_queries.append((query, limit))
        catalog = [
            InstrumentMatch(
                symbol="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                currency="USD",
                source=_source(self.name, "AAPL"),
            ),
            InstrumentMatch(
                symbol="MSFT",
                name="Microsoft Corporation",
                exchange="NASDAQ",
                currency="USD",
                source=_source(self.name, "MSFT"),
            ),
        ]
        token = query.strip().lower()
        matches = [
            item
            for item in catalog
            if token in item.symbol.lower()
            or (item.name is not None and token in item.name.lower())
        ]
        return matches[:limit]

    def _reject_unknown(self, instrument: str) -> None:
        if instrument.upper() == "MISSING":
            raise ProviderError("unknown instrument")

    def get_quote(self, instrument: str) -> MarketQuote:
        self._reject_unknown(instrument)
        return MarketQuote(
            symbol=instrument,
            value=190.25,
            timestamp=NOW,
            currency="USD",
            exchange="NASDAQ",
            change_percent=1.5,
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
        self._reject_unknown(instrument)
        prices = [
            HistoricalPrice(
                symbol=instrument,
                timestamp=datetime(2024, 1, 2 + day, 21, 0, tzinfo=UTC),
                open=100.0 + day,
                high=101.0 + day,
                low=99.0 + day,
                close=100.5 + day,
                period=interval,
                source=_source(self.name, instrument),
            )
            for day in range(25)
        ]
        return OhlcSeries(
            symbol=instrument,
            period=interval,
            source=_source(self.name, instrument),
            prices=prices,
        )

    def get_index(self, symbol: str) -> Any:
        raise ProviderError("index is not required for stock retrieval tests")

    def get_volume(self, instrument: str) -> VolumeSnapshot:
        self._reject_unknown(instrument)
        return VolumeSnapshot(
            symbol=instrument,
            value=50_000_000,
            timestamp=NOW,
            source=_source(self.name, instrument),
        )

    def get_market_info(self, instrument: str) -> MarketInfo:
        self._reject_unknown(instrument)
        return MarketInfo(
            symbol=instrument,
            name="Apple Inc." if instrument.upper() == "AAPL" else instrument,
            exchange="NASDAQ",
            currency="USD",
            asset_class="equity",
            source=_source(self.name, instrument),
        )


class _FakeFundamentalDataProvider(FundamentalDataProvider):
    def __init__(self, settings=None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "fake-fundamentals"

    def get_company_profile(self, instrument: str) -> CompanyProfile:
        if instrument.upper() == "MISSING":
            raise ProviderError("unknown instrument")
        return CompanyProfile(
            symbol=instrument,
            name="Apple Inc." if instrument.upper() == "AAPL" else "Test Corp",
            sector="Technology",
            industry="Consumer Electronics",
            source=_source(self.name, instrument),
        )

    def get_financial_statements(self, instrument: str, **kwargs: Any) -> list:
        return []

    def get_key_metrics(self, instrument: str) -> FinancialMetrics:
        if instrument.upper() == "MISSING":
            raise ProviderError("unknown instrument")
        return FinancialMetrics(
            symbol=instrument,
            revenue=394_328_000_000,
            net_income=96_995_000_000,
            pe_ratio=28.5,
            timestamp=NOW,
            source=_source(self.name, instrument),
        )

    def get_valuation_metrics(self, instrument: str) -> ValuationMetrics:
        if instrument.upper() == "MISSING":
            raise ProviderError("unknown instrument")
        return ValuationMetrics(
            symbol=instrument,
            pe_ratio=28.5,
            market_cap=3_000_000_000_000,
            source=_source(self.name, instrument),
        )


def _stock_app(*, specialists=None, llm=None, market=None, fundamentals=None):
    application = create_app(make_settings(app_env="test", log_level="WARNING"))
    bundle = application.state.providers
    application.state.providers = ProviderBundle(
        llm=llm or _FakeLLM(),
        market_data=market or _FakeMarketDataProvider(),
        fundamentals=fundamentals or _FakeFundamentalDataProvider(),
        news=bundle.news,
    )
    if specialists is not None:
        application.state.workflow_specialists = specialists
    return application


def test_search_returns_provider_matches_without_hardcoded_vendor_logic() -> None:
    market = _FakeMarketDataProvider()
    application = _stock_app(market=market)
    with TestClient(application) as client:
        response = client.get("/stocks/search", params={"q": "apple", "limit": 5})
        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "apple"
        assert body["matches"][0]["symbol"] == "AAPL"
        assert body["matches"][0]["name"] == "Apple Inc."
        assert body["matches"][0]["source"]["provider"] == "fake-market"
        assert market.search_queries == [("apple", 5)]
        empty = client.get("/stocks/search", params={"q": "no-such-name"})
        assert empty.status_code == 200
        assert empty.json()["matches"] == []


def test_search_requires_query_and_does_not_use_stub_invention() -> None:
    application = create_app(make_settings(app_env="test", log_level="WARNING"))
    with TestClient(application) as client:
        missing = client.get("/stocks/search")
        assert missing.status_code == 422
        blank = client.get("/stocks/search", params={"q": "   "})
        assert blank.status_code == 422
        stubbed = client.get("/stocks/search", params={"q": "AAPL"})
        assert stubbed.status_code == 501
        assert stubbed.json()["error"]["code"] == "provider_not_implemented"


def test_stock_retrieval_returns_current_market_and_fundamental_data() -> None:
    application = _stock_app()
    with TestClient(application) as client:
        selected = client.post("/stocks/select", json={"symbol": "aapl"})
        assert selected.status_code == 200
        overview = selected.json()
        assert overview["symbol"] == "AAPL"
        assert overview["name"] == "Apple Inc."
        assert overview["selected"]["symbol"] == "AAPL"
        assert overview["quote"]["value"] == 190.25
        assert overview["quote"]["source"]["provider"] == "fake-market"
        assert overview["profile"]["sector"] == "Technology"
        assert overview["evidence"]
        assert overview["evidence"][0]["source"]["timestamp"]

        current = client.get("/stocks/AAPL")
        assert current.status_code == 200
        assert current.json()["quote"]["value"] == 190.25

        market = client.get("/stocks/AAPL/market")
        assert market.status_code == 200
        market_body = market.json()
        assert market_body["quote"]["value"] == 190.25
        assert market_body["volume"]["value"] == 50_000_000
        assert market_body["history"]["prices"]
        assert market_body["snapshot"]["current_price"] == 190.25
        assert market_body["snapshot"]["trend"] == "uptrend"
        assert market_body["evidence"][0]["source"]["provider"] == "fake-market"

        fundamentals = client.get("/stocks/AAPL/fundamentals")
        assert fundamentals.status_code == 200
        fund_body = fundamentals.json()
        assert fund_body["metrics"]["revenue"] == 394_328_000_000
        assert fund_body["valuation"]["pe_ratio"] == 28.5
        assert fund_body["snapshot"]["profitability"] == "profitable"
        assert fund_body["evidence"][0]["source"]["provider"] == "fake-fundamentals"


def test_stock_retrieval_is_independent_of_uploaded_portfolio() -> None:
    application = _stock_app()
    with TestClient(application) as client:
        portfolio_id = _import_portfolio(client)
        search = client.get("/stocks/search", params={"q": "MSFT"})
        assert search.status_code == 200
        assert search.json()["matches"][0]["symbol"] == "MSFT"
        overview = client.get("/stocks/MSFT")
        assert overview.status_code == 200
        assert overview.json()["symbol"] == "MSFT"
        assert "portfolio_id" not in overview.json()
        listed = client.get(f"/portfolios/{portfolio_id}")
        assert listed.status_code == 200
        assert listed.json()["holding_count"] == 2


def test_suggested_questions_and_custom_analysis_request() -> None:
    specialists = _specialists()
    llm = _FakeLLM()
    application = _stock_app(specialists=specialists, llm=llm)
    with TestClient(application) as client:
        questions = client.get("/stocks/aapl/questions")
        assert questions.status_code == 200
        payload = questions.json()
        assert payload["symbol"] == "AAPL"
        assert len(payload["questions"]) >= 3
        suggested = payload["questions"][0]["question"]
        assert "AAPL" in suggested

        listed = client.get("/stocks/AAPL/analysis")
        assert listed.status_code == 200
        assert listed.json() == []

        custom = client.post(
            "/stocks/AAPL/analysis",
            json={"question": "Is AAPL overvalued on available metrics?"},
        )
        assert custom.status_code == 200
        body = custom.json()
        assert body["symbol"] == "AAPL"
        assert "portfolio_id" not in body
        assert body["question"] == "Is AAPL overvalued on available metrics?"
        assert body["analysis_type"] == "stock_analysis"
        assert body["status"] == "completed"
        assert body["recommendation"]["summary"] == SYNTHESIS["summary"]
        assert body["recommendation"]["trade_execution"] == "not_implemented"
        assert body["evidence"]
        assert body["evidence"][0]["source"]["provider"]
        assert body["evidence"][0]["source"]["source"]
        assert body["evidence"][0]["source"]["timestamp"]
        specialists_names = [item["agent"] for item in body["specialist_results"]]
        assert "market-analysis" in specialists_names
        assert "fundamental-analysis" in specialists_names
        assert "risk-assessment" in specialists_names
        assert "portfolio-optimization" not in specialists_names
        assert not specialists["portfolio-optimization"].calls
        assert all("extras" not in item for item in body["specialist_results"])
        assert HIDDEN_KEYS & _collect_keys(body) == set()

        suggested_run = client.post("/stocks/AAPL/analysis", json={"question": suggested})
        assert suggested_run.status_code == 200
        assert suggested_run.json()["question"] == suggested

        analysis_id = body["id"]
        replay = client.get(f"/stocks/AAPL/analysis/{analysis_id}")
        assert replay.status_code == 200
        assert replay.json()["id"] == analysis_id
        summaries = client.get("/stocks/AAPL/analysis")
        assert summaries.status_code == 200
        assert {item["id"] for item in summaries.json()} == {
            analysis_id,
            suggested_run.json()["id"],
        }
        assert "recommendation" not in summaries.json()[0]


def test_stock_analysis_does_not_require_a_portfolio() -> None:
    specialists = _specialists()
    application = _stock_app(specialists=specialists, llm=_FakeLLM())
    with TestClient(application) as client:
        assert client.get("/portfolios").json() == []
        response = client.post(
            "/stocks/MSFT/analysis",
            json={"question": "Summarize MSFT using retrieved evidence."},
        )
        assert response.status_code == 200
        assert response.json()["symbol"] == "MSFT"
        assert client.get("/portfolios").json() == []
        empty = client.post("/stocks/MSFT/analysis", json={})
        assert empty.status_code == 422
        invalid_type = client.post(
            "/stocks/MSFT/analysis",
            json={"question": "Review MSFT", "analysis_type": "portfolio_risk"},
        )
        assert invalid_type.status_code == 422
        watchlist = client.get("/watchlist")
        assert watchlist.status_code == 200
        assert watchlist.json() == []
        assert client.get("/stocks").status_code == 404


def test_unknown_stock_and_analysis_are_not_found() -> None:
    application = _stock_app()
    with TestClient(application) as client:
        missing = client.get("/stocks/MISSING")
        assert missing.status_code == 404
        unknown = client.get("/stocks/AAPL/analysis/does-not-exist")
        assert unknown.status_code == 404
        invalid = client.get("/stocks/AAPL_US")
        assert invalid.status_code == 422


def test_stub_providers_do_not_invent_stock_data() -> None:
    application = create_app(make_settings(app_env="test", log_level="WARNING"))
    with TestClient(application) as client:
        overview = client.get("/stocks/AAPL")
        assert overview.status_code == 501
        market = client.get("/stocks/AAPL/market")
        assert market.status_code == 501
        fundamentals = client.get("/stocks/AAPL/fundamentals")
        assert fundamentals.status_code == 501
        questions = client.get("/stocks/AAPL/questions")
        assert questions.status_code == 200
        assert questions.json()["questions"]


def test_public_stock_mapper_omits_graph_internals() -> None:
    state = create_investment_state(
        "sa-1",
        user_request=UserRequest(
            text="Review AAPL",
            symbols=["AAPL"],
            analysis_type="stock_analysis",
        ),
        selected_stock=SelectedStock(symbol="AAPL", name="Apple Inc."),
    )
    state["final_recommendation"] = FinalRecommendation(
        summary="Hold.",
        recommendation="Do not place trades.",
        findings=["Trend is constructive."],
        confidence=0.6,
    )
    state["agent_results"] = {
        "market-analysis": AgentResultSnapshot(
            agent="market-analysis",
            role="market-analyst",
            status="succeeded",
            summary="Uptrend",
            findings=["Price sits above the long average."],
            confidence=0.7,
            error_code="internal-code",
            error_message=None,
        )
    }
    state["execution"] = ExecutionMetadata(
        status="completed",
        current_node="synthesize",
        requested_agents=["market-analysis"],
        invoked_agents=["market-analysis"],
        duration_ms=9.0,
        llm_provider="fake-llm",
        llm_model="hidden-model",
        reflection_cycle=1,
        errors=[],
    )
    result = public_stock_analysis_result(state, symbol="AAPL")
    dumped = result.model_dump(mode="json")
    assert dumped["id"] == "sa-1"
    assert dumped["symbol"] == "AAPL"
    assert "portfolio_id" not in dumped
    assert dumped["specialist_results"][0]["agent"] == "market-analysis"
    assert "error_code" not in dumped["specialist_results"][0]
    assert "current_node" not in dumped["execution"]
    assert "llm_provider" not in dumped["execution"]
    assert dumped["critiques"] == []
    assert HIDDEN_KEYS & _collect_keys(dumped) == set()
    StockAnalysisResult.model_validate(dumped)


def test_stock_service_depends_on_contracts_not_vendor_adapters() -> None:
    from pathlib import Path

    text = Path("app/services/stock.py").read_text(encoding="utf-8")
    for token in (
        "StubMarketDataProvider",
        "StubFundamentalDataProvider",
        "yfinance",
        "alpha_vantage",
        "polygon",
        "finnhub",
        "MARKET_DATA_ADAPTERS",
    ):
        assert token not in text


def test_unimplemented_search_adapter_is_not_replaced_by_hardcoded_listings() -> None:
    class _NoSearchMarket(_FakeMarketDataProvider):
        def search_instruments(self, query: str, *, limit: int = 10) -> list[InstrumentMatch]:
            raise ProviderNotImplementedError("Instrument search is not implemented.")

    application = _stock_app(market=_NoSearchMarket())
    with TestClient(application) as client:
        response = client.get("/stocks/search", params={"q": "AAPL"})
        assert response.status_code == 501
        assert response.json()["error"]["code"] == "provider_not_implemented"
