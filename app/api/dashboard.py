"""Dashboard overview route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_portfolio_store, get_providers_dep
from app.models.dashboard import DashboardOverview
from app.providers.registry import ProviderBundle
from app.repositories.portfolio import PortfolioStore
from app.services.dashboard import get_dashboard_overview

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOverview)
def get_dashboard(
    store: PortfolioStore = Depends(get_portfolio_store),
    providers: ProviderBundle = Depends(get_providers_dep),
) -> DashboardOverview:
    """Return a lightweight market and optional portfolio overview."""
    return get_dashboard_overview(store, providers)
