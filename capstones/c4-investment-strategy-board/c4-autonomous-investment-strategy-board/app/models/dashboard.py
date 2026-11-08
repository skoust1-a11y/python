"""Dashboard overview payloads.

These models are compact entry-point summaries. They do not include
specialist analysis, recommendations, or stock-level research.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field

from app.models.common import DomainModel, Evidence
from app.models.types import (
    CurrencyCode,
    FiniteNumber,
    NonEmptyText,
    NonNegativeFinite,
    Symbol,
    UnitInterval,
)

MarketSession = Literal["open", "closed", "pre_market", "after_hours", "unknown"]
WeightBasis = Literal["market_value", "uploaded_weight", "cost_value", "insufficient_data"]
ConcentrationLabel = Literal["low", "moderate", "high", "insufficient_data"]
DiversificationLabel = Literal["diversified", "moderate", "concentrated", "insufficient_data"]


class IndexOverview(DomainModel):
    """One index level plus current-day performance."""

    symbol: Symbol
    name: NonEmptyText | None = None
    value: NonNegativeFinite | None = None
    change: FiniteNumber | None = None
    change_percent: FiniteNumber | None = None
    timestamp: AwareDatetime | None = None
    currency: CurrencyCode | None = None
    exchange: NonEmptyText | None = None


class MarketOverview(DomainModel):
    """NIFTY 50, major Indian indices, session, and retrieval time."""

    nifty50: IndexOverview | None = None
    indices: list[IndexOverview] = Field(default_factory=list)
    session: MarketSession = "unknown"
    timezone: NonEmptyText | None = None
    trading_hours: NonEmptyText | None = None
    as_of: AwareDatetime | None = None
    provider: NonEmptyText | None = None
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class AllocationSlice(DomainModel):
    """One compact allocation row for the dashboard."""

    symbol: Symbol
    name: NonEmptyText | None = None
    weight: UnitInterval | None = None
    market_value: NonNegativeFinite | None = None


class PortfolioRiskOverview(DomainModel):
    """High-level concentration and diversification labels only."""

    concentration: ConcentrationLabel = "insufficient_data"
    diversification: DiversificationLabel = "insufficient_data"
    largest_symbol: Symbol | None = None
    largest_weight: UnitInterval | None = None
    hhi: NonNegativeFinite | None = None
    effective_n: NonNegativeFinite | None = None
    top3_share: UnitInterval | None = None
    oversized_symbols: list[Symbol] = Field(default_factory=list)
    weight_basis: WeightBasis = "insufficient_data"


class PortfolioOverview(DomainModel):
    """Imported portfolio snapshot for the dashboard. Not an analysis result."""

    id: str
    name: NonEmptyText | None = None
    holding_count: int
    market_value: NonNegativeFinite | None = None
    day_change: FiniteNumber | None = None
    day_change_percent: FiniteNumber | None = None
    cost_value: NonNegativeFinite | None = None
    currency: CurrencyCode | None = None
    mixed_currency: bool = False
    allocation: list[AllocationSlice] = Field(default_factory=list)
    risk: PortfolioRiskOverview
    imported_at: AwareDatetime
    quoted_holding_count: int = 0
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class DashboardOverview(DomainModel):
    """Lightweight market and optional portfolio summary."""

    market: MarketOverview
    portfolio: PortfolioOverview | None = None
