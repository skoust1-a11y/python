"""Stock Analyzer retrieval use cases.

Search, selection, and current/market/fundamental views call injected
provider contracts. They never invent prices or metrics and never read
an uploaded portfolio.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from app.exceptions import AppError, NotFoundError, ProviderError, ProviderNotImplementedError
from app.models.common import Evidence

logger = logging.getLogger("app.services")
from app.models.stock import (
    StockFundamentalData,
    StockMarketData,
    StockOverview,
    StockSearchResponse,
    SuggestedQuestion,
    SuggestedQuestionList,
)
from app.models.types import NonEmptyText, normalize_period, normalize_symbol
from app.providers.registry import ProviderBundle
from app.tools.fundamentals import classify_financial_health, classify_profitability
from app.tools.market import (
    classify_trend,
    closes,
    price_momentum,
    realized_volatility,
    sorted_bars,
)
from app.workflow.state import FundamentalDataSnapshot, MarketDataSnapshot, SelectedStock

T = TypeVar("T")

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 25
MAX_SEARCH_QUERY_LENGTH = 64

SUGGESTED_QUESTIONS: tuple[tuple[str, str, str], ...] = (
    ("trend", "market", "What is the current market trend for {symbol}?"),
    (
        "fundamentals",
        "fundamentals",
        "How healthy are {symbol}'s latest reported fundamentals?",
    ),
    (
        "valuation",
        "valuation",
        "Is {symbol} expensive or cheap based on available valuation metrics?",
    ),
    ("risks", "risk", "What are the main risks of holding {symbol}?"),
    (
        "summary",
        "overview",
        "Give an evidence-based summary of {symbol} as a single-name investment.",
    ),
)


def search_stocks(
    providers: ProviderBundle,
    query: str,
    *,
    limit: int = DEFAULT_SEARCH_LIMIT,
    country: str | None = None,
) -> StockSearchResponse:
    """Search instruments through the configured market-data adapter."""
    token = _require_query(query)
    capped = _require_limit(limit)
    matches = providers.market_data.search_instruments(token, limit=capped, country=country)
    return StockSearchResponse(query=token, matches=list(matches)[:capped])


def select_stock(providers: ProviderBundle, symbol: str) -> StockOverview:
    """Resolve a chosen instrument and return current information."""
    return get_stock_overview(providers, symbol)


def get_stock_overview(providers: ProviderBundle, symbol: str) -> StockOverview:
    """Return current identity, quote, and profile for one instrument."""
    token = _require_symbol(symbol)
    unavailable: list[str] = []
    unimplemented: list[ProviderNotImplementedError] = []
    quote = _fetch(lambda: providers.market_data.get_quote(token), unavailable, "current_price", unimplemented)
    volume = _fetch(lambda: providers.market_data.get_volume(token), unavailable, "volume", unimplemented)
    info = _fetch(lambda: providers.market_data.get_market_info(token), unavailable, "market_info", unimplemented)
    profile = _fetch(
        lambda: providers.fundamentals.get_company_profile(token),
        unavailable,
        "company_profile",
        unimplemented,
    )
    _raise_if_unresolved(quote, volume, info, profile, unimplemented=unimplemented, symbol=token)

    name = _first_present(
        profile.name if profile is not None else None,
        info.name if info is not None else None,
    )
    exchange = _first_present(
        quote.exchange if quote is not None else None,
        info.exchange if info is not None else None,
        profile.exchange if profile is not None else None,
    )
    currency = _first_present(
        quote.currency if quote is not None else None,
        info.currency if info is not None else None,
        profile.currency if profile is not None else None,
    )
    evidence = _collect_evidence(
        (quote, "price", quote.value if quote is not None else None),
        (volume, "volume", volume.value if volume is not None else None),
        (info, "market_info", token),
        (profile, "company_name", name),
        symbol=token,
    )
    return StockOverview(
        symbol=token,
        name=name,
        exchange=exchange,
        currency=currency,
        asset_class=info.asset_class if info is not None else None,
        quote=quote,
        volume=volume,
        market_info=info,
        profile=profile,
        selected=SelectedStock(symbol=token, name=name),
        unavailable=_unique(unavailable),
        evidence=evidence,
    )


def get_stock_market_data(
    providers: ProviderBundle,
    symbol: str,
    *,
    interval: str = "1d",
) -> StockMarketData:
    """Return retrieved market facts and compact indicators for one instrument."""
    token = _require_symbol(symbol)
    period = _require_interval(interval)
    unavailable: list[str] = []
    unimplemented: list[ProviderNotImplementedError] = []
    quote = _fetch(lambda: providers.market_data.get_quote(token), unavailable, "current_price", unimplemented)
    volume = _fetch(lambda: providers.market_data.get_volume(token), unavailable, "volume", unimplemented)
    info = _fetch(lambda: providers.market_data.get_market_info(token), unavailable, "market_info", unimplemented)
    history = _fetch(
        lambda: providers.market_data.get_historical_ohlc(token, interval=period),
        unavailable,
        "historical_ohlc",
        unimplemented,
    )
    if history is not None and not history.prices:
        unavailable.append("historical_ohlc")
        history = None
    _raise_if_unresolved(quote, volume, info, history, unimplemented=unimplemented, symbol=token)

    bars = sorted_bars(history)
    asset_closes = closes(history)
    trend = classify_trend(asset_closes) if asset_closes else None
    if trend is None and "historical_ohlc" not in unavailable:
        unavailable.append("trend")
    volatility = realized_volatility(asset_closes) if asset_closes else None
    momentum = price_momentum(asset_closes) if asset_closes else None
    currency = _first_present(
        quote.currency if quote is not None else None,
        info.currency if info is not None else None,
        bars[0].currency if bars else None,
    )
    exchange = _first_present(
        quote.exchange if quote is not None else None,
        info.exchange if info is not None else None,
        bars[0].exchange if bars else None,
    )
    snapshot = MarketDataSnapshot(
        symbol=token,
        current_price=quote.value if quote is not None else None,
        currency=currency,
        exchange=exchange,
        change_percent=quote.change_percent if quote is not None else None,
        volume=volume.value if volume is not None else None,
        trend=trend,
        volatility=volatility,
        momentum=momentum,
        unavailable=_unique(unavailable),
        as_of=quote.timestamp if quote is not None else None,
        source=quote.source if quote is not None else (info.source if info is not None else None),
    )
    evidence = _collect_evidence(
        (quote, "price", quote.value if quote is not None else None),
        (volume, "volume", volume.value if volume is not None else None),
        (history, "historical_ohlc", len(bars) if bars else None),
        (info, "market_info", token),
        symbol=token,
        period=period,
    )
    return StockMarketData(
        symbol=token,
        quote=quote,
        volume=volume,
        market_info=info,
        history=history,
        snapshot=snapshot,
        unavailable=_unique(unavailable),
        evidence=evidence,
    )


def get_stock_fundamentals(providers: ProviderBundle, symbol: str) -> StockFundamentalData:
    """Return retrieved profile, metrics, and valuation for one instrument."""
    token = _require_symbol(symbol)
    unavailable: list[str] = []
    unimplemented: list[ProviderNotImplementedError] = []
    profile = _fetch(
        lambda: providers.fundamentals.get_company_profile(token),
        unavailable,
        "company_profile",
        unimplemented,
    )
    metrics = _fetch(
        lambda: providers.fundamentals.get_key_metrics(token),
        unavailable,
        "key_metrics",
        unimplemented,
    )
    valuation = _fetch(
        lambda: providers.fundamentals.get_valuation_metrics(token),
        unavailable,
        "valuation_metrics",
        unimplemented,
    )
    _raise_if_unresolved(profile, metrics, valuation, unimplemented=unimplemented, symbol=token)

    profitability = classify_profitability(metrics.net_income if metrics is not None else None)
    health = classify_financial_health(
        profitability=profitability,
        liquidity="insufficient_data",
        cash_generation="insufficient_data",
    )
    snapshot = FundamentalDataSnapshot(
        symbol=token,
        company_name=profile.name if profile is not None else None,
        sector=profile.sector if profile is not None else None,
        industry=profile.industry if profile is not None else None,
        revenue=metrics.revenue if metrics is not None else None,
        earnings=metrics.net_income if metrics is not None else None,
        pe_ratio=_first_present(
            valuation.pe_ratio if valuation is not None else None,
            metrics.pe_ratio if metrics is not None else None,
        ),
        profitability=None if profitability == "insufficient_data" else profitability,
        financial_health=None if health == "insufficient_data" else health,
        unavailable=_unique(unavailable),
        as_of=metrics.timestamp if metrics is not None else None,
        source=profile.source if profile is not None else None,
    )
    evidence = _collect_evidence(
        (profile, "company_name", profile.name if profile is not None else None),
        (metrics, "revenue", metrics.revenue if metrics is not None else None),
        (metrics, "net_income", metrics.net_income if metrics is not None else None),
        (valuation, "pe_ratio", valuation.pe_ratio if valuation is not None else None),
        symbol=token,
    )
    return StockFundamentalData(
        symbol=token,
        profile=profile,
        metrics=metrics,
        valuation=valuation,
        snapshot=snapshot,
        unavailable=_unique(unavailable),
        evidence=evidence,
    )


def suggested_questions(symbol: str) -> SuggestedQuestionList:
    """Return canned analyzer prompts for the selected instrument."""
    token = _require_symbol(symbol)
    questions = [
        SuggestedQuestion(id=item_id, topic=topic, question=template.format(symbol=token))
        for item_id, topic, template in SUGGESTED_QUESTIONS
    ]
    return SuggestedQuestionList(symbol=token, questions=questions)


def _require_query(query: str) -> str:
    token = query.strip()
    if not token:
        raise AppError("Search query is required.", status_code=422, error_code="validation_error")
    if len(token) > MAX_SEARCH_QUERY_LENGTH:
        raise AppError(
            "Search query is too long.",
            status_code=422,
            error_code="validation_error",
        )
    return token


def _require_limit(limit: int) -> int:
    if limit < 1 or limit > MAX_SEARCH_LIMIT:
        raise AppError(
            f"Search limit must be between 1 and {MAX_SEARCH_LIMIT}.",
            status_code=422,
            error_code="validation_error",
        )
    return limit


def _require_symbol(symbol: str) -> str:
    try:
        return normalize_symbol(symbol)
    except ValueError as exc:
        raise AppError("Invalid stock symbol.", status_code=422, error_code="validation_error") from exc


def _require_interval(interval: str) -> str:
    try:
        return normalize_period(interval)
    except ValueError as exc:
        raise AppError("Invalid market interval.", status_code=422, error_code="validation_error") from exc


def _fetch(
    operation: Callable[[], T],
    unavailable: list[str],
    label: str,
    unimplemented: list[ProviderNotImplementedError],
) -> T | None:
    try:
        return operation()
    except ProviderNotImplementedError as exc:
        unavailable.append(label)
        unimplemented.append(exc)
        return None
    except ProviderError:
        unavailable.append(label)
        return None


def _raise_if_unresolved(*payloads: object, unimplemented: list[ProviderNotImplementedError], symbol: str) -> None:
    if any(item is not None for item in payloads):
        return
    if unimplemented:
        raise unimplemented[0]
    raise NotFoundError(f"Stock {symbol} was not found.")


def _collect_evidence(
    *items: tuple[object | None, str, object | None],
    symbol: str,
    period: str | None = None,
) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen: set[str] = set()
    for payload, field, value in items:
        source = getattr(payload, "source", None)
        if payload is None or source is None:
            continue
        item = Evidence(source=source, symbol=symbol, field=field, value=value, period=period)
        key = item.model_dump_json()
        if key in seen:
            continue
        seen.add(key)
        evidence.append(item)
    return evidence


def _first_present(*values: T | None) -> T | None:
    for value in values:
        if isinstance(value, str):
            if value:
                return value
            continue
        if value is not None:
            return value
    return None


def _unique(values: list[str]) -> list[NonEmptyText]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
