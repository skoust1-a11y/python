"""Provider-independent news payloads."""

from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, Field

from app.models.common import DataSourceMetadata, DomainModel
from app.models.types import (
    ExchangeCode,
    Headline,
    HttpUrlString,
    NonEmptyText,
    Symbol,
)


class NewsArticle(DomainModel):
    """A single headline or article retrieved from an external news source."""

    headline: Headline
    timestamp: AwareDatetime
    source: DataSourceMetadata
    summary: str | None = None
    url: HttpUrlString | None = None
    publisher: NonEmptyText | None = None
    symbol: Symbol | None = None
    exchange: ExchangeCode | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


NewsItem = NewsArticle
