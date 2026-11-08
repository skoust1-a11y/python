"""Portfolio analysis HTTP API tests."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.analysis import PortfolioAnalysisResult
from app.providers.registry import ProviderBundle
from app.services.analysis import public_analysis_result
from app.workflow.state import (
    AgentResultSnapshot,
    ExecutionMetadata,
    FinalRecommendation,
    UserRequest,
    create_investment_state,
    CritiqueRecord,
)
from tests.helpers import csv_bytes, make_settings
from tests.test_portfolio import VALID_HEADERS, VALID_ROWS, _upload
from tests.test_workflow import SYNTHESIS, _FakeLLM, _portfolio, _specialists

HIDDEN_KEYS = {
    "chain_of_thought",
    "chainOfThought",
    "reasoning",
    "scratchpad",
    "thoughts",
    "extras",
    "current_node",
    "messages",
    "artifacts",
    "reflection_cycle",
    "critique_findings",
    "pending_findings",
}


def _analysis_app(*, specialists=None, llm=None):
    application = create_app(make_settings(app_env="test", log_level="WARNING"))
    bundle = application.state.providers
    application.state.providers = ProviderBundle(
        llm=llm or _FakeLLM(),
        market_data=bundle.market_data,
        fundamentals=bundle.fundamentals,
        news=bundle.news,
    )
    if specialists is not None:
        application.state.workflow_specialists = specialists
    return application


def _import_portfolio(client: TestClient) -> str:
    preview = _upload(client, "holdings.csv", csv_bytes(VALID_HEADERS, VALID_ROWS)).json()
    confirmed = client.post(f"/portfolios/uploads/{preview['upload_id']}/confirm")
    assert confirmed.status_code == 200
    return confirmed.json()["id"]


def _collect_keys(payload: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(payload, dict):
        keys.update(payload.keys())
        for value in payload.values():
            keys.update(_collect_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            keys.update(_collect_keys(item))
    return keys


def test_submit_analysis_returns_structured_result_without_internal_state() -> None:
    specialists = _specialists()
    llm = _FakeLLM()
    application = _analysis_app(specialists=specialists, llm=llm)
    with TestClient(application) as client:
        portfolio_id = _import_portfolio(client)
        listed = client.get(f"/portfolios/{portfolio_id}/analysis")
        assert listed.status_code == 200
        assert listed.json() == []

        response = client.post(
            f"/portfolios/{portfolio_id}/analysis",
            json={
                "question": "How concentrated is my portfolio risk?",
                "analysis_type": "portfolio_risk",
                "risk_tolerance": "moderate",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["portfolio_id"] == portfolio_id
        assert body["question"] == "How concentrated is my portfolio risk?"
        assert body["analysis_type"] == "portfolio_risk"
        assert body["status"] == "completed"
        assert body["recommendation"]["summary"] == SYNTHESIS["summary"]
        assert body["recommendation"]["trade_execution"] == "not_implemented"
        assert body["recommendation"]["confidence"] is not None
        assert body["execution"]["status"] == "completed"
        assert "current_node" not in body["execution"]
        assert "llm_model" not in body["execution"]
        specialists_names = [item["agent"] for item in body["specialist_results"]]
        assert "market-analysis" in specialists_names
        assert "risk-assessment" in specialists_names
        assert "fundamental-analysis" not in specialists_names
        assert all("extras" not in item for item in body["specialist_results"])
        assert body["evidence"]
        assert body["evidence"][0]["source"]["provider"]
        assert body["evidence"][0]["source"]["source"]
        assert body["evidence"][0]["source"]["timestamp"]
        assert "critiques" in body
        assert isinstance(body["critiques"], list)
        assert not specialists["portfolio-optimization"].calls
        hidden = HIDDEN_KEYS & _collect_keys(body)
        assert hidden == set()

        analysis_id = body["id"]
        replay = client.get(f"/portfolios/{portfolio_id}/analysis/{analysis_id}")
        assert replay.status_code == 200
        assert replay.json()["id"] == analysis_id
        assert replay.json()["recommendation"]["summary"] == SYNTHESIS["summary"]

        summaries = client.get(f"/portfolios/{portfolio_id}/analysis")
        assert summaries.status_code == 200
        assert summaries.json()[0]["id"] == analysis_id
        assert "recommendation" not in summaries.json()[0]


def test_analysis_requires_imported_portfolio_and_question() -> None:
    specialists = _specialists()
    application = _analysis_app(specialists=specialists, llm=_FakeLLM())
    with TestClient(application) as client:
        missing = client.post(
            "/portfolios/missing/analysis",
            json={"question": "How risky is this book?"},
        )
        assert missing.status_code == 404

        preview = _upload(client, "holdings.csv", csv_bytes(VALID_HEADERS, VALID_ROWS)).json()
        draft = client.post(
            f"/portfolios/{preview['upload_id']}/analysis",
            json={"question": "How risky is this book?"},
        )
        assert draft.status_code == 404

        portfolio_id = _import_portfolio(client)
        empty = client.post(f"/portfolios/{portfolio_id}/analysis", json={})
        assert empty.status_code == 422
        blank = client.post(
            f"/portfolios/{portfolio_id}/analysis",
            json={"question": "   "},
        )
        assert blank.status_code == 422
        invalid_type = client.post(
            f"/portfolios/{portfolio_id}/analysis",
            json={"question": "Review my book", "analysis_type": "watchlist"},
        )
        assert invalid_type.status_code == 422


def test_analysis_result_includes_risk_evidence_and_does_not_run_stock_routes() -> None:
    specialists = _specialists()
    application = _analysis_app(specialists=specialists, llm=_FakeLLM())
    with TestClient(application) as client:
        portfolio_id = _import_portfolio(client)
        response = client.post(
            f"/portfolios/{portfolio_id}/analysis",
            json={
                "question": "Should I rebalance my portfolio?",
                "analysis_type": "portfolio_rebalancing",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["risk_analysis"] is not None
        assert body["risk_analysis"]["concentration"] == "moderate"
        assert body["optimization"] is not None
        assert body["optimization"]["trade_execution"] == "not_implemented"
        assert body["optimization"]["proposed_allocation"]
        assert specialists["portfolio-optimization"].calls
        assert client.get("/stocks").status_code == 404
        watchlist = client.get("/watchlist")
        assert watchlist.status_code == 200
        assert watchlist.json() == []


def test_existing_upload_flow_still_works_alongside_analysis() -> None:
    application = _analysis_app(specialists=_specialists(), llm=_FakeLLM())
    with TestClient(application) as client:
        portfolio_id = _import_portfolio(client)
        available = client.get(f"/portfolios/{portfolio_id}")
        assert available.status_code == 200
        assert available.json()["holding_count"] == 2
        listed = client.get("/portfolios")
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == portfolio_id
        client.post(
            f"/portfolios/{portfolio_id}/analysis",
            json={"question": "Review my portfolio", "analysis_type": "portfolio_review"},
        )
        assert client.get(f"/portfolios/{portfolio_id}").json()["id"] == portfolio_id
        assert client.get("/health").json()["status"] == "ok"


def test_public_mapper_omits_graph_internals() -> None:
    state = create_investment_state(
        "an-1",
        user_request=UserRequest(text="Review the book", analysis_type="portfolio_review"),
        portfolio=_portfolio("AAPL", "MSFT"),
    )
    state["final_recommendation"] = FinalRecommendation(
        summary="Hold.",
        recommendation="Do not place trades.",
        findings=["Concentration is moderate."],
        confidence=0.6,
    )
    state["agent_results"] = {
        "risk-assessment": AgentResultSnapshot(
            agent="risk-assessment",
            role="risk-analyst",
            status="succeeded",
            summary="Moderate concentration",
            findings=["Largest weight is acceptable."],
            confidence=0.7,
            error_code="internal-code",
            error_message=None,
        )
    }
    state["execution"] = ExecutionMetadata(
        status="completed",
        current_node="synthesize",
        requested_agents=["risk-assessment"],
        invoked_agents=["risk-assessment"],
        duration_ms=12.5,
        llm_provider="fake-llm",
        llm_model="hidden-model",
        reflection_cycle=1,
        errors=[],
    )
    state["critiques"] = [
        CritiqueRecord(
            author="portfolio-manager",
            message="Market and fundamental views should be read together.",
            category="agent_disagreement",
            severity="warning",
        )
    ]
    result = public_analysis_result(state, portfolio_id="pf-workflow")
    dumped = result.model_dump(mode="json")
    assert dumped["id"] == "an-1"
    assert dumped["portfolio_id"] == "pf-workflow"
    assert dumped["specialist_results"][0]["agent"] == "risk-assessment"
    assert "error_code" not in dumped["specialist_results"][0]
    assert "extras" not in dumped["specialist_results"][0]
    assert "current_node" not in dumped["execution"]
    assert "llm_provider" not in dumped["execution"]
    assert "llm_model" not in dumped["execution"]
    assert "reflection_cycle" not in dumped["execution"]
    assert dumped["recommendation"]["trade_execution"] == "not_implemented"
    assert dumped["critiques"][0]["message"] == "Market and fundamental views should be read together."
    assert dumped["critiques"][0]["category"] == "agent_disagreement"
    assert "reasoning" not in dumped["critiques"][0]
    assert HIDDEN_KEYS & _collect_keys(dumped) == set()
    PortfolioAnalysisResult.model_validate(dumped)


def test_unknown_analysis_is_not_found() -> None:
    application = _analysis_app(specialists=_specialists(), llm=_FakeLLM())
    with TestClient(application) as client:
        portfolio_id = _import_portfolio(client)
        missing = client.get(f"/portfolios/{portfolio_id}/analysis/does-not-exist")
        assert missing.status_code == 404
        other = client.get("/portfolios/other/analysis/does-not-exist")
        assert other.status_code == 404
