"""LangGraph investment state schema and incremental reducers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import get_type_hints

import pytest
from pydantic import ValidationError

from app.models.common import DataSourceMetadata, Evidence
from app.models.portfolio import Holding, Portfolio, SymbolValidation
from app.workflow.graph import build_strategy_graph
from app.workflow.state import (
    INVESTMENT_STATE_REDUCERS,
    AgentResultSnapshot,
    ConflictRecord,
    CritiqueRecord,
    ExecutionMetadata,
    FinalRecommendation,
    FundamentalDataSnapshot,
    InvestmentProfile,
    InvestmentState,
    MarketDataSnapshot,
    NewsSnapshot,
    OptimizationResultSnapshot,
    RiskAnalysisSnapshot,
    SelectedStock,
    UserRequest,
    annotated_reducer,
    create_investment_state,
    merge_investment_state,
)

UTC = timezone.utc


def _now() -> datetime:
    return datetime(2024, 6, 15, 14, 30, tzinfo=UTC)


def _source() -> DataSourceMetadata:
    return DataSourceMetadata(
        provider="stub",
        source="unit-test",
        timestamp=_now(),
    )


def _holding(symbol: str, quantity: float = 10.0) -> Holding:
    return Holding(
        symbol=symbol,
        quantity=quantity,
        symbol_validation=SymbolValidation(
            input=symbol, normalized=symbol.upper(), status="valid"
        ),
    )


def _portfolio() -> Portfolio:
    return Portfolio(
        id="pf-state",
        holdings=[_holding("AAPL"), _holding("MSFT")],
        base_currency="USD",
        source_filename="holdings.csv",
        source_format="csv",
        imported_at=_now(),
    )


def _evidence(*, field: str = "price", value: float = 190.25) -> Evidence:
    return Evidence(
        source=_source(),
        symbol="AAPL",
        field=field,
        value=value,
    )


def test_create_investment_state_starts_with_empty_accumulators() -> None:
    state = create_investment_state(" req-1 ")
    assert state["request_id"] == "req-1"
    assert state["market_data"] == {}
    assert state["fundamental_data"] == {}
    assert state["news"] == []
    assert state["agent_results"] == {}
    assert state["conflicts"] == []
    assert state["critiques"] == []
    assert state["evidence"] == []
    assert state["execution"].status == "pending"
    assert "user_request" not in state
    assert "final_recommendation" not in state


def test_create_investment_state_requires_request_id() -> None:
    with pytest.raises(ValueError, match="request_id"):
        create_investment_state("  ")


def test_user_request_and_profile_validate() -> None:
    request = UserRequest(
        text="Analyze AAPL",
        symbols=["aapl"],
        analysis_type="stock_analysis",
    )
    assert request.symbols == ["AAPL"]
    profile = InvestmentProfile(
        risk_tolerance="moderate",
        horizon="long",
        base_currency="usd",
        constraints=["No tobacco"],
    )
    assert profile.base_currency == "USD"
    with pytest.raises(ValidationError):
        UserRequest(text=" ")
    with pytest.raises(ValidationError):
        InvestmentProfile(risk_tolerance="yolo")


def test_snapshots_reject_raw_series_and_statement_fields() -> None:
    with pytest.raises(ValidationError):
        MarketDataSnapshot(symbol="AAPL", prices=[{"close": 1.0}])
    with pytest.raises(ValidationError):
        FundamentalDataSnapshot(symbol="AAPL", line_items={"revenue": 1.0})
    with pytest.raises(ValidationError):
        NewsSnapshot(
            headline="Earnings beat",
            timestamp=_now(),
            source=_source(),
            extra={"body": "full article"},
        )
    with pytest.raises(ValidationError):
        RiskAnalysisSnapshot(pairwise_correlations=[{"left": "AAPL", "right": "MSFT"}])
    with pytest.raises(ValidationError):
        AgentResultSnapshot(
            agent="market-analysis",
            role="market-analyst",
            status="succeeded",
            summary="ok",
            evidence=[_evidence()],
        )


def test_incremental_node_updates_do_not_wipe_unrelated_fields() -> None:
    state = create_investment_state(
        "req-merge",
        user_request=UserRequest(text="Review the portfolio", symbols=["AAPL"]),
        portfolio=_portfolio(),
        selected_stock=SelectedStock(symbol="aapl", name="Apple"),
    )
    after_market = merge_investment_state(
        state,
        {
            "market_data": {
                "AAPL": MarketDataSnapshot(
                    symbol="AAPL",
                    current_price=190.25,
                    trend="uptrend",
                    source=_source(),
                )
            },
            "execution": ExecutionMetadata(
                status="running",
                current_node="market-analysis",
                invoked_agents=["market-analysis"],
            ),
        },
    )
    after_fundamental = merge_investment_state(
        after_market,
        {
            "fundamental_data": {
                "AAPL": FundamentalDataSnapshot(
                    symbol="AAPL",
                    financial_health="healthy",
                    as_of_kind="latest_reported",
                    source=_source(),
                )
            },
            "execution": ExecutionMetadata(
                current_node="fundamental-analysis",
                invoked_agents=["fundamental-analysis"],
            ),
        },
    )

    assert after_fundamental["request_id"] == "req-merge"
    assert after_fundamental["user_request"].text == "Review the portfolio"
    assert after_fundamental["portfolio"].id == "pf-state"
    assert after_fundamental["selected_stock"].symbol == "AAPL"
    assert after_fundamental["market_data"]["AAPL"].current_price == 190.25
    assert after_fundamental["fundamental_data"]["AAPL"].financial_health == "healthy"
    assert after_fundamental["execution"].status == "running"
    assert after_fundamental["execution"].invoked_agents == [
        "market-analysis",
        "fundamental-analysis",
    ]
    assert after_fundamental["execution"].requested_agents == []
    assert after_fundamental["execution"].current_node == "fundamental-analysis"


def test_symbol_snapshots_merge_by_ticker_and_overwrite_the_same_name() -> None:
    state = create_investment_state("req-symbols")
    state = merge_investment_state(
        state,
        {
            "market_data": {
                "AAPL": MarketDataSnapshot(symbol="AAPL", current_price=190.0)
            }
        },
    )
    state = merge_investment_state(
        state,
        {
            "market_data": {
                "MSFT": MarketDataSnapshot(symbol="MSFT", current_price=420.0),
                "AAPL": MarketDataSnapshot(symbol="AAPL", current_price=191.5),
            }
        },
    )
    assert set(state["market_data"]) == {"AAPL", "MSFT"}
    assert state["market_data"]["AAPL"].current_price == 191.5
    assert state["market_data"]["MSFT"].current_price == 420.0


def test_agent_results_and_evidence_accumulate_with_deduplication() -> None:
    state = create_investment_state("req-agents")
    first = merge_investment_state(
        state,
        {
            "agent_results": {
                "market-analysis": AgentResultSnapshot(
                    agent="market-analysis",
                    role="market-analyst",
                    status="succeeded",
                    summary="Uptrend",
                    findings=["Price rose"],
                    confidence=0.7,
                )
            },
            "evidence": [_evidence()],
        },
    )
    second = merge_investment_state(
        first,
        {
            "agent_results": {
                "risk-assessment": AgentResultSnapshot(
                    agent="risk-assessment",
                    role="risk-analyst",
                    status="succeeded",
                    summary="Concentrated",
                )
            },
            "evidence": [_evidence(), _evidence(field="weight", value=0.4)],
        },
    )
    assert set(second["agent_results"]) == {"market-analysis", "risk-assessment"}
    assert [item.field for item in second["evidence"]] == ["price", "weight"]


def test_conflicts_news_and_critiques_append_incrementally() -> None:
    state = create_investment_state("req-notes")
    state = merge_investment_state(
        state,
        {
            "news": [
                NewsSnapshot(
                    headline="Chip demand rises",
                    timestamp=_now(),
                    source=_source(),
                    symbol="AAPL",
                )
            ],
            "conflicts": [
                ConflictRecord(
                    description="Uptrend versus stressed balance sheet.",
                    agents=["market-analysis", "fundamental-analysis"],
                )
            ],
            "critiques": [
                CritiqueRecord(
                    author="portfolio-manager",
                    target="risk-assessment",
                    message="Concentration is under-specified.",
                )
            ],
        },
    )
    state = merge_investment_state(
        state,
        {
            "news": [
                NewsSnapshot(
                    headline="Chip demand rises",
                    timestamp=_now(),
                    source=_source(),
                    symbol="AAPL",
                ),
                NewsSnapshot(
                    headline="Index futures mixed",
                    timestamp=_now(),
                    source=_source(),
                ),
            ],
            "conflicts": [
                ConflictRecord(
                    description="Uptrend versus stressed balance sheet.",
                    agents=["market-analysis", "fundamental-analysis"],
                )
            ],
            "critiques": [
                CritiqueRecord(
                    author="portfolio-manager",
                    target="risk-assessment",
                    message="Concentration is under-specified.",
                    resolved=True,
                )
            ],
        },
    )
    assert len(state["news"]) == 2
    assert len(state["conflicts"]) == 1
    assert len(state["critiques"]) == 1
    assert state["critiques"][0].resolved is True


def test_risk_optimization_and_recommendation_are_replaced_not_concatenated() -> None:
    state = create_investment_state("req-final", portfolio=_portfolio())
    state = merge_investment_state(
        state,
        {
            "risk_analysis": RiskAnalysisSnapshot(
                overall_risk_assessment="Elevated concentration",
                concentration="high",
                hhi=0.42,
            ),
            "optimization_results": OptimizationResultSnapshot(
                objective="minimum_volatility",
                proposed_allocation={"AAPL": 0.4, "MSFT": 0.6},
                feasible=True,
            ),
        },
    )
    state = merge_investment_state(
        state,
        {
            "risk_analysis": RiskAnalysisSnapshot(
                overall_risk_assessment="Moderate after review",
                concentration="moderate",
                hhi=0.31,
            ),
            "final_recommendation": FinalRecommendation(
                summary="Hold the sleeve",
                recommendation="Keep the uploaded mix; do not trade.",
                confidence=0.55,
            ),
        },
    )
    assert state["risk_analysis"].concentration == "moderate"
    assert state["optimization_results"].trade_execution == "not_implemented"
    assert state["final_recommendation"].trade_execution == "not_implemented"
    assert state["final_recommendation"].recommendation.startswith("Keep")


def test_dict_updates_are_coerced_into_typed_snapshots() -> None:
    state = create_investment_state("req-json")
    updated = merge_investment_state(
        state,
        {
            "selected_stock": {"symbol": "msft", "name": "Microsoft"},
            "portfolio": _portfolio().model_dump(mode="json"),
            "agent_results": {
                "market-analysis": {
                    "agent": "market-analysis",
                    "role": "market-analyst",
                    "status": "failed",
                    "summary": "market-analysis failed",
                    "error_code": "provider_error",
                    "error_message": "quote unavailable",
                }
            },
        },
    )
    assert isinstance(updated["selected_stock"], SelectedStock)
    assert updated["selected_stock"].symbol == "MSFT"
    assert isinstance(updated["portfolio"], Portfolio)
    assert updated["portfolio"].id == "pf-state"
    result = updated["agent_results"]["market-analysis"]
    assert isinstance(result, AgentResultSnapshot)
    assert result.status == "failed"


def test_execution_errors_accumulate_and_started_at_is_preserved() -> None:
    started = _now()
    state = create_investment_state("req-exec")
    state = merge_investment_state(
        state,
        {
            "execution": ExecutionMetadata(
                status="running",
                started_at=started,
                invoked_agents=["market-analysis"],
            )
        },
    )
    state = merge_investment_state(
        state,
        {
            "execution": ExecutionMetadata(
                status="failed",
                errors=["market-analysis: quote unavailable"],
                duration_ms=12.5,
            )
        },
    )
    assert state["execution"].started_at == started
    assert state["execution"].status == "failed"
    assert state["execution"].errors == ["market-analysis: quote unavailable"]
    assert state["execution"].duration_ms == 12.5


def test_execution_reflection_cycle_is_replaced_not_added() -> None:
    state = create_investment_state("req-cycle")
    state = merge_investment_state(
        state,
        {"execution": ExecutionMetadata(status="running", reflection_cycle=0)},
    )
    state = merge_investment_state(
        state,
        {"execution": ExecutionMetadata(reflection_cycle=1)},
    )
    assert state["execution"].reflection_cycle == 1


def test_investment_state_exposes_langgraph_reducers_on_accumulators() -> None:
    hints = get_type_hints(InvestmentState, include_extras=True)
    for field, reducer in INVESTMENT_STATE_REDUCERS.items():
        assert field in hints
        assert annotated_reducer(field) is reducer
    assert annotated_reducer("request_id") is None
    assert annotated_reducer("final_recommendation") is None


def test_investment_state_covers_required_slots() -> None:
    expected = {
        "request_id",
        "user_request",
        "investment_profile",
        "portfolio",
        "selected_stock",
        "market_data",
        "fundamental_data",
        "news",
        "agent_results",
        "risk_analysis",
        "optimization_results",
        "conflicts",
        "critiques",
        "evidence",
        "final_recommendation",
        "execution",
    }
    assert set(InvestmentState.__annotations__) == expected


def test_compiled_graph_exposes_strategy_nodes() -> None:
    from app.agents.base import AgentContext
    from app.providers.registry import build_providers
    from tests.helpers import make_settings

    graph = build_strategy_graph(AgentContext(providers=build_providers(make_settings())))
    node_names = set(graph.nodes)
    assert "plan" in node_names
    assert "market-analysis" in node_names
    assert "synthesize" in node_names
