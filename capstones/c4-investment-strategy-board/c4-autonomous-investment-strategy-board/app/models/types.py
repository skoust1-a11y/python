"""Reusable field types for provider-independent domain models."""

from __future__ import annotations

import re
from typing import Annotated, Any
from urllib.parse import urlparse

from pydantic import AfterValidator, Field

SYMBOL_PATTERN = re.compile(r"^\^?[A-Z0-9][A-Z0-9.\-]{0,31}$")
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
EXCHANGE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,15}$")
PERIOD_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_\-/]{0,31}$")


def _as_stripped_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value.strip()


def normalize_symbol(value: str) -> str:
    normalized = _as_stripped_text(value, "symbol").upper()
    if not normalized:
        raise ValueError("symbol is required")
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError("symbol must be a ticker or index code")
    return normalized


def normalize_currency(value: str) -> str:
    normalized = _as_stripped_text(value, "currency").upper()
    if not CURRENCY_PATTERN.fullmatch(normalized):
        raise ValueError("currency must be a 3-letter ISO 4217 code")
    return normalized


def normalize_exchange(value: str) -> str:
    normalized = _as_stripped_text(value, "exchange").upper()
    if not normalized:
        raise ValueError("exchange is required")
    if not EXCHANGE_PATTERN.fullmatch(normalized):
        raise ValueError("exchange must be an exchange code")
    return normalized


def normalize_period(value: str) -> str:
    normalized = _as_stripped_text(value, "period").lower()
    if not normalized:
        raise ValueError("period is required")
    if not PERIOD_PATTERN.fullmatch(normalized):
        raise ValueError("period must be a reporting period or interval token")
    return normalized


def normalize_label(field: str):
    def validator(value: str) -> str:
        normalized = _as_stripped_text(value, field)
        if not normalized:
            raise ValueError(f"{field} is required")
        return normalized

    return validator


def normalize_http_url(value: str) -> str:
    normalized = _as_stripped_text(value, "url")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an absolute http or https URL")
    return normalized


Symbol = Annotated[str, AfterValidator(normalize_symbol)]
CurrencyCode = Annotated[str, AfterValidator(normalize_currency)]
ExchangeCode = Annotated[str, AfterValidator(normalize_exchange)]
Period = Annotated[str, AfterValidator(normalize_period)]
ProviderName = Annotated[str, AfterValidator(normalize_label("provider"))]
SourceName = Annotated[str, AfterValidator(normalize_label("source"))]
Headline = Annotated[str, AfterValidator(normalize_label("headline"))]
NonEmptyText = Annotated[str, AfterValidator(normalize_label("value"))]
HttpUrlString = Annotated[str, AfterValidator(normalize_http_url)]
FiniteNumber = Annotated[float, Field(allow_inf_nan=False)]
NonNegativeFinite = Annotated[float, Field(ge=0, allow_inf_nan=False)]
PositiveFinite = Annotated[float, Field(gt=0, allow_inf_nan=False)]
UnitInterval = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
NonNegativeInt = Annotated[int, Field(ge=0)]
