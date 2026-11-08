"""Shared provenance models used by every retrieved financial payload."""

from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.models.types import (
    FiniteNumber,
    HttpUrlString,
    NonEmptyText,
    Period,
    ProviderName,
    SourceName,
    Symbol,
)


class DomainModel(BaseModel):
    """Base for application models. Unknown vendor fields are rejected."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
        frozen=True,
    )


class DataSourceMetadata(DomainModel):
    """Where a payload came from and when it was observed or retrieved.

    Field names are provider-independent. Adapter identifiers belong in
    `provider`; the originating feed or publication belongs in `source`.
    """

    provider: ProviderName
    source: SourceName
    timestamp: AwareDatetime
    url: HttpUrlString | None = None
    raw_reference: str | None = None


class Evidence(DomainModel):
    """Citable fact used by agents and services.

    `source` carries provenance. `symbol`, `period`, and `value` identify the
    referenced observation without vendor field names.
    """

    source: DataSourceMetadata
    symbol: Symbol | None = None
    period: Period | None = None
    field: NonEmptyText | None = None
    value: FiniteNumber | str | None = None
    excerpt: str | None = None


class MarketObservation(DomainModel):
    """A market, fundamental, or news datum with required evidence."""

    symbol: Symbol
    field: NonEmptyText
    value: FiniteNumber | str | None = None
    unit: str | None = None
    evidence: Evidence
    extra: dict[str, Any] = Field(default_factory=dict)
