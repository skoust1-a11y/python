"""Application factory and ASGI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.config.logging import configure_logging
from app.config.settings import Settings, get_settings
from app.providers.registry import build_providers
from app.repositories.portfolio import InMemoryPortfolioStore
from app.repositories.stock import InMemoryStockAnalysisStore
from app.repositories.watchlist import InMemoryWatchlistStore

logger = logging.getLogger("app")

# Vite dev server and preview. The UI may call the API directly or via proxy.
FRONTEND_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application with logging, providers, and error handlers."""
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logger.info("Starting %s v%s (%s)", settings.app_name, __version__, settings.app_env)
        logger.info("Selected providers: %s", settings.selected_providers())
        yield
        logger.info("Shutting down %s", settings.app_name)

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Stateful multi-agent financial decision-support prototype.",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.providers = build_providers(settings)
    application.state.portfolio_store = InMemoryPortfolioStore()
    application.state.stock_analysis_store = InMemoryStockAnalysisStore()
    application.state.watchlist_store = InMemoryWatchlistStore()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(FRONTEND_CORS_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
