"""Watchlist monitoring use cases.

Add, list, current information, and removal stay on this surface. Opening a
symbol reuses Stock Analyzer selection and never runs AI analysis. Quotes come
from injected provider contracts; missing data is recorded, not invented.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.exceptions import AppError, ConflictError, NotFoundError, ProviderError
from app.models.stock import StockOverview
from app.models.types import NonEmptyText, normalize_symbol
from app.models.watchlist import (
    WatchlistItem,
    WatchlistOpenResponse,
    WatchlistRemoval,
)
from app.providers.registry import ProviderBundle
from app.repositories.watchlist import WatchlistEntry, WatchlistStore
from app.services.stock import get_stock_overview, select_stock

UTC = timezone.utc
logger = logging.getLogger("app.services")


def add_watchlist_stock(
    store: WatchlistStore,
    providers: ProviderBundle,
    symbol: str,
) -> WatchlistItem:
    """Resolve a symbol and start monitoring it. Duplicates are rejected."""
    token = _require_symbol(symbol)
    if store.get(token) is not None:
        raise ConflictError(f"Stock {token} is already on the watchlist.")
    overview = get_stock_overview(providers, token)
    entry = WatchlistEntry(
        symbol=overview.symbol,
        name=overview.name,
        exchange=overview.exchange,
        currency=overview.currency,
        added_at=datetime.now(tz=UTC),
    )
    if not store.add(entry):
        raise ConflictError(f"Stock {entry.symbol} is already on the watchlist.")
    logger.info("watchlist.add symbol=%s", entry.symbol)
    return _to_item(entry, overview)


def list_watchlist(store: WatchlistStore, providers: ProviderBundle) -> list[WatchlistItem]:
    """Return monitored symbols with current information when available."""
    return [_item_with_current_data(providers, entry) for entry in store.list_entries()]


def get_watchlist_stock(
    store: WatchlistStore,
    providers: ProviderBundle,
    symbol: str,
) -> WatchlistItem:
    """Return current information for one monitored symbol."""
    entry = _require_entry(store, symbol)
    return _item_with_current_data(providers, entry)


def remove_watchlist_stock(store: WatchlistStore, symbol: str) -> WatchlistRemoval:
    """Stop monitoring a symbol."""
    token = _require_symbol(symbol)
    removed = store.remove(token)
    if removed is None:
        raise NotFoundError(f"Stock {token} is not on the watchlist.")
    logger.info("watchlist.remove symbol=%s", token)
    return WatchlistRemoval(symbol=removed.symbol, removed=True)


def open_watchlist_stock(
    store: WatchlistStore,
    providers: ProviderBundle,
    symbol: str,
) -> WatchlistOpenResponse:
    """Open a monitored symbol through Stock Analyzer selection.

    This is navigation, not analysis. The compiled workflow is not invoked.
    """
    entry = _require_entry(store, symbol)
    overview = select_stock(providers, entry.symbol)
    return WatchlistOpenResponse(
        symbol=overview.symbol,
        selected=overview.selected,
        overview=overview,
    )


def _item_with_current_data(providers: ProviderBundle, entry: WatchlistEntry) -> WatchlistItem:
    overview, unavailable = _safe_overview(providers, entry.symbol)
    return _to_item(entry, overview, unavailable=unavailable)


def _safe_overview(
    providers: ProviderBundle,
    symbol: str,
) -> tuple[StockOverview | None, list[str]]:
    try:
        return get_stock_overview(providers, symbol), []
    except (NotFoundError, ProviderError):
        return None, ["current_information"]


def _to_item(
    entry: WatchlistEntry,
    overview: StockOverview | None,
    *,
    unavailable: list[str] | None = None,
) -> WatchlistItem:
    extra = list(unavailable or [])
    if overview is None:
        return WatchlistItem(
            symbol=entry.symbol,
            name=entry.name,
            exchange=entry.exchange,
            currency=entry.currency,
            added_at=entry.added_at,
            unavailable=_unique([*extra, "current_information"]),
        )
    return WatchlistItem(
        symbol=entry.symbol,
        name=overview.name if overview.name else entry.name,
        exchange=overview.exchange if overview.exchange else entry.exchange,
        currency=overview.currency if overview.currency else entry.currency,
        added_at=entry.added_at,
        quote=overview.quote,
        volume=overview.volume,
        unavailable=_unique([*list(overview.unavailable), *extra]),
        evidence=list(overview.evidence),
    )


def _require_entry(store: WatchlistStore, symbol: str) -> WatchlistEntry:
    token = _require_symbol(symbol)
    entry = store.get(token)
    if entry is None:
        raise NotFoundError(f"Stock {token} is not on the watchlist.")
    return entry


def _require_symbol(symbol: str) -> str:
    try:
        return normalize_symbol(symbol)
    except ValueError as exc:
        raise AppError("Invalid stock symbol.", status_code=422, error_code="validation_error") from exc


def _unique(values: list[str]) -> list[NonEmptyText]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
