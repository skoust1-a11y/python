"""In-memory persistence for Watchlist symbols.

Watchlist entries are independent of uploaded portfolios and of Stock Analyzer
runs. Duplicate symbols are rejected at the store boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Protocol


@dataclass(frozen=True)
class WatchlistEntry:
    """Persisted monitoring row. Quotes are not stored."""

    symbol: str
    name: str | None
    exchange: str | None
    currency: str | None
    added_at: datetime


class WatchlistStore(Protocol):
    """Persistence contract for monitored symbols."""

    def add(self, entry: WatchlistEntry) -> bool:
        """Insert a symbol. Returns False when it is already present."""

    def get(self, symbol: str) -> WatchlistEntry | None:
        """Return one entry, or None."""

    def list_entries(self) -> list[WatchlistEntry]:
        """Return monitored symbols, newest first."""

    def remove(self, symbol: str) -> WatchlistEntry | None:
        """Delete one entry and return it, or None."""


class InMemoryWatchlistStore:
    """Process-local store used by the prototype Watchlist API."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._entries: dict[str, WatchlistEntry] = {}

    def add(self, entry: WatchlistEntry) -> bool:
        key = _key(entry.symbol)
        with self._lock:
            if key in self._entries:
                return False
            self._entries[key] = entry
            return True

    def get(self, symbol: str) -> WatchlistEntry | None:
        with self._lock:
            return self._entries.get(_key(symbol))

    def list_entries(self) -> list[WatchlistEntry]:
        with self._lock:
            entries = list(self._entries.values())
        return sorted(entries, key=lambda item: item.added_at, reverse=True)

    def remove(self, symbol: str) -> WatchlistEntry | None:
        with self._lock:
            return self._entries.pop(_key(symbol), None)


def _key(symbol: str) -> str:
    return symbol.strip().upper()
