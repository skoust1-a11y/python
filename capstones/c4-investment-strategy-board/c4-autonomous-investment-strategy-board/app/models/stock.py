"""Public Stock Analyzer HTTP models.

Search, selection, and retrieved market/fundamental payloads stay independent
of any uploaded portfolio. Vendor field names stay off this surface.
"""

from __future__ import annotations

from pydantic import Field

from app.models.common import DomainModel, Evidence
from app.models.fundamentals import CompanyProfile, FinancialMetrics, ValuationMetrics
from app.models.market import InstrumentMatch, MarketInfo, MarketQuote, OhlcSeries, VolumeSnapshot
from app.models.types import NonEmptyText, Symbol
from app.workflow.state import FundamentalDataSnapshot, MarketDataSnapshot, SelectedStock


class StockSearchResponse(DomainModel):
    """Provider-backed instrument matches for a user search query."""

    query: NonEmptyText
    matches: list[InstrumentMatch] = Field(default_factory=list)


class StockSelectionRequest(DomainModel):
    """Client choice of a single instrument. Not a portfolio holding."""

    symbol: Symbol


class SuggestedQuestion(DomainModel):
    """A canned analyzer prompt. The text is a question, not market data."""

    id: NonEmptyText
    question: NonEmptyText
    topic: NonEmptyText


class SuggestedQuestionList(DomainModel):
    """Suggested questions for the selected instrument."""

    symbol: Symbol
    questions: list[SuggestedQuestion] = Field(default_factory=list)


class StockOverview(DomainModel):
    """Current identity and quote for a selected instrument."""

    symbol: Symbol
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    asset_class: str | None = None
    quote: MarketQuote | None = None
    volume: VolumeSnapshot | None = None
    market_info: MarketInfo | None = None
    profile: CompanyProfile | None = None
    selected: SelectedStock
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class StockMarketData(DomainModel):
    """Retrieved market facts plus compact indicators. Bars are not invented."""

    symbol: Symbol
    quote: MarketQuote | None = None
    volume: VolumeSnapshot | None = None
    market_info: MarketInfo | None = None
    history: OhlcSeries | None = None
    snapshot: MarketDataSnapshot | None = None
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class StockFundamentalData(DomainModel):
    """Retrieved company profile, metrics, and valuation. Figures are not invented."""

    symbol: Symbol
    profile: CompanyProfile | None = None
    metrics: FinancialMetrics | None = None
    valuation: ValuationMetrics | None = None
    snapshot: FundamentalDataSnapshot | None = None
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
