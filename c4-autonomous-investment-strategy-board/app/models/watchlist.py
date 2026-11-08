"""Public Watchlist HTTP models.

The Watchlist is a monitoring and navigation surface. It stores selected
symbols and current quotes; it does not run AI analysis. Detailed analysis
belongs to Stock Analyzer.
"""

from __future__ import annotations

from pydantic import AwareDatetime, Field, computed_field

from app.models.common import DomainModel, Evidence
from app.models.market import MarketQuote, VolumeSnapshot
from app.models.stock import StockOverview
from app.models.types import NonEmptyText, Symbol
from app.workflow.state import SelectedStock


class WatchlistAddRequest(DomainModel):
    """Client request to monitor a single instrument."""

    symbol: Symbol


class WatchlistItem(DomainModel):
    """One monitored symbol with current information when available.

    Missing quotes stay unset. This is not an analysis result.
    """

    symbol: Symbol
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    added_at: AwareDatetime
    quote: MarketQuote | None = None
    volume: VolumeSnapshot | None = None
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

    @computed_field
    @property
    def analyzer_path(self) -> str:
        """Stock Analyzer route for this symbol. Navigation only."""
        return f"/stocks/{self.symbol}"


class WatchlistRemoval(DomainModel):
    """Confirmation that a symbol is no longer monitored."""

    symbol: Symbol
    removed: bool = True


class WatchlistOpenResponse(DomainModel):
    """Handoff to Stock Analyzer. Does not run AI analysis."""

    symbol: Symbol
    selected: SelectedStock
    overview: StockOverview

    @computed_field
    @property
    def analyzer_path(self) -> str:
        return f"/stocks/{self.symbol}"
