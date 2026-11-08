"""Provider-independent fundamental-data payloads.

Field names are standard financial concepts. Vendor-specific extras belong in
`extra`, not in the provider interface.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import AwareDatetime, Field

from app.models.common import DataSourceMetadata, DomainModel
from app.models.types import (
    CurrencyCode,
    ExchangeCode,
    FiniteNumber,
    HttpUrlString,
    NonEmptyText,
    NonNegativeFinite,
    NonNegativeInt,
    Period,
    Symbol,
)

StatementType = Literal["income", "balance_sheet", "cash_flow"]
ReportingPeriod = Literal["annual", "quarterly"]


class CompanyProfile(DomainModel):
    """Descriptive company information."""

    symbol: Symbol
    source: DataSourceMetadata
    name: NonEmptyText | None = None
    sector: NonEmptyText | None = None
    industry: NonEmptyText | None = None
    description: str | None = None
    country: NonEmptyText | None = None
    currency: CurrencyCode | None = None
    exchange: ExchangeCode | None = None
    website: HttpUrlString | None = None
    employees: NonNegativeInt | None = None
    timestamp: AwareDatetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class FinancialStatement(DomainModel):
    """One filing period of an income statement, balance sheet, or cash-flow statement.

    Line items stay a mapping so adapters can translate vendor schemas without
    leaking those schemas into callers.
    """

    symbol: Symbol
    statement_type: StatementType
    period: ReportingPeriod
    source: DataSourceMetadata
    currency: CurrencyCode | None = None
    exchange: ExchangeCode | None = None
    period_end: date | None = None
    fiscal_period: Period | None = None
    timestamp: AwareDatetime | None = None
    line_items: dict[str, FiniteNumber | str | None] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class FinancialMetrics(DomainModel):
    """Common profitability, returns, leverage, and valuation metrics."""

    symbol: Symbol
    source: DataSourceMetadata
    period: Period | None = None
    timestamp: AwareDatetime | None = None
    currency: CurrencyCode | None = None
    exchange: ExchangeCode | None = None
    revenue: FiniteNumber | None = None
    net_income: FiniteNumber | None = None
    eps: FiniteNumber | None = None
    ebitda: FiniteNumber | None = None
    operating_margin: FiniteNumber | None = None
    profit_margin: FiniteNumber | None = None
    roe: FiniteNumber | None = None
    roa: FiniteNumber | None = None
    debt_to_equity: FiniteNumber | None = None
    current_ratio: FiniteNumber | None = None
    pe_ratio: FiniteNumber | None = None
    forward_pe: FiniteNumber | None = None
    pb_ratio: FiniteNumber | None = None
    ps_ratio: FiniteNumber | None = None
    peg_ratio: FiniteNumber | None = None
    ev_to_ebitda: FiniteNumber | None = None
    market_cap: NonNegativeFinite | None = None
    enterprise_value: FiniteNumber | None = None
    dividend_yield: FiniteNumber | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ValuationMetrics(DomainModel):
    """Common valuation multiples and related measures."""

    symbol: Symbol
    source: DataSourceMetadata
    timestamp: AwareDatetime | None = None
    currency: CurrencyCode | None = None
    exchange: ExchangeCode | None = None
    pe_ratio: FiniteNumber | None = None
    forward_pe: FiniteNumber | None = None
    pb_ratio: FiniteNumber | None = None
    ps_ratio: FiniteNumber | None = None
    peg_ratio: FiniteNumber | None = None
    ev_to_ebitda: FiniteNumber | None = None
    market_cap: NonNegativeFinite | None = None
    enterprise_value: FiniteNumber | None = None
    dividend_yield: FiniteNumber | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


KeyFinancialMetrics = FinancialMetrics
