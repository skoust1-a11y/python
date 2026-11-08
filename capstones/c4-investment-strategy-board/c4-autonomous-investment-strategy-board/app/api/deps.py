"""FastAPI dependency providers. Routes should depend on contracts, not vendors."""

from typing import Any

from fastapi import Request

from app.agents.base import Agent, AgentContext
from app.config.settings import Settings
from app.providers.registry import ProviderBundle
from app.repositories.portfolio import PortfolioStore
from app.repositories.stock import StockAnalysisStore
from app.repositories.watchlist import WatchlistStore


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_providers_dep(request: Request) -> ProviderBundle:
    return request.app.state.providers


def get_portfolio_store(request: Request) -> PortfolioStore:
    return request.app.state.portfolio_store


def get_stock_analysis_store(request: Request) -> StockAnalysisStore:
    return request.app.state.stock_analysis_store


def get_watchlist_store(request: Request) -> WatchlistStore:
    return request.app.state.watchlist_store


def get_agent_context(request: Request) -> AgentContext:
    extras: dict[str, Any] = dict(getattr(request.app.state, "workflow_extras", None) or {})
    specialists: dict[str, Agent] | None = getattr(
        request.app.state, "workflow_specialists", None
    )
    if specialists is not None:
        extras["specialists"] = specialists
    return AgentContext(
        providers=request.app.state.providers,
        extras=extras or None,
    )
