"""Portfolio upload, preview, confirmation, retrieval, and analysis routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, File, UploadFile
from pydantic import BaseModel, Field

from app.agents.base import AgentContext
from app.api.deps import get_agent_context, get_portfolio_store, get_settings_dep
from app.config.settings import Settings
from app.models.analysis import (
    PortfolioAnalysisRequest,
    PortfolioAnalysisResult,
    PortfolioAnalysisSummary,
)
from app.models.portfolio import (
    Portfolio,
    PortfolioHoldings,
    PortfolioPreview,
    PortfolioSummary,
)
from app.repositories.portfolio import PortfolioStore
from app.services.analysis import (
    analyze_portfolio,
    get_portfolio_analysis,
    list_portfolio_analyses,
)
from app.services.portfolio import (
    confirm_portfolio_upload,
    get_imported_holdings,
    get_imported_portfolio,
    get_imported_portfolio_summary,
    get_portfolio_preview,
    list_imported_portfolios,
    stage_portfolio_upload,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


class ConfirmPortfolioRequest(BaseModel):
    """Optional label applied at import time."""

    name: str | None = Field(default=None)


@router.post("/uploads", response_model=PortfolioPreview)
async def upload_portfolio(
    file: UploadFile = File(...),
    store: PortfolioStore = Depends(get_portfolio_store),
    settings: Settings = Depends(get_settings_dep),
) -> PortfolioPreview:
    """Upload a CSV or XLSX file, validate it, and return a preview."""
    content = await file.read()
    return stage_portfolio_upload(
        store,
        settings,
        filename=file.filename,
        content=content,
    )


@router.get("/uploads/{upload_id}", response_model=PortfolioPreview)
def get_upload(
    upload_id: str,
    store: PortfolioStore = Depends(get_portfolio_store),
) -> PortfolioPreview:
    """Return a previously staged portfolio preview."""
    return get_portfolio_preview(store, upload_id)


@router.post("/uploads/{upload_id}/confirm", response_model=Portfolio)
def confirm_upload(
    upload_id: str,
    payload: ConfirmPortfolioRequest | None = Body(default=None),
    store: PortfolioStore = Depends(get_portfolio_store),
) -> Portfolio:
    """Persist a staged preview. Required before the portfolio is available."""
    name = payload.name if payload is not None else None
    return confirm_portfolio_upload(store, upload_id, name=name)


@router.get("", response_model=list[PortfolioSummary])
def list_portfolios(
    store: PortfolioStore = Depends(get_portfolio_store),
) -> list[PortfolioSummary]:
    """List confirmed portfolios. Drafts are not included."""
    return list_imported_portfolios(store)


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
def get_portfolio_summary(
    portfolio_id: str,
    store: PortfolioStore = Depends(get_portfolio_store),
) -> PortfolioSummary:
    """Return a confirmed portfolio without holdings."""
    return get_imported_portfolio_summary(store, portfolio_id)


@router.get("/{portfolio_id}/holdings", response_model=PortfolioHoldings)
def get_portfolio_holdings(
    portfolio_id: str,
    store: PortfolioStore = Depends(get_portfolio_store),
) -> PortfolioHoldings:
    """Return confirmed holdings for an imported portfolio."""
    return get_imported_holdings(store, portfolio_id)


@router.post("/{portfolio_id}/analysis", response_model=PortfolioAnalysisResult)
def submit_portfolio_analysis(
    portfolio_id: str,
    payload: PortfolioAnalysisRequest,
    store: PortfolioStore = Depends(get_portfolio_store),
    context: AgentContext = Depends(get_agent_context),
) -> PortfolioAnalysisResult:
    """Run one portfolio analysis and return the structured result."""
    return analyze_portfolio(store, context, portfolio_id, payload)


@router.get("/{portfolio_id}/analysis", response_model=list[PortfolioAnalysisSummary])
def list_analyses(
    portfolio_id: str,
    store: PortfolioStore = Depends(get_portfolio_store),
) -> list[PortfolioAnalysisSummary]:
    """List stored analysis runs for an imported portfolio."""
    return list_portfolio_analyses(store, portfolio_id)


@router.get("/{portfolio_id}/analysis/{analysis_id}", response_model=PortfolioAnalysisResult)
def get_analysis(
    portfolio_id: str,
    analysis_id: str,
    store: PortfolioStore = Depends(get_portfolio_store),
) -> PortfolioAnalysisResult:
    """Return a previously stored structured analysis result."""
    return get_portfolio_analysis(store, portfolio_id, analysis_id)


@router.get("/{portfolio_id}", response_model=Portfolio)
def get_portfolio(
    portfolio_id: str,
    store: PortfolioStore = Depends(get_portfolio_store),
) -> Portfolio:
    """Return a confirmed portfolio."""
    return get_imported_portfolio(store, portfolio_id)
