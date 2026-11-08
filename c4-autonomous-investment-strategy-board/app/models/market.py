"""Provider-independent market-data payloads.

Adapters map vendor responses onto these models. Callers never see ticker-API
field names, query strings, or SDK types.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import AwareDatetime, Field, computed_field, model_validator

from app.models.common import DataSourceMetadata, DomainModel
from app.models.types import (
    CurrencyCode,
    ExchangeCode,
    FiniteNumber,
    NonEmptyText,
    NonNegativeFinite,
    Period,
    Symbol,
)


class InstrumentMatch(DomainModel):
    """One instrument returned by a provider-independent search."""

    symbol: Symbol
    source: DataSourceMetadata
    name: NonEmptyText | None = None
    exchange: ExchangeCode | None = None
    currency: CurrencyCode | None = None
    asset_class: NonEmptyText | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class MarketQuote(DomainModel):
    """Current market quote for an instrument."""

    symbol: Symbol
    value: NonNegativeFinite
    timestamp: AwareDatetime
    currency: CurrencyCode | None = None
    exchange: ExchangeCode | None = None
    bid: NonNegativeFinite | None = None
    ask: NonNegativeFinite | None = None
    change: FiniteNumber | None = None
    change_percent: FiniteNumber | None = None
    volume: NonNegativeFinite | None = None
    source: DataSourceMetadata
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def bid_must_not_exceed_ask(self) -> Self:
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ValueError("bid must be less than or equal to ask")
        return self


class HistoricalPrice(DomainModel):
    """One open/high/low/close observation for a symbol and period."""

    symbol: Symbol
    timestamp: AwareDatetime
    open: NonNegativeFinite
    high: NonNegativeFinite
    low: NonNegativeFinite
    close: NonNegativeFinite
    period: Period
    volume: NonNegativeFinite | None = None
    currency: CurrencyCode | None = None
    exchange: ExchangeCode | None = None
    source: DataSourceMetadata
    extra: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def value(self) -> float:
        """Normalized last price for the period, equal to close."""
        return self.close

    @model_validator(mode="after")
    def ohlc_must_be_consistent(self) -> Self:
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if self.open < self.low or self.open > self.high:
            raise ValueError("open must be between low and high")
        if self.close < self.low or self.close > self.high:
            raise ValueError("close must be between low and high")
        return self


class MarketIndex(DomainModel):
    """Level and metadata for a market index."""

    symbol: Symbol
    value: NonNegativeFinite
    timestamp: AwareDatetime
    name: NonEmptyText | None = None
    currency: CurrencyCode | None = None
    exchange: ExchangeCode | None = None
    change: FiniteNumber | None = None
    change_percent: FiniteNumber | None = None
    constituents: list[Symbol] | None = None
    source: DataSourceMetadata
    extra: dict[str, Any] = Field(default_factory=dict)


class OhlcSeries(DomainModel):
    """Historical OHLC series for one symbol and interval."""

    symbol: Symbol
    period: Period
    source: DataSourceMetadata
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None
    prices: list[HistoricalPrice] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def prices_must_match_series(self) -> Self:
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must be less than or equal to end")
        for price in self.prices:
            if price.symbol != self.symbol:
                raise ValueError("historical prices must use the series symbol")
            if price.period != self.period:
                raise ValueError("historical prices must use the series period")
        return self


class VolumeSnapshot(DomainModel):
    """Traded volume for an instrument."""

    symbol: Symbol
    value: NonNegativeFinite
    timestamp: AwareDatetime
    average_volume: NonNegativeFinite | None = None
    currency: CurrencyCode | None = None
    exchange: ExchangeCode | None = None
    source: DataSourceMetadata
    extra: dict[str, Any] = Field(default_factory=dict)


class MarketInfo(DomainModel):
    """Exchange, currency, and other descriptive market metadata."""

    symbol: Symbol
    source: DataSourceMetadata
    name: NonEmptyText | None = None
    exchange: ExchangeCode | None = None
    currency: CurrencyCode | None = None
    asset_class: NonEmptyText | None = None
    timezone: NonEmptyText | None = None
    trading_hours: NonEmptyText | None = None
    session: NonEmptyText | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


Quote = MarketQuote
OhlcBar = HistoricalPrice
IndexInfo = MarketIndex
SearchHit = InstrumentMatch
