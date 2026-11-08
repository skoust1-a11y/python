"""In-memory persistence for single-stock analysis runs.

Stock Analyzer results are stored independently of uploaded portfolios.
"""

from __future__ import annotations

from threading import Lock
from typing import Protocol

from app.models.analysis import StockAnalysisResult


class StockAnalysisStore(Protocol):
    """Persistence contract for Stock Analyzer runs."""

    def save_analysis(self, result: StockAnalysisResult) -> None:
        """Insert or replace a completed stock analysis."""

    def get_analysis(self, analysis_id: str) -> StockAnalysisResult | None:
        """Return a stored stock analysis, or None."""

    def list_analyses(self, symbol: str) -> list[StockAnalysisResult]:
        """Return analyses for one symbol, newest first."""


class InMemoryStockAnalysisStore:
    """Process-local store used by the prototype Stock Analyzer API."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._analyses: dict[str, StockAnalysisResult] = {}

    def save_analysis(self, result: StockAnalysisResult) -> None:
        with self._lock:
            self._analyses[result.id] = result

    def get_analysis(self, analysis_id: str) -> StockAnalysisResult | None:
        with self._lock:
            return self._analyses.get(analysis_id)

    def list_analyses(self, symbol: str) -> list[StockAnalysisResult]:
        token = symbol.strip().upper()
        with self._lock:
            matches = [item for item in self._analyses.values() if item.symbol == token]
        return sorted(matches, key=lambda item: item.created_at, reverse=True)
