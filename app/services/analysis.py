"""Run portfolio analysis through the compiled workflow and map a public result.

The HTTP contract never includes graph node names, specialist extras, prompts,
or chain-of-thought. Evidence and source metadata are preserved.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from uuid import uuid4

from app.agents.base import Agent, AgentContext
from app.agents.manager import INVOCATION_ORDER
from app.exceptions import AppError, NotFoundError
from app.models.analysis import (
    AnalysisExecution,
    PortfolioAnalysisRequest,
    PortfolioAnalysisResult,
    PortfolioAnalysisSummary,
    SpecialistResult,
    StockAnalysisRequest,
    StockAnalysisResult,
    StockAnalysisSummary,
)
from app.models.types import normalize_symbol
from app.repositories.portfolio import PortfolioStore
from app.repositories.stock import StockAnalysisStore
from app.services.portfolio import get_imported_portfolio
from app.workflow.graph import invoke_strategy_board
from app.workflow.state import (
    AgentResultSnapshot,
    ExecutionMetadata,
    InvestmentProfile,
    InvestmentState,
    SelectedStock,
    UserRequest,
    create_investment_state,
)

UTC = timezone.utc
logger = logging.getLogger("app.services")
MANAGER_AGENT = "portfolio-manager"


def analyze_portfolio(
    store: PortfolioStore,
    context: AgentContext,
    portfolio_id: str,
    request: PortfolioAnalysisRequest,
) -> PortfolioAnalysisResult:
    """Load an imported portfolio, run one workflow pass, and persist the result."""
    portfolio = get_imported_portfolio(store, portfolio_id)
    analysis_id = uuid4().hex
    profile = _investment_profile(request)
    user_request = UserRequest(
        text=request.question,
        analysis_type=request.analysis_type,
        portfolio_id=portfolio.id,
    )
    state = create_investment_state(
        analysis_id,
        user_request=user_request,
        investment_profile=profile,
        portfolio=portfolio,
    )
    specialists = _specialists_from(context)
    logger.info(
        "portfolio.analysis.start portfolio_id=%s analysis_id=%s",
        portfolio.id,
        analysis_id,
    )
    final_state = invoke_strategy_board(state, context, specialists=specialists)
    result = public_analysis_result(final_state, portfolio_id=portfolio.id)
    store.save_analysis(result)
    logger.info(
        "portfolio.analysis.complete portfolio_id=%s analysis_id=%s status=%s",
        portfolio.id,
        result.id,
        result.status,
    )
    return result


def get_portfolio_analysis(
    store: PortfolioStore, portfolio_id: str, analysis_id: str
) -> PortfolioAnalysisResult:
    get_imported_portfolio(store, portfolio_id)
    result = store.get_analysis(analysis_id)
    if result is None or result.portfolio_id != portfolio_id:
        raise NotFoundError("Portfolio analysis not found.")
    return result


def list_portfolio_analyses(
    store: PortfolioStore, portfolio_id: str
) -> list[PortfolioAnalysisSummary]:
    get_imported_portfolio(store, portfolio_id)
    return [
        PortfolioAnalysisSummary(
            id=item.id,
            portfolio_id=item.portfolio_id,
            question=item.question,
            analysis_type=item.analysis_type,
            status=item.status,
            created_at=item.created_at,
        )
        for item in store.list_analyses(portfolio_id)
    ]


def analyze_stock(
    store: StockAnalysisStore,
    context: AgentContext,
    symbol: str,
    request: StockAnalysisRequest,
) -> StockAnalysisResult:
    """Run one stock-analysis workflow pass without an uploaded portfolio."""
    token = _require_stock_symbol(symbol)
    analysis_type = _stock_analysis_type(request)
    analysis_id = uuid4().hex
    profile = _investment_profile(request)
    user_request = UserRequest(
        text=request.question,
        symbols=[token],
        analysis_type=analysis_type,
    )
    state = create_investment_state(
        analysis_id,
        user_request=user_request,
        investment_profile=profile,
        selected_stock=SelectedStock(symbol=token),
    )
    specialists = _specialists_from(context)
    logger.info("stock.analysis.start symbol=%s analysis_id=%s", token, analysis_id)
    final_state = invoke_strategy_board(state, context, specialists=specialists)
    result = public_stock_analysis_result(final_state, symbol=token)
    store.save_analysis(result)
    logger.info(
        "stock.analysis.complete symbol=%s analysis_id=%s status=%s",
        token,
        result.id,
        result.status,
    )
    return result


def get_stock_analysis(
    store: StockAnalysisStore, symbol: str, analysis_id: str
) -> StockAnalysisResult:
    token = _require_stock_symbol(symbol)
    result = store.get_analysis(analysis_id)
    if result is None or result.symbol != token:
        raise NotFoundError("Stock analysis not found.")
    return result


def list_stock_analyses(store: StockAnalysisStore, symbol: str) -> list[StockAnalysisSummary]:
    token = _require_stock_symbol(symbol)
    return [
        StockAnalysisSummary(
            id=item.id,
            symbol=item.symbol,
            question=item.question,
            analysis_type=item.analysis_type,
            status=item.status,
            created_at=item.created_at,
        )
        for item in store.list_analyses(token)
    ]


def public_stock_analysis_result(state: InvestmentState, *, symbol: str) -> StockAnalysisResult:
    """Project graph state onto the public single-stock analysis contract."""
    execution = state.get("execution")
    request = state.get("user_request")
    created_at = _created_at(execution)
    status = execution.status if execution is not None and execution.status else "completed"
    question = request.text if request is not None else "Stock analysis"
    analysis_type = request.analysis_type if request is not None else "stock_analysis"
    selected = state.get("selected_stock")
    resolved = selected.symbol if selected is not None else symbol
    return StockAnalysisResult(
        id=str(state.get("request_id") or uuid4().hex),
        symbol=resolved,
        question=question,
        analysis_type=analysis_type,
        status=status,
        recommendation=state.get("final_recommendation"),
        specialist_results=_specialist_results(state.get("agent_results") or {}),
        risk_analysis=state.get("risk_analysis"),
        optimization=state.get("optimization_results"),
        market_data=_sorted_snapshots(state.get("market_data") or {}),
        fundamental_data=_sorted_snapshots(state.get("fundamental_data") or {}),
        news=list(state.get("news") or []),
        evidence=list(state.get("evidence") or []),
        conflicts=list(state.get("conflicts") or []),
        critiques=list(state.get("critiques") or []),
        execution=_public_execution(execution),
        created_at=created_at,
    )


def public_analysis_result(
    state: InvestmentState,
    *,
    portfolio_id: str,
) -> PortfolioAnalysisResult:
    """Project graph state onto the public analysis contract."""
    execution = state.get("execution")
    request = state.get("user_request")
    created_at = _created_at(execution)
    status = execution.status if execution is not None and execution.status else "completed"
    question = request.text if request is not None else "Portfolio analysis"
    analysis_type = request.analysis_type if request is not None else None
    return PortfolioAnalysisResult(
        id=str(state.get("request_id") or uuid4().hex),
        portfolio_id=portfolio_id,
        question=question,
        analysis_type=analysis_type,
        status=status,
        recommendation=state.get("final_recommendation"),
        specialist_results=_specialist_results(state.get("agent_results") or {}),
        risk_analysis=state.get("risk_analysis"),
        optimization=state.get("optimization_results"),
        market_data=_sorted_snapshots(state.get("market_data") or {}),
        fundamental_data=_sorted_snapshots(state.get("fundamental_data") or {}),
        news=list(state.get("news") or []),
        evidence=list(state.get("evidence") or []),
        conflicts=list(state.get("conflicts") or []),
        critiques=list(state.get("critiques") or []),
        execution=_public_execution(execution),
        created_at=created_at,
    )


def _investment_profile(
    request: PortfolioAnalysisRequest | StockAnalysisRequest,
) -> InvestmentProfile | None:
    if request.risk_tolerance is None and request.horizon is None and not request.objective:
        return None
    return InvestmentProfile(
        risk_tolerance=request.risk_tolerance,
        horizon=request.horizon,
        objective=request.objective,
    )


def _specialists_from(context: AgentContext) -> dict[str, Agent] | None:
    extras = context.extras or {}
    raw = extras.get("specialists")
    if not isinstance(raw, Mapping) or not raw:
        return None
    return dict(raw)


def _specialist_results(
    results: Mapping[str, AgentResultSnapshot],
) -> list[SpecialistResult]:
    ordered: list[AgentResultSnapshot] = []
    seen: set[str] = set()
    for name in (*INVOCATION_ORDER, MANAGER_AGENT):
        snapshot = results.get(name)
        if snapshot is None:
            continue
        ordered.append(snapshot)
        seen.add(name)
    for name in sorted(results):
        if name in seen:
            continue
        ordered.append(results[name])
    return [_to_specialist(item) for item in ordered]


def _to_specialist(snapshot: AgentResultSnapshot) -> SpecialistResult:
    return SpecialistResult(
        agent=snapshot.agent,
        role=snapshot.role,
        status=snapshot.status,
        summary=snapshot.summary,
        findings=list(snapshot.findings),
        confidence=snapshot.confidence,
        error_message=snapshot.error_message,
    )


def _sorted_snapshots(mapping: Mapping[str, object]) -> list[object]:
    return [mapping[key] for key in sorted(mapping)]


def _public_execution(execution: ExecutionMetadata | None) -> AnalysisExecution:
    if execution is None:
        return AnalysisExecution(status="completed")
    status = execution.status or "completed"
    return AnalysisExecution(
        status=status,
        requested_agents=list(execution.requested_agents),
        invoked_agents=list(execution.invoked_agents),
        started_at=execution.started_at,
        completed_at=execution.updated_at,
        duration_ms=execution.duration_ms,
        errors=list(execution.errors),
    )


def _created_at(execution: ExecutionMetadata | None) -> datetime:
    if execution is not None and execution.started_at is not None:
        return execution.started_at
    return datetime.now(tz=UTC)


def _require_stock_symbol(symbol: str) -> str:
    try:
        return normalize_symbol(symbol)
    except ValueError as exc:
        raise AppError("Invalid stock symbol.", status_code=422, error_code="validation_error") from exc


def _stock_analysis_type(request: StockAnalysisRequest) -> str:
    analysis_type = request.analysis_type or "stock_analysis"
    if analysis_type != "stock_analysis":
        raise AppError(
            "Stock Analyzer only supports analysis_type=stock_analysis.",
            status_code=422,
            error_code="validation_error",
        )
    return analysis_type
