"""Abstract provider contracts.

Agents and services must call these interfaces. Concrete adapters are selected
through environment configuration and the provider factories. Vendor SDK types
and API details must not appear on these contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel

from app.models.fundamentals import (
    CompanyProfile,
    FinancialMetrics,
    FinancialStatement,
    ReportingPeriod,
    StatementType,
    ValuationMetrics,
)
from app.models.market import (
    InstrumentMatch,
    MarketIndex,
    MarketInfo,
    MarketQuote,
    OhlcSeries,
    VolumeSnapshot,
)
from app.models.news import NewsArticle

TModel = TypeVar("TModel", bound=BaseModel)


class LLMProvider(ABC):
    """LLM adapter used for interpretation, synthesis, and critique only.

    Agents depend on this contract, never on a vendor SDK. Adding a provider
    means registering a new adapter; agent code stays unchanged.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Configured adapter identifier (for example, `openai` or `groq`)."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Configured model or deployment name for this adapter."""

    @property
    def fallback_name(self) -> str | None:
        """Name of the fallback adapter, if one is wired."""
        return None

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Return model text. Must not be used to invent market prices."""

    @abstractmethod
    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        """Return a Pydantic model parsed from the LLM response."""


class MarketDataProvider(ABC):
    """Quotes, search, OHLC series, volume, indices, and market metadata.

    Operations are provider-independent. Adapters translate vendor APIs onto
    these methods without exposing ticker-API query shapes to callers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Configured adapter identifier."""

    @abstractmethod
    def search_instruments(self, query: str, *, limit: int = 10) -> list[InstrumentMatch]:
        """Return instruments matching a ticker or name query.

        `query` is a domain search string. Adapters map it onto vendor lookup
        APIs and must not invent listings.
        """

    @abstractmethod
    def get_quote(self, instrument: str) -> MarketQuote:
        """Return the current quote for an instrument."""

    @abstractmethod
    def get_historical_ohlc(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        interval: str = "1d",
    ) -> OhlcSeries:
        """Return historical open/high/low/close bars.

        `interval` is a domain token such as `1d` or `1h`. Adapters map it to
        vendor-specific resolutions.
        """

    @abstractmethod
    def get_index(self, symbol: str) -> MarketIndex:
        """Return level and metadata for a market index."""

    @abstractmethod
    def get_volume(self, instrument: str) -> VolumeSnapshot:
        """Return traded volume for an instrument."""

    @abstractmethod
    def get_market_info(self, instrument: str) -> MarketInfo:
        """Return exchange, currency, and other basic market information."""


class FundamentalDataProvider(ABC):
    """Company profiles, filings, key metrics, and valuation measures."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Configured adapter identifier."""

    @abstractmethod
    def get_company_profile(self, instrument: str) -> CompanyProfile:
        """Return descriptive company information."""

    @abstractmethod
    def get_financial_statements(
        self,
        instrument: str,
        *,
        statement_type: StatementType = "income",
        period: ReportingPeriod = "annual",
    ) -> list[FinancialStatement]:
        """Return financial statements for the requested type and period."""

    @abstractmethod
    def get_key_metrics(self, instrument: str) -> FinancialMetrics:
        """Return key financial metrics such as margins, returns, and leverage."""

    @abstractmethod
    def get_valuation_metrics(self, instrument: str) -> ValuationMetrics:
        """Return valuation metrics such as multiples and market cap."""


class NewsDataProvider(ABC):
    """Company-specific and broader market news from an external source."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Configured adapter identifier."""

    @abstractmethod
    def get_company_news(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        """Return news articles about a company or instrument."""

    @abstractmethod
    def get_market_news(
        self,
        *,
        query: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        """Return general market news, optionally filtered by a domain query."""


NewsProvider = NewsDataProvider
