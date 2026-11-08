"""Watchlist monitoring and Stock Analyzer navigation routes.

These routes do not run AI analysis. Detailed analysis stays on /stocks.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_providers_dep, get_watchlist_store
from app.models.watchlist import (
    WatchlistAddRequest,
    WatchlistItem,
    WatchlistOpenResponse,
    WatchlistRemoval,
)
from app.providers.registry import ProviderBundle
from app.repositories.watchlist import WatchlistStore
from app.services.watchlist import (
    add_watchlist_stock,
    get_watchlist_stock,
    list_watchlist,
    open_watchlist_stock,
    remove_watchlist_stock,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItem])
def list_items(
    store: WatchlistStore = Depends(get_watchlist_store),
    providers: ProviderBundle = Depends(get_providers_dep),
) -> list[WatchlistItem]:
    """List monitored symbols with current information when available."""
    return list_watchlist(store, providers)


@router.post("", response_model=WatchlistItem)
def add_item(
    payload: WatchlistAddRequest,
    store: WatchlistStore = Depends(get_watchlist_store),
    providers: ProviderBundle = Depends(get_providers_dep),
) -> WatchlistItem:
    """Add a symbol to the Watchlist. Duplicates are rejected."""
    return add_watchlist_stock(store, providers, payload.symbol)


@router.post("/{symbol}/open", response_model=WatchlistOpenResponse)
def open_item(
    symbol: str,
    store: WatchlistStore = Depends(get_watchlist_store),
    providers: ProviderBundle = Depends(get_providers_dep),
) -> WatchlistOpenResponse:
    """Open a monitored symbol through Stock Analyzer. No AI analysis is run."""
    return open_watchlist_stock(store, providers, symbol)


@router.get("/{symbol}", response_model=WatchlistItem)
def get_item(
    symbol: str,
    store: WatchlistStore = Depends(get_watchlist_store),
    providers: ProviderBundle = Depends(get_providers_dep),
) -> WatchlistItem:
    """Return current information for one monitored symbol."""
    return get_watchlist_stock(store, providers, symbol)


@router.delete("/{symbol}", response_model=WatchlistRemoval)
def delete_item(
    symbol: str,
    store: WatchlistStore = Depends(get_watchlist_store),
) -> WatchlistRemoval:
    """Remove a symbol from the Watchlist."""
    return remove_watchlist_stock(store, symbol)
