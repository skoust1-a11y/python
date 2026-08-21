"""Stock Analyzer search, selection, data, and analysis routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.agents.base import AgentContext
from app.api.deps import get_agent_context, get_providers_dep, get_stock_analysis_store
from app.models.analysis import (
    StockAnalysisRequest,
    StockAnalysisResult,
    StockAnalysisSummary,
)
from app.models.stock import (
    StockFundamentalData,
    StockMarketData,
    StockOverview,
    StockSearchResponse,
    StockSelectionRequest,
    SuggestedQuestionList,
)
from app.providers.registry import ProviderBundle
from app.repositories.stock import StockAnalysisStore
from app.services.analysis import analyze_stock, get_stock_analysis, list_stock_analyses
from app.services.stock import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    get_stock_fundamentals,
    get_stock_market_data,
    get_stock_overview,
    search_stocks,
    select_stock,
    suggested_questions,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/search", response_model=StockSearchResponse)
def search(
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT),
    providers: ProviderBundle = Depends(get_providers_dep),
) -> StockSearchResponse:
    """Search instruments through the configured market-data provider."""
    return search_stocks(providers, q, limit=limit)


@router.post("/select", response_model=StockOverview)
def select(
    payload: StockSelectionRequest,
    providers: ProviderBundle = Depends(get_providers_dep),
) -> StockOverview:
    """Select a stock for analysis. Independent of any uploaded portfolio."""
    return select_stock(providers, payload.symbol)


@router.get("/{symbol}/market", response_model=StockMarketData)
def get_market(
    symbol: str,
    interval: str = Query(default="1d"),
    providers: ProviderBundle = Depends(get_providers_dep),
) -> StockMarketData:
    """Return retrieved market data for the selected stock."""
    return get_stock_market_data(providers, symbol, interval=interval)


@router.get("/{symbol}/fundamentals", response_model=StockFundamentalData)
def get_fundamentals(
    symbol: str,
    providers: ProviderBundle = Depends(get_providers_dep),
) -> StockFundamentalData:
    """Return retrieved fundamental data for the selected stock."""
    return get_stock_fundamentals(providers, symbol)


@router.get("/{symbol}/questions", response_model=SuggestedQuestionList)
def get_questions(symbol: str) -> SuggestedQuestionList:
    """Return suggested Stock Analyzer questions for the selected symbol."""
    return suggested_questions(symbol)


@router.post("/{symbol}/analysis", response_model=StockAnalysisResult)
def submit_analysis(
    symbol: str,
    payload: StockAnalysisRequest,
    store: StockAnalysisStore = Depends(get_stock_analysis_store),
    context: AgentContext = Depends(get_agent_context),
) -> StockAnalysisResult:
    """Run one AI stock analysis. Does not use the uploaded portfolio."""
    return analyze_stock(store, context, symbol, payload)


@router.get("/{symbol}/analysis", response_model=list[StockAnalysisSummary])
def list_analyses(
    symbol: str,
    store: StockAnalysisStore = Depends(get_stock_analysis_store),
) -> list[StockAnalysisSummary]:
    """List stored Stock Analyzer runs for one symbol."""
    return list_stock_analyses(store, symbol)


@router.get("/{symbol}/analysis/{analysis_id}", response_model=StockAnalysisResult)
def get_analysis(
    symbol: str,
    analysis_id: str,
    store: StockAnalysisStore = Depends(get_stock_analysis_store),
) -> StockAnalysisResult:
    """Return a previously stored structured stock-analysis result."""
    return get_stock_analysis(store, symbol, analysis_id)


@router.get("/{symbol}", response_model=StockOverview)
def get_stock(
    symbol: str,
    providers: ProviderBundle = Depends(get_providers_dep),
) -> StockOverview:
    """Return current information for a selected stock."""
    return get_stock_overview(providers, symbol)
