"""HTTP routes."""

from fastapi import APIRouter

from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.portfolios import router as portfolios_router
from app.api.stocks import router as stocks_router
from app.api.watchlist import router as watchlist_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(portfolios_router)
api_router.include_router(stocks_router)
api_router.include_router(watchlist_router)
