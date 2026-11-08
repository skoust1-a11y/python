"""User-uploaded portfolio models.

The uploaded file is the only user-provided financial dataset. These models
hold positions as submitted; they do not include market prices or valuations.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import AwareDatetime, computed_field, model_validator

from app.models.common import DomainModel
from app.models.types import (
    CurrencyCode,
    NonEmptyText,
    NonNegativeFinite,
    PositiveFinite,
    Symbol,
    UnitInterval,
)

PortfolioFormat = Literal["csv", "xlsx"]
PreviewStatus = Literal["valid", "valid_with_warnings", "invalid"]
IssueSeverity = Literal["error", "warning"]
SymbolValidationStatus = Literal["valid", "invalid", "missing"]
PortfolioStatus = Literal["imported"]


class ValidationIssue(DomainModel):
    """One structured validation error or warning from portfolio ingestion."""

    severity: IssueSeverity
    code: str
    message: str
    row: int | None = None
    column: str | None = None
    value: str | None = None


class SymbolValidation(DomainModel):
    """Format-only ticker check. Listing/market existence is not verified here."""

    input: str | None = None
    normalized: str | None = None
    status: SymbolValidationStatus
    reason: str | None = None


class Holding(DomainModel):
    """One normalized position from a confirmed portfolio upload."""

    symbol: Symbol
    quantity: PositiveFinite
    average_cost: NonNegativeFinite | None = None
    currency: CurrencyCode | None = None
    name: NonEmptyText | None = None
    weight: UnitInterval | None = None
    symbol_validation: SymbolValidation

    @computed_field
    @property
    def cost_value(self) -> float | None:
        """Quantity times user-supplied average cost. Not a market value."""
        if self.average_cost is None:
            return None
        return self.quantity * self.average_cost


class PreviewHolding(DomainModel):
    """A parsed row shown before import. Invalid rows stay visible."""

    row: int
    symbol: str | None = None
    quantity: float | None = None
    average_cost: float | None = None
    currency: str | None = None
    name: str | None = None
    weight: float | None = None
    symbol_validation: SymbolValidation
    valid: bool = False

    @computed_field
    @property
    def cost_value(self) -> float | None:
        if self.quantity is None or self.average_cost is None:
            return None
        return self.quantity * self.average_cost


class Portfolio(DomainModel):
    """Confirmed, persisted holdings. Available only after explicit import."""

    id: str
    status: PortfolioStatus = "imported"
    name: NonEmptyText | None = None
    holdings: list[Holding]
    base_currency: CurrencyCode | None = None
    source_filename: NonEmptyText
    source_format: PortfolioFormat
    imported_at: AwareDatetime
    upload_id: str | None = None

    @computed_field
    @property
    def holding_count(self) -> int:
        return len(self.holdings)

    @model_validator(mode="after")
    def holdings_must_be_unique(self) -> Self:
        symbols = [holding.symbol for holding in self.holdings]
        if len(symbols) != len(set(symbols)):
            raise ValueError("portfolio holdings must not contain duplicate symbols")
        if not self.holdings:
            raise ValueError("portfolio must contain at least one holding")
        return self


class PortfolioPreview(DomainModel):
    """Staged upload result. Confirmation is required before persistence."""

    upload_id: str
    status: PreviewStatus
    can_confirm: bool
    filename: NonEmptyText
    format: PortfolioFormat | None = None
    holdings: list[PreviewHolding]
    issues: list[ValidationIssue]
    created_at: AwareDatetime
    expires_at: AwareDatetime
    imported_portfolio_id: str | None = None

    @computed_field
    @property
    def holding_count(self) -> int:
        return len(self.holdings)

    @computed_field
    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @computed_field
    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


class PortfolioSummary(DomainModel):
    """Compact listing row for confirmed portfolios. Holdings are omitted."""

    id: str
    status: PortfolioStatus = "imported"
    name: NonEmptyText | None = None
    holding_count: int
    base_currency: CurrencyCode | None = None
    source_filename: NonEmptyText
    source_format: PortfolioFormat
    imported_at: AwareDatetime


class PortfolioHoldings(DomainModel):
    """Confirmed positions for one imported portfolio."""

    portfolio_id: str
    holdings: list[Holding]

    @computed_field
    @property
    def holding_count(self) -> int:
        return len(self.holdings)
