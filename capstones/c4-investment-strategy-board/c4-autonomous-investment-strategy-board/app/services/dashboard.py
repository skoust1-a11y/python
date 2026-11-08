"""Dashboard overview use cases.

Market figures come from the injected market-data provider. Portfolio
summaries use uploaded holdings plus live quotes when available. This
service never runs the analysis workflow or invents missing prices.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from app.exceptions import ProviderError, ProviderNotImplementedError
from app.models.common import Evidence

logger = logging.getLogger("app.services")
from app.models.dashboard import (
    AllocationSlice,
    DashboardOverview,
    IndexOverview,
    MarketOverview,
    MarketSession,
    PortfolioOverview,
    PortfolioRiskOverview,
)
from app.models.market import MarketIndex, MarketInfo, MarketQuote
from app.models.portfolio import Holding, Portfolio
from app.models.types import NonEmptyText
from app.providers.contracts import MarketDataProvider
from app.providers.registry import ProviderBundle
from app.repositories.portfolio import PortfolioStore
from app.services.portfolio import list_imported_portfolios
from app.tools.risk import (
    classify_concentration,
    classify_diversification,
    effective_n,
    herfindahl_hirschman_index,
    largest_share,
    oversized_symbols,
    resolve_weight_vector,
    top_n_share,
)

T = TypeVar("T")

NIFTY50_SYMBOL = "NIFTY50"
MAJOR_INDEX_SYMBOLS: tuple[tuple[str, str], ...] = (
    ("SENSEX", "SENSEX"),
    ("NIFTYBANK", "NIFTY Bank"),
    ("NIFTYIT", "NIFTY IT"),
)
MAX_ALLOCATION_ROWS = 6


def get_dashboard_overview(
    store: PortfolioStore,
    providers: ProviderBundle,
) -> DashboardOverview:
    """Return a compact market and optional portfolio overview."""
    market = _market_overview(providers.market_data)
    portfolios = list_imported_portfolios(store)
    if not portfolios:
        return DashboardOverview(market=market, portfolio=None)
    imported = store.get_portfolio(portfolios[0].id)
    if imported is None:
        return DashboardOverview(market=market, portfolio=None)
    return DashboardOverview(
        market=market,
        portfolio=_portfolio_overview(imported, providers.market_data),
    )


def _market_overview(market: MarketDataProvider) -> MarketOverview:
    unavailable: list[str] = []
    unimplemented: list[ProviderNotImplementedError] = []
    nifty = _fetch(
        lambda: market.get_index(NIFTY50_SYMBOL),
        unavailable,
        "nifty50",
        unimplemented,
    )
    info = _fetch(
        lambda: market.get_market_info(NIFTY50_SYMBOL),
        unavailable,
        "market_status",
        unimplemented,
    )
    retrieved_indices: list[tuple[MarketIndex, str]] = []
    for symbol, fallback_name in MAJOR_INDEX_SYMBOLS:
        item = _fetch(
            lambda symbol=symbol: market.get_index(symbol),
            unavailable,
            f"index:{symbol}",
            unimplemented,
        )
        if item is not None:
            retrieved_indices.append((item, fallback_name))
    indices = [_index_overview(item, fallback_name) for item, fallback_name in retrieved_indices]
    nifty_overview = _index_overview(nifty, "NIFTY 50") if nifty is not None else None
    timestamps = [
        item.timestamp
        for item in (nifty_overview, *indices)
        if item is not None and item.timestamp is not None
    ]
    if info is not None:
        timestamps.append(info.source.timestamp)
    as_of = max(timestamps) if timestamps else None
    evidence = _collect_evidence(
        (nifty, "index_level", nifty.value if nifty is not None else None, NIFTY50_SYMBOL),
        (info, "market_status", _session_from_info(info), NIFTY50_SYMBOL),
        *[
            (item, "index_level", item.value, item.symbol)
            for item, _name in retrieved_indices
        ],
    )
    return MarketOverview(
        nifty50=nifty_overview,
        indices=indices,
        session=_session_from_info(info),
        timezone=info.timezone if info is not None else None,
        trading_hours=info.trading_hours if info is not None else None,
        as_of=as_of,
        provider=market.name,
        unavailable=_unique(unavailable),
        evidence=evidence,
    )


def _index_overview(index: MarketIndex, fallback_name: str) -> IndexOverview:
    return IndexOverview(
        symbol=index.symbol,
        name=index.name or fallback_name,
        value=index.value,
        change=index.change,
        change_percent=index.change_percent,
        timestamp=index.timestamp,
        currency=index.currency,
        exchange=index.exchange,
    )


def _session_from_info(info: MarketInfo | None) -> MarketSession:
    if info is None:
        return "unknown"
    raw = info.session or (info.extra.get("session") if info.extra else None)
    if raw in {"open", "closed", "pre_market", "after_hours"}:
        return raw
    return "unknown"


def _portfolio_overview(portfolio: Portfolio, market: MarketDataProvider) -> PortfolioOverview:
    unavailable: list[str] = []
    unimplemented: list[ProviderNotImplementedError] = []
    quotes: dict[str, MarketQuote] = {}
    for holding in portfolio.holdings:
        quote = _fetch(
            lambda symbol=holding.symbol: market.get_quote(symbol),
            unavailable,
            f"quote:{holding.symbol}",
            unimplemented,
        )
        if quote is not None:
            quotes[holding.symbol] = quote
    currencies = {holding.currency for holding in portfolio.holdings if holding.currency}
    quote_currencies = {quote.currency for quote in quotes.values() if quote.currency}
    mixed_currency = len(currencies | quote_currencies) > 1
    market_values = [_market_value(holding, quotes.get(holding.symbol)) for holding in portfolio.holdings]
    uploaded_weights = [holding.weight for holding in portfolio.holdings]
    cost_values = [holding.cost_value for holding in portfolio.holdings]
    weights, basis = resolve_weight_vector(
        market_values=market_values,
        uploaded_weights=uploaded_weights,
        cost_values=cost_values,
        mixed_currency=mixed_currency,
    )
    total_market_value = _sum_present(market_values) if not mixed_currency else None
    if mixed_currency:
        total_market_value = None
        if "portfolio_value" not in unavailable:
            unavailable.append("portfolio_value")
    elif any(value is None for value in market_values) and "portfolio_value" not in unavailable:
        if total_market_value is None:
            unavailable.append("portfolio_value")
    total_cost = _sum_present(cost_values)
    day_change = _portfolio_day_change(portfolio.holdings, quotes) if not mixed_currency else None
    previous = None
    if total_market_value is not None and day_change is not None:
        previous = total_market_value - day_change
    day_change_percent = (
        (day_change / previous) * 100.0
        if day_change is not None and previous not in {None, 0}
        else None
    )
    allocation = _allocation_rows(portfolio.holdings, weights, market_values)
    largest_weight = largest_share(weights) if weights is not None else None
    largest_symbol = _largest_symbol(portfolio.holdings, weights)
    hhi = herfindahl_hirschman_index(weights) if weights is not None else None
    effective = effective_n(weights) if weights is not None else None
    top3 = top_n_share(weights, 3) if weights is not None else None
    weight_map = {
        holding.symbol: weight
        for holding, weight in zip(portfolio.holdings, weights or [])
    }
    risk = PortfolioRiskOverview(
        concentration=classify_concentration(hhi=hhi, largest=largest_weight),
        diversification=classify_diversification(
            effective_n_value=effective,
            holding_count=len(portfolio.holdings),
        ),
        largest_symbol=largest_symbol,
        largest_weight=largest_weight,
        hhi=hhi,
        effective_n=effective,
        top3_share=top3,
        oversized_symbols=oversized_symbols(weight_map) if weights is not None else [],
        weight_basis=basis,
    )
    currency = _single_currency(currencies | quote_currencies) or portfolio.base_currency
    evidence = _collect_evidence(
        *[
            (quote, "price", quote.value, symbol)
            for symbol, quote in quotes.items()
        ]
    )
    if not quotes and "quotes" not in unavailable:
        unavailable.append("quotes")
    return PortfolioOverview(
        id=portfolio.id,
        name=portfolio.name,
        holding_count=portfolio.holding_count,
        market_value=total_market_value,
        day_change=day_change,
        day_change_percent=day_change_percent,
        cost_value=total_cost,
        currency=currency,
        mixed_currency=mixed_currency,
        allocation=allocation,
        risk=risk,
        imported_at=portfolio.imported_at,
        quoted_holding_count=len(quotes),
        unavailable=_unique(unavailable),
        evidence=evidence,
    )


def _market_value(holding: Holding, quote: MarketQuote | None) -> float | None:
    if quote is None:
        return None
    return holding.quantity * quote.value


def _portfolio_day_change(
    holdings: list[Holding],
    quotes: dict[str, MarketQuote],
) -> float | None:
    total = 0.0
    seen = False
    for holding in holdings:
        quote = quotes.get(holding.symbol)
        if quote is None or quote.change is None:
            continue
        total += holding.quantity * quote.change
        seen = True
    return total if seen else None


def _allocation_rows(
    holdings: list[Holding],
    weights: list[float] | None,
    market_values: list[float | None],
) -> list[AllocationSlice]:
    if weights is None:
        return [
            AllocationSlice(
                symbol=holding.symbol,
                name=holding.name,
                weight=holding.weight,
                market_value=value,
            )
            for holding, value in zip(holdings, market_values)
        ][:MAX_ALLOCATION_ROWS]
    ranked = sorted(
        zip(holdings, weights, market_values),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        AllocationSlice(
            symbol=holding.symbol,
            name=holding.name,
            weight=weight,
            market_value=value,
        )
        for holding, weight, value in ranked[:MAX_ALLOCATION_ROWS]
    ]


def _largest_symbol(holdings: list[Holding], weights: list[float] | None) -> str | None:
    if not holdings or weights is None or len(holdings) != len(weights):
        return None
    holding, _weight = max(zip(holdings, weights), key=lambda item: item[1])
    return holding.symbol


def _single_currency(currencies: set[str | None]) -> str | None:
    present = {item for item in currencies if item}
    if len(present) == 1:
        return next(iter(present))
    return None


def _sum_present(values: list[float | None]) -> float | None:
    if not values or any(value is None for value in values):
        return None
    return sum(values)


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


def _collect_evidence(
    *items: tuple[object | None, str, object | None, str | None],
) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen: set[str] = set()
    for payload, field, value, symbol in items:
        source = getattr(payload, "source", None)
        if payload is None or source is None:
            continue
        item = Evidence(source=source, symbol=symbol, field=field, value=value)
        key = item.model_dump_json()
        if key in seen:
            continue
        seen.add(key)
        evidence.append(item)
    return evidence


def _unique(values: list[str]) -> list[NonEmptyText]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
