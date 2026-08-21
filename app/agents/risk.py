"""Risk Assessment Agent.

Consumes an uploaded portfolio, retrieved market history, deterministic
portfolio-risk calculations, and any relevant market or fundamental evidence
already present on the request. Numerical risk metrics are computed in Python.
The LLM interprets that structured evidence and must not supply missing figures.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TypeVar

from pydantic import AwareDatetime, Field, ValidationError

from app.agents.base import Agent, AgentMetadata, AgentRuntime
from app.agents.contracts import AgentAnalysis, AgentInput
from app.exceptions import AgentError, ProviderError
from app.models.common import DataSourceMetadata, DomainModel, Evidence
from app.models.fundamentals import CompanyProfile
from app.models.market import MarketIndex, MarketQuote, OhlcSeries
from app.models.portfolio import Holding, Portfolio
from app.models.types import NonEmptyText, Symbol, UnitInterval, normalize_period, normalize_symbol
from app.providers.contracts import FundamentalDataProvider, MarketDataProvider
from app.tools.market import realized_volatility, sorted_bars
from app.tools.risk import (
    DEFAULT_LARGE_POSITION_THRESHOLD,
    DEFAULT_MIN_RETURNS,
    DEFAULT_PERIODS_PER_YEAR,
    DEFAULT_TOP_N,
    UNCLASSIFIED_SECTOR,
    ConcentrationLabel,
    DiversificationLabel,
    WeightBasis,
    aligned_portfolio_values,
    aligned_return_pair,
    beta,
    classify_concentration,
    classify_diversification,
    close_map,
    diversification_ratio,
    effective_n,
    equal_weight,
    herfindahl_hirschman_index,
    largest_share,
    max_drawdown,
    mean_pairwise_correlation,
    oversized_symbols,
    pairwise_correlation,
    pearson_correlation,
    relative_volatility,
    resolve_weight_vector,
    sector_weights,
    series_drawdown,
    series_volatility,
    top_n_share,
    tracking_error,
    weighted_average,
)

UTC = timezone.utc
T = TypeVar("T")

PRIOR_MARKET_KEY = "market-analysis"
PRIOR_FUNDAMENTAL_KEY = "fundamental-analysis"

SYSTEM_PROMPT = (
    "You are a portfolio-risk interpreter. You receive structured evidence "
    "already calculated from an uploaded portfolio, retrieved market history, "
    "and optional market or fundamental specialist output. Interpret only that "
    "evidence. Do not invent weights, volatilities, drawdowns, correlations, "
    "betas, sector exposures, prices, or other figures. "
    "If a field is null or listed as unavailable, treat it as missing and say so. "
    "weight_basis tells you whether weights come from market values, uploaded "
    "weights, or cost basis; do not describe cost or uploaded weights as live "
    "market values. Do not use outside knowledge of current market prices."
)


class PositionRiskMetrics(DomainModel):
    """Per-holding figures derived in Python. Null means missing."""

    symbol: Symbol
    quantity: float
    price: float | None = None
    market_value: float | None = None
    weight: float | None = None
    uploaded_weight: float | None = None
    cost_value: float | None = None
    sector: str | None = None
    currency: str | None = None
    volatility: float | None = None
    max_drawdown: float | None = None
    beta: float | None = None
    benchmark_correlation: float | None = None
    bar_count: int | None = None
    history_start: AwareDatetime | None = None
    history_end: AwareDatetime | None = None
    oversized: bool | None = None
    weight_vs_equal: float | None = None


class PairwiseCorrelation(DomainModel):
    """Return correlation for one symbol pair. Null correlation is not estimated."""

    left: Symbol
    right: Symbol
    correlation: float | None = None
    overlapping_returns: int | None = None


class RiskMetrics(DomainModel):
    """Deterministic portfolio-risk figures. Null means missing."""

    weight_basis: WeightBasis
    holding_count: int
    total_market_value: float | None = None
    largest_weight: float | None = None
    largest_symbol: Symbol | None = None
    top_n: int
    top_n_weight: float | None = None
    hhi: float | None = None
    effective_n: float | None = None
    concentration: ConcentrationLabel
    sector_hhi: float | None = None
    largest_sector: str | None = None
    largest_sector_weight: float | None = None
    sector_concentration: ConcentrationLabel
    unclassified_sector_weight: float | None = None
    sector_weights: dict[str, float] = Field(default_factory=dict)
    portfolio_volatility: float | None = None
    weighted_average_volatility: float | None = None
    max_drawdown: float | None = None
    average_pairwise_correlation: float | None = None
    diversification_ratio: float | None = None
    diversification: DiversificationLabel
    equal_weight: float | None = None
    large_position_threshold: float
    oversized_symbols: list[Symbol] = Field(default_factory=list)
    beta: float | None = None
    benchmark_correlation: float | None = None
    tracking_error: float | None = None
    benchmark_volatility: float | None = None
    relative_volatility: float | None = None
    index_symbol: str | None = None
    history_bar_count: int | None = None
    history_start: AwareDatetime | None = None
    history_end: AwareDatetime | None = None
    positions: list[PositionRiskMetrics] = Field(default_factory=list)
    pairwise_correlations: list[PairwiseCorrelation] = Field(default_factory=list)


class ComputedPortfolioRisk(DomainModel):
    """Python result before LLM interpretation."""

    metrics: RiskMetrics
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)
    factual_observations: list[NonEmptyText] = Field(default_factory=list)
    as_of: AwareDatetime | None = None
    sources: list[DataSourceMetadata] = Field(default_factory=list)


class RiskInterpretation(DomainModel):
    """LLM reading of structured evidence. Must not introduce new figures."""

    overall_risk_assessment: NonEmptyText
    major_risks: list[NonEmptyText] = Field(default_factory=list)
    concentration_findings: list[NonEmptyText] = Field(default_factory=list)
    diversification_findings: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)
    confidence: UnitInterval


class RiskAgentExtras(DomainModel):
    """Structured payload stored on `AgentOutput.extras`."""

    overall_risk_assessment: NonEmptyText
    major_risks: list[NonEmptyText] = Field(default_factory=list)
    concentration_findings: list[NonEmptyText] = Field(default_factory=list)
    diversification_findings: list[NonEmptyText] = Field(default_factory=list)
    risk_metrics: RiskMetrics
    limitations: list[NonEmptyText] = Field(default_factory=list)
    as_of: AwareDatetime | None = None
    analyzed_at: AwareDatetime
    sources: list[DataSourceMetadata] = Field(default_factory=list)
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    market_data_provider: NonEmptyText
    fundamental_data_provider: NonEmptyText
    weight_basis: WeightBasis
    interval: NonEmptyText
    portfolio_id: str | None = None
    prior_agent_artifacts: list[NonEmptyText] = Field(default_factory=list)


@dataclass
class _Windows:
    min_returns: int = DEFAULT_MIN_RETURNS
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR
    large_position_threshold: float = DEFAULT_LARGE_POSITION_THRESHOLD
    top_n: int = DEFAULT_TOP_N


@dataclass
class _HoldingSnapshot:
    holding: Holding
    quote: MarketQuote | None = None
    history: OhlcSeries | None = None
    profile: CompanyProfile | None = None
    sector: str | None = None
    unavailable: list[str] = field(default_factory=list)


@dataclass
class _PortfolioSnapshot:
    portfolio: Portfolio
    holdings: list[_HoldingSnapshot]
    index: MarketIndex | None = None
    index_history: OhlcSeries | None = None
    unavailable: list[str] = field(default_factory=list)


class RiskAssessmentAgent(Agent):
    """Specialist that scores portfolio risk from uploaded holdings and market history."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="risk-assessment",
            role="risk-analyst",
            description=(
                "Analyzes concentration, sector exposure, volatility, drawdown, "
                "correlation, diversification, position sizing, and market-related "
                "risk using uploaded portfolio data, retrieved market history, and "
                "deterministic Python calculations."
            ),
        )

    def analyze(self, payload: AgentInput, runtime: AgentRuntime) -> AgentAnalysis:
        portfolio = _portfolio_from_extras(payload.extras)
        windows = _windows_from_extras(payload.extras)
        interval = _interval_from_extras(payload.extras)
        index_symbol = _index_symbol_from_extras(payload.extras)
        start, end = _history_bounds(payload.extras)
        prior_evidence = _prior_evidence_from_extras(payload.extras)

        snapshot = _load_portfolio(
            runtime.providers.market_data,
            runtime.providers.fundamentals,
            portfolio,
            start=start,
            end=end,
            interval=interval,
            index_symbol=index_symbol,
            prior_evidence=prior_evidence,
        )
        computed = _compute_portfolio_risk(snapshot, windows)
        _record_evidence(runtime, computed, snapshot)

        interpretation = runtime.complete_structured(
            _interpretation_prompt(payload, computed, prior_evidence),
            RiskInterpretation,
            system=SYSTEM_PROMPT,
            metadata={"task": "risk-interpretation"},
        )
        extras_model = _build_extras(
            interpretation,
            computed,
            snapshot,
            provider_name=runtime.providers.market_data.name,
            fundamental_provider_name=runtime.providers.fundamentals.name,
            interval=interval,
            prior_artifacts=list(prior_evidence),
        )
        return AgentAnalysis(
            summary=extras_model.overall_risk_assessment,
            findings=_findings(extras_model),
            evidence=runtime.evidence.items(),
            confidence=_capped_confidence(
                interpretation.confidence,
                extras_model.unavailable,
                extras_model.weight_basis,
            ),
            extras=extras_model.model_dump(mode="json"),
        )


def _portfolio_from_extras(extras: dict[str, Any]) -> Portfolio:
    raw = extras.get("portfolio")
    if raw is None:
        raise AgentError("Risk assessment requires uploaded portfolio data.")
    if isinstance(raw, Portfolio):
        return raw
    if isinstance(raw, dict):
        try:
            return Portfolio.model_validate(_portable_portfolio_payload(raw))
        except ValidationError as exc:
            raise AgentError("portfolio extras must be a confirmed Portfolio payload.") from exc
    raise AgentError("portfolio extras must be a confirmed Portfolio payload.")


def _portable_portfolio_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Drop computed dump fields so a persisted Portfolio JSON can be reloaded."""
    payload = dict(raw)
    payload.pop("holding_count", None)
    holdings = payload.get("holdings")
    if isinstance(holdings, list):
        cleaned: list[Any] = []
        for item in holdings:
            if isinstance(item, dict):
                holding = dict(item)
                holding.pop("cost_value", None)
                cleaned.append(holding)
            else:
                cleaned.append(item)
        payload["holdings"] = cleaned
    return payload


def _windows_from_extras(extras: dict[str, Any]) -> _Windows:
    windows = _Windows(
        min_returns=_positive_int(extras, "min_volatility_returns", DEFAULT_MIN_RETURNS),
        periods_per_year=_positive_int(extras, "periods_per_year", DEFAULT_PERIODS_PER_YEAR),
        large_position_threshold=_unit_interval(
            extras, "large_position_threshold", DEFAULT_LARGE_POSITION_THRESHOLD
        ),
        top_n=_positive_int(extras, "top_n", DEFAULT_TOP_N),
    )
    if windows.min_returns < 2:
        raise AgentError("min_volatility_returns must be at least 2.")
    return windows


def _positive_int(extras: dict[str, Any], key: str, default: int) -> int:
    if key not in extras or extras[key] is None:
        return default
    try:
        value = int(extras[key])
    except (TypeError, ValueError) as exc:
        raise AgentError(f"{key} must be a positive integer.") from exc
    if value < 1:
        raise AgentError(f"{key} must be a positive integer.")
    return value


def _unit_interval(extras: dict[str, Any], key: str, default: float) -> float:
    if key not in extras or extras[key] is None:
        return default
    try:
        value = float(extras[key])
    except (TypeError, ValueError) as exc:
        raise AgentError(f"{key} must be a number between 0 and 1.") from exc
    if not 0 < value <= 1:
        raise AgentError(f"{key} must be a number between 0 and 1.")
    return value


def _interval_from_extras(extras: dict[str, Any]) -> str:
    raw = extras.get("interval", "1d")
    if not isinstance(raw, str) or not raw.strip():
        raise AgentError("interval must be a non-empty period token.")
    try:
        return normalize_period(raw)
    except ValueError as exc:
        raise AgentError("interval must be a non-empty period token.") from exc


def _index_symbol_from_extras(extras: dict[str, Any]) -> str | None:
    for key in ("index_symbol", "benchmark_symbol"):
        raw = extras.get(key)
        if raw is None or raw == "":
            continue
        if not isinstance(raw, str):
            raise AgentError(f"{key} must be a symbol string.")
        try:
            return normalize_symbol(raw)
        except ValueError as exc:
            raise AgentError(f"{key} must be a ticker or index code.") from exc
    return None


def _history_bounds(extras: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    return _optional_datetime(extras, "start"), _optional_datetime(extras, "end")


def _optional_datetime(extras: dict[str, Any], key: str) -> datetime | None:
    raw = extras.get(key)
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            raise AgentError(f"{key} must be timezone-aware.")
        return raw
    raise AgentError(f"{key} must be a timezone-aware datetime.")


def _prior_evidence_from_extras(extras: dict[str, Any]) -> dict[str, Any]:
    prior: dict[str, Any] = {}
    for key in (PRIOR_MARKET_KEY, PRIOR_FUNDAMENTAL_KEY):
        artifact = extras.get(key)
        if isinstance(artifact, dict) and artifact:
            prior[key] = _summarize_prior_artifact(artifact)
    return prior


def _summarize_prior_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    extras = artifact.get("extras") if isinstance(artifact.get("extras"), dict) else {}
    keep = (
        "market_assessment",
        "trend",
        "risks",
        "key_observations",
        "supporting_metrics",
        "fundamental_assessment",
        "strengths",
        "weaknesses",
        "financial_risks",
        "unavailable",
        "analyses",
    )
    trimmed_extras = {key: extras[key] for key in keep if key in extras}
    return {
        "summary": artifact.get("summary"),
        "findings": artifact.get("findings"),
        "status": artifact.get("status"),
        "extras": trimmed_extras,
    }


def _sector_from_prior(prior_evidence: Mapping[str, Any], symbol: str) -> str | None:
    artifact = prior_evidence.get(PRIOR_FUNDAMENTAL_KEY)
    if not isinstance(artifact, dict):
        return None
    extras = artifact.get("extras")
    if not isinstance(extras, dict):
        return None
    analyses = extras.get("analyses")
    if isinstance(analyses, list):
        for item in analyses:
            if not isinstance(item, dict):
                continue
            metrics = item.get("supporting_metrics")
            if not isinstance(metrics, dict):
                continue
            if str(metrics.get("symbol", "")).upper() == symbol:
                sector = metrics.get("sector")
                if isinstance(sector, str) and sector.strip():
                    return sector.strip()
    metrics = extras.get("supporting_metrics")
    if isinstance(metrics, dict) and str(metrics.get("symbol", "")).upper() == symbol:
        sector = metrics.get("sector")
        if isinstance(sector, str) and sector.strip():
            return sector.strip()
    return None


def _load_portfolio(
    market: MarketDataProvider,
    fundamentals: FundamentalDataProvider,
    portfolio: Portfolio,
    *,
    start: datetime | None,
    end: datetime | None,
    interval: str,
    index_symbol: str | None,
    prior_evidence: Mapping[str, Any],
) -> _PortfolioSnapshot:
    unavailable: list[str] = []
    index, index_history, index_unavailable = _load_index_context(
        market, index_symbol, start=start, end=end, interval=interval
    )
    unavailable.extend(index_unavailable)

    holdings: list[_HoldingSnapshot] = []
    for holding in portfolio.holdings:
        snapshot = _load_holding(
            market,
            fundamentals,
            holding,
            start=start,
            end=end,
            interval=interval,
            prior_evidence=prior_evidence,
        )
        holdings.append(snapshot)
    return _PortfolioSnapshot(
        portfolio=portfolio,
        holdings=holdings,
        index=index,
        index_history=index_history,
        unavailable=_unique(unavailable),
    )


def _load_index_context(
    market: MarketDataProvider,
    index_symbol: str | None,
    *,
    start: datetime | None,
    end: datetime | None,
    interval: str,
) -> tuple[MarketIndex | None, OhlcSeries | None, list[str]]:
    unavailable: list[str] = []
    if index_symbol is None:
        return None, None, ["market_index", "beta", "tracking_error", "relative_volatility"]

    index = _fetch(lambda: market.get_index(index_symbol), unavailable, "market_index")
    index_history = _fetch(
        lambda: market.get_historical_ohlc(
            index_symbol, start=start, end=end, interval=interval
        ),
        unavailable,
        "index_history",
    )
    if index_history is not None and not index_history.prices:
        unavailable.append("index_history")
        index_history = None
    if "index_history" in unavailable:
        unavailable.extend(["beta", "tracking_error", "relative_volatility"])
    return index, index_history, _unique(unavailable)


def _load_holding(
    market: MarketDataProvider,
    fundamentals: FundamentalDataProvider,
    holding: Holding,
    *,
    start: datetime | None,
    end: datetime | None,
    interval: str,
    prior_evidence: Mapping[str, Any],
) -> _HoldingSnapshot:
    unavailable: list[str] = []
    quote = _fetch(lambda: market.get_quote(holding.symbol), unavailable, "current_price")
    history = _fetch(
        lambda: market.get_historical_ohlc(
            holding.symbol, start=start, end=end, interval=interval
        ),
        unavailable,
        "historical_ohlc",
    )
    if history is not None and not history.prices:
        unavailable.append("historical_ohlc")
        history = None
    profile = _fetch(
        lambda: fundamentals.get_company_profile(holding.symbol),
        unavailable,
        "company_profile",
    )
    sector = profile.sector if profile is not None else None
    if sector is None:
        sector = _sector_from_prior(prior_evidence, holding.symbol)
        if sector is None:
            unavailable.append("sector")
    return _HoldingSnapshot(
        holding=holding,
        quote=quote,
        history=history,
        profile=profile,
        sector=sector,
        unavailable=_unique(unavailable),
    )


def _fetch(operation: Callable[[], T], unavailable: list[str], label: str) -> T | None:
    try:
        return operation()
    except ProviderError:
        unavailable.append(label)
        return None


def _compute_portfolio_risk(snapshot: _PortfolioSnapshot, windows: _Windows) -> ComputedPortfolioRisk:
    unavailable = list(snapshot.unavailable)
    holdings = snapshot.holdings
    symbols = [item.holding.symbol for item in holdings]
    quantities = {item.holding.symbol: item.holding.quantity for item in holdings}

    prices: list[float | None] = []
    market_values: list[float | None] = []
    uploaded_weights: list[float | None] = []
    cost_values: list[float | None] = []
    sectors: list[str | None] = []
    closes_by_symbol: dict[str, dict[datetime, float]] = {}

    for item in holdings:
        quote_price = item.quote.value if item.quote is not None else None
        prices.append(quote_price)
        market_values.append(
            item.holding.quantity * quote_price if quote_price is not None else None
        )
        uploaded_weights.append(item.holding.weight)
        cost_values.append(item.holding.cost_value)
        sectors.append(item.sector)
        closes = close_map(item.history)
        if closes:
            closes_by_symbol[item.holding.symbol] = closes
        else:
            unavailable.append(f"historical_ohlc:{item.holding.symbol}")

    mixed_currency = _mixed_currency(holdings)
    if mixed_currency:
        unavailable.append("fx_conversion")

    weights, basis = resolve_weight_vector(
        market_values=market_values,
        uploaded_weights=uploaded_weights,
        cost_values=cost_values,
        mixed_currency=mixed_currency,
    )
    if weights is None:
        unavailable.extend(["weights", "concentration", "diversification", "position_sizing"])
    elif basis != "market_value":
        unavailable.append("market_value_weights")

    total_market_value = None if mixed_currency else _sum_if_complete(market_values)
    if total_market_value is None and not mixed_currency:
        unavailable.append("total_market_value")

    hhi = herfindahl_hirschman_index(weights) if weights is not None else None
    effective = effective_n(weights) if weights is not None else None
    largest = largest_share(weights) if weights is not None else None
    top_n_weight = top_n_share(weights, windows.top_n) if weights is not None else None
    concentration = classify_concentration(
        hhi=hhi,
        largest=largest,
        large_position_threshold=windows.large_position_threshold,
    )
    equal = equal_weight(len(holdings))
    weights_by_symbol = (
        {symbol: weight for symbol, weight in zip(symbols, weights)} if weights is not None else {}
    )
    oversized = oversized_symbols(
        weights_by_symbol, threshold=windows.large_position_threshold
    )
    largest_symbol = None
    if weights is not None and largest is not None:
        for symbol, weight in zip(symbols, weights):
            if weight == largest:
                largest_symbol = symbol
                break

    grouped_sectors = sector_weights(weights, sectors) if weights is not None else None
    sector_hhi_value = (
        herfindahl_hirschman_index(list(grouped_sectors.values()))
        if grouped_sectors
        else None
    )
    largest_sector = None
    largest_sector_weight = None
    if grouped_sectors:
        largest_sector = max(grouped_sectors, key=grouped_sectors.get)
        largest_sector_weight = grouped_sectors[largest_sector]
    sector_concentration = classify_concentration(
        hhi=sector_hhi_value,
        largest=largest_sector_weight,
        large_position_threshold=windows.large_position_threshold,
    )
    unclassified_weight = grouped_sectors.get(UNCLASSIFIED_SECTOR) if grouped_sectors else None
    if grouped_sectors is None:
        unavailable.append("sector_risk")
    elif unclassified_weight:
        unavailable.append("complete_sector_map")

    index_closes = close_map(snapshot.index_history)
    value_series = aligned_portfolio_values(quantities, closes_by_symbol)
    portfolio_values = value_series[1] if value_series is not None else None
    history_start = value_series[0][0] if value_series is not None else None
    history_end = value_series[0][-1] if value_series is not None else None
    history_bar_count = len(portfolio_values) if portfolio_values is not None else None

    missing_history = [symbol for symbol in symbols if symbol not in closes_by_symbol]
    if missing_history:
        unavailable.append("complete_price_history")
    if portfolio_values is None:
        unavailable.extend(["volatility", "drawdown"])
    elif history_bar_count is not None and history_bar_count - 1 < windows.min_returns:
        unavailable.append("volatility")

    portfolio_vol = (
        realized_volatility(
            portfolio_values,
            periods_per_year=windows.periods_per_year,
            min_returns=windows.min_returns,
        )
        if portfolio_values is not None
        else None
    )
    drawdown = max_drawdown(portfolio_values) if portfolio_values is not None else None
    average_corr = mean_pairwise_correlation(
        closes_by_symbol, min_returns=windows.min_returns
    )
    _mark_missing(unavailable, "correlation", average_corr, len(holdings) > 1)

    pairwise = _pairwise_rows(closes_by_symbol, windows.min_returns)
    position_vols = [
        series_volatility(
            closes_by_symbol.get(item.holding.symbol, {}),
            periods_per_year=windows.periods_per_year,
            min_returns=windows.min_returns,
        )
        for item in holdings
    ]
    weighted_vol = (
        weighted_average(position_vols, weights) if weights is not None else None
    )
    div_ratio = diversification_ratio(weighted_vol, portfolio_vol)
    diversification = classify_diversification(
        effective_n_value=effective,
        holding_count=len(holdings),
        average_correlation=average_corr,
    )

    portfolio_closes = (
        {timestamp: value for timestamp, value in zip(value_series[0], value_series[1])}
        if value_series is not None
        else {}
    )
    aligned_returns = (
        aligned_return_pair(portfolio_closes, index_closes)
        if portfolio_closes and index_closes
        else None
    )
    port_beta = (
        beta(
            aligned_returns[0],
            aligned_returns[1],
            min_returns=windows.min_returns,
        )
        if aligned_returns is not None
        else None
    )
    port_bench_corr = (
        pearson_correlation(
            aligned_returns[0],
            aligned_returns[1],
            min_observations=windows.min_returns,
        )
        if aligned_returns is not None
        else None
    )
    active_error = (
        tracking_error(
            aligned_returns[0],
            aligned_returns[1],
            periods_per_year=windows.periods_per_year,
            min_returns=windows.min_returns,
        )
        if aligned_returns is not None
        else None
    )
    bench_vol = (
        series_volatility(
            index_closes,
            periods_per_year=windows.periods_per_year,
            min_returns=windows.min_returns,
        )
        if index_closes
        else None
    )
    rel_vol = relative_volatility(portfolio_vol, bench_vol)
    _mark_missing(unavailable, "beta", port_beta, snapshot.index_history is not None)
    _mark_missing(
        unavailable,
        "benchmark_correlation",
        port_bench_corr,
        snapshot.index_history is not None,
    )
    _mark_missing(
        unavailable, "tracking_error", active_error, snapshot.index_history is not None
    )
    _mark_missing(
        unavailable, "relative_volatility", rel_vol, snapshot.index_history is not None
    )
    _mark_missing(unavailable, "volatility", portfolio_vol, portfolio_values is not None)
    _mark_missing(unavailable, "drawdown", drawdown, portfolio_values is not None)

    positions = [
        _position_metrics(
            item,
            weight=weights[index] if weights is not None else None,
            market_value=market_values[index],
            price=prices[index],
            volatility=position_vols[index],
            equal=equal,
            threshold=windows.large_position_threshold,
            min_returns=windows.min_returns,
            index_closes=index_closes,
        )
        for index, item in enumerate(holdings)
    ]

    metrics = RiskMetrics(
        weight_basis=basis,
        holding_count=len(holdings),
        total_market_value=total_market_value,
        largest_weight=largest,
        largest_symbol=largest_symbol,
        top_n=windows.top_n,
        top_n_weight=top_n_weight,
        hhi=hhi,
        effective_n=effective,
        concentration=concentration,
        sector_hhi=sector_hhi_value,
        largest_sector=largest_sector,
        largest_sector_weight=largest_sector_weight,
        sector_concentration=sector_concentration,
        unclassified_sector_weight=unclassified_weight,
        sector_weights=grouped_sectors or {},
        portfolio_volatility=portfolio_vol,
        weighted_average_volatility=weighted_vol,
        max_drawdown=drawdown,
        average_pairwise_correlation=average_corr,
        diversification_ratio=div_ratio,
        diversification=diversification,
        equal_weight=equal,
        large_position_threshold=windows.large_position_threshold,
        oversized_symbols=oversized,
        beta=port_beta,
        benchmark_correlation=port_bench_corr,
        tracking_error=active_error,
        benchmark_volatility=bench_vol,
        relative_volatility=rel_vol,
        index_symbol=snapshot.index.symbol if snapshot.index is not None else None,
        history_bar_count=history_bar_count,
        history_start=history_start,
        history_end=history_end,
        positions=positions,
        pairwise_correlations=pairwise,
    )
    unavailable = _unique([*unavailable, *[label for item in holdings for label in item.unavailable]])
    limitations = _limitations(metrics, unavailable, mixed_currency, missing_history)
    sources = _sources(snapshot)
    return ComputedPortfolioRisk(
        metrics=metrics,
        unavailable=unavailable,
        limitations=limitations,
        factual_observations=_factual_observations(metrics, unavailable),
        as_of=_as_of(snapshot, history_end),
        sources=sources,
    )


def _position_metrics(
    item: _HoldingSnapshot,
    *,
    weight: float | None,
    market_value: float | None,
    price: float | None,
    volatility: float | None,
    equal: float | None,
    threshold: float,
    min_returns: int,
    index_closes: Mapping[datetime, float],
) -> PositionRiskMetrics:
    closes = close_map(item.history)
    timestamps = sorted(closes)
    aligned = aligned_return_pair(closes, index_closes) if closes and index_closes else None
    position_beta = (
        beta(aligned[0], aligned[1], min_returns=min_returns) if aligned is not None else None
    )
    position_bench_corr = (
        pearson_correlation(aligned[0], aligned[1], min_observations=min_returns)
        if aligned is not None
        else None
    )
    weight_vs_equal = None
    if weight is not None and equal not in (None, 0):
        weight_vs_equal = weight / equal
    oversized = None if weight is None else weight >= threshold
    return PositionRiskMetrics(
        symbol=item.holding.symbol,
        quantity=item.holding.quantity,
        price=price,
        market_value=market_value,
        weight=weight,
        uploaded_weight=item.holding.weight,
        cost_value=item.holding.cost_value,
        sector=item.sector,
        currency=_holding_currency(item),
        volatility=volatility,
        max_drawdown=series_drawdown(closes),
        beta=position_beta,
        benchmark_correlation=position_bench_corr,
        bar_count=len(timestamps) if timestamps else None,
        history_start=timestamps[0] if timestamps else None,
        history_end=timestamps[-1] if timestamps else None,
        oversized=oversized,
        weight_vs_equal=weight_vs_equal,
    )


def _pairwise_rows(
    closes_by_symbol: Mapping[str, Mapping[datetime, float]],
    min_returns: int,
) -> list[PairwiseCorrelation]:
    symbols = sorted(symbol for symbol, series in closes_by_symbol.items() if series)
    rows: list[PairwiseCorrelation] = []
    for index, left in enumerate(symbols):
        for right in symbols[index + 1 :]:
            corr, overlap = pairwise_correlation(
                closes_by_symbol[left], closes_by_symbol[right], min_returns=min_returns
            )
            rows.append(
                PairwiseCorrelation(
                    left=left,
                    right=right,
                    correlation=corr,
                    overlapping_returns=overlap or None,
                )
            )
    return rows


def _holding_currency(item: _HoldingSnapshot) -> str | None:
    return _first_present(
        item.quote.currency if item.quote is not None else None,
        item.holding.currency,
        item.profile.currency if item.profile is not None else None,
    )


def _declared_currencies(item: _HoldingSnapshot) -> set[str]:
    values = [
        item.holding.currency,
        item.quote.currency if item.quote is not None else None,
        item.profile.currency if item.profile is not None else None,
    ]
    return {value for value in values if value}


def _mixed_currency(holdings: Sequence[_HoldingSnapshot]) -> bool:
    combined: set[str] = set()
    for item in holdings:
        combined |= _declared_currencies(item)
    return len(combined) > 1


def _sum_if_complete(values: Sequence[float | None]) -> float | None:
    if not values or any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _mark_missing(unavailable: list[str], label: str, value: Any, relevant: bool) -> None:
    if relevant and value is None and label not in unavailable:
        unavailable.append(label)


def _first_present(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _as_of(snapshot: _PortfolioSnapshot, history_end: datetime | None) -> datetime | None:
    timestamps: list[datetime] = []
    if history_end is not None:
        timestamps.append(history_end)
    if snapshot.index is not None:
        timestamps.append(snapshot.index.timestamp)
    for item in snapshot.holdings:
        if item.quote is not None:
            timestamps.append(item.quote.timestamp)
        bars = sorted_bars(item.history)
        if bars:
            timestamps.append(bars[-1].timestamp)
        if item.profile is not None and item.profile.timestamp is not None:
            timestamps.append(item.profile.timestamp)
    return max(timestamps) if timestamps else None


def _sources(snapshot: _PortfolioSnapshot) -> list[DataSourceMetadata]:
    payloads: list[Any] = [snapshot.index, snapshot.index_history]
    for item in snapshot.holdings:
        payloads.extend([item.quote, item.history, item.profile])
    sources: list[DataSourceMetadata] = []
    seen: set[str] = set()
    for payload in payloads:
        if payload is None:
            continue
        source = payload.source
        key = source.model_dump_json()
        if key not in seen:
            seen.add(key)
            sources.append(source)
    return sources


def _factual_observations(metrics: RiskMetrics, unavailable: list[str]) -> list[str]:
    observations: list[str] = []
    observations.append(
        f"Portfolio has {metrics.holding_count} holdings. Weight basis is {metrics.weight_basis}."
    )
    if metrics.total_market_value is not None:
        observations.append(f"Total market value is {metrics.total_market_value}.")
    if metrics.largest_weight is not None and metrics.largest_symbol:
        observations.append(
            f"Largest position is {metrics.largest_symbol} at weight {metrics.largest_weight}."
        )
    if metrics.hhi is not None:
        observations.append(f"Concentration HHI is {metrics.hhi}.")
    if metrics.effective_n is not None:
        observations.append(f"Effective number of holdings is {metrics.effective_n}.")
    observations.append(f"Concentration is {metrics.concentration}.")
    if metrics.largest_sector and metrics.largest_sector_weight is not None:
        observations.append(
            f"Largest sector is {metrics.largest_sector} at weight {metrics.largest_sector_weight}."
        )
    if metrics.sector_hhi is not None:
        observations.append(f"Sector HHI is {metrics.sector_hhi}.")
    observations.append(f"Sector concentration is {metrics.sector_concentration}.")
    if metrics.portfolio_volatility is not None:
        observations.append(f"Portfolio annualized volatility is {metrics.portfolio_volatility}.")
    if metrics.max_drawdown is not None:
        observations.append(f"Portfolio max drawdown is {metrics.max_drawdown}.")
    if metrics.average_pairwise_correlation is not None:
        observations.append(
            f"Average pairwise return correlation is {metrics.average_pairwise_correlation}."
        )
    observations.append(f"Diversification is {metrics.diversification}.")
    if metrics.oversized_symbols:
        observations.append(
            "Oversized positions relative to the size threshold: "
            + ", ".join(metrics.oversized_symbols)
            + "."
        )
    if metrics.beta is not None:
        observations.append(f"Portfolio beta versus the benchmark is {metrics.beta}.")
    if metrics.benchmark_correlation is not None:
        observations.append(f"Portfolio correlation versus the benchmark is {metrics.benchmark_correlation}.")
    if metrics.tracking_error is not None:
        observations.append(f"Tracking error versus the benchmark is {metrics.tracking_error}.")
    if metrics.relative_volatility is not None:
        observations.append(
            f"Portfolio volatility relative to the benchmark is {metrics.relative_volatility}."
        )
    if unavailable:
        observations.append("Unavailable and not estimated: " + ", ".join(unavailable) + ".")
    return observations


def _limitations(
    metrics: RiskMetrics,
    unavailable: Sequence[str],
    mixed_currency: bool,
    missing_history: Sequence[str],
) -> list[str]:
    notes: list[str] = []
    if metrics.weight_basis == "insufficient_data":
        notes.append("Position weights could not be formed from market values, uploaded weights, or cost basis.")
    elif metrics.weight_basis == "uploaded_weight":
        notes.append("Concentration uses uploaded weights, not live market values.")
    elif metrics.weight_basis == "cost_value":
        notes.append("Concentration uses cost basis, not live market values.")
    if mixed_currency:
        notes.append("Holdings use more than one currency; market values were not combined without FX conversion.")
    if missing_history:
        notes.append(
            "Historical series missing for "
            + ", ".join(missing_history)
            + "; those names were excluded from time-series risk."
        )
    if metrics.history_bar_count is not None and metrics.portfolio_volatility is None:
        notes.append("Historical window is too short to compute portfolio volatility.")
    if metrics.max_drawdown is None:
        notes.append("Max drawdown was not computed because a complete positive value series was unavailable.")
    if metrics.holding_count > 1 and metrics.average_pairwise_correlation is None:
        notes.append("Pairwise correlations were not computed because overlapping returns were insufficient.")
    if metrics.beta is None:
        notes.append("Market beta was not computed because aligned benchmark history was insufficient.")
    if UNCLASSIFIED_SECTOR in metrics.sector_weights:
        notes.append("One or more holdings have no sector classification.")
    if "volatility" in unavailable or "drawdown" in unavailable or "correlation" in unavailable:
        notes.append("Insufficient historical data was left missing rather than estimated.")
    return notes


def _record_evidence(
    runtime: AgentRuntime,
    computed: ComputedPortfolioRisk,
    snapshot: _PortfolioSnapshot,
) -> None:
    metrics = computed.metrics
    derived_source = DataSourceMetadata(
        provider=runtime.providers.market_data.name,
        source="derived-risk-metric",
        timestamp=computed.as_of or datetime.now(tz=UTC),
    )
    for item, position in zip(snapshot.holdings, metrics.positions):
        if item.quote is not None:
            runtime.evidence.add(
                Evidence(
                    source=item.quote.source,
                    symbol=position.symbol,
                    field="price",
                    value=item.quote.value,
                )
            )
        if position.weight is not None:
            runtime.evidence.add(
                Evidence(
                    source=derived_source,
                    symbol=position.symbol,
                    field="weight",
                    value=position.weight,
                )
            )
        if position.volatility is not None:
            runtime.evidence.add(
                Evidence(
                    source=derived_source,
                    symbol=position.symbol,
                    field="volatility",
                    value=position.volatility,
                )
            )
        if item.history is not None and position.history_end is not None:
            runtime.evidence.add(
                Evidence(
                    source=item.history.source,
                    symbol=position.symbol,
                    period=item.history.period,
                    field="historical_close",
                    value=close_map(item.history)[position.history_end],
                )
            )
    if snapshot.index is not None:
        runtime.evidence.add(
            Evidence(
                source=snapshot.index.source,
                symbol=snapshot.index.symbol,
                field="index_level",
                value=snapshot.index.value,
            )
        )
    derived = (
        ("hhi", metrics.hhi),
        ("effective_n", metrics.effective_n),
        ("largest_weight", metrics.largest_weight),
        ("sector_hhi", metrics.sector_hhi),
        ("portfolio_volatility", metrics.portfolio_volatility),
        ("max_drawdown", metrics.max_drawdown),
        ("average_pairwise_correlation", metrics.average_pairwise_correlation),
        ("diversification_ratio", metrics.diversification_ratio),
        ("beta", metrics.beta),
        ("tracking_error", metrics.tracking_error),
        ("relative_volatility", metrics.relative_volatility),
        ("total_market_value", metrics.total_market_value),
    )
    for field_name, value in derived:
        if value is None:
            continue
        runtime.evidence.add(
            Evidence(
                source=derived_source,
                field=field_name,
                value=value,
            )
        )
    runtime.evidence.add(
        Evidence(
            source=derived_source,
            field="weight_basis",
            value=metrics.weight_basis,
        )
    )
    runtime.evidence.add(
        Evidence(
            source=derived_source,
            field="concentration",
            value=metrics.concentration,
        )
    )
    runtime.evidence.add(
        Evidence(
            source=derived_source,
            field="diversification",
            value=metrics.diversification,
        )
    )


def _build_extras(
    interpretation: RiskInterpretation,
    computed: ComputedPortfolioRisk,
    snapshot: _PortfolioSnapshot,
    *,
    provider_name: str,
    fundamental_provider_name: str,
    interval: str,
    prior_artifacts: Sequence[str],
) -> RiskAgentExtras:
    risks = list(interpretation.major_risks)
    gap_risk = _gap_risk(computed.unavailable)
    if gap_risk and gap_risk not in risks:
        risks.append(gap_risk)
    limitations = _unique([*computed.limitations, *interpretation.limitations])
    return RiskAgentExtras(
        overall_risk_assessment=interpretation.overall_risk_assessment,
        major_risks=risks,
        concentration_findings=list(interpretation.concentration_findings),
        diversification_findings=list(interpretation.diversification_findings),
        risk_metrics=computed.metrics,
        limitations=limitations,
        as_of=computed.as_of,
        analyzed_at=datetime.now(tz=UTC),
        sources=computed.sources,
        unavailable=computed.unavailable,
        market_data_provider=provider_name,
        fundamental_data_provider=fundamental_provider_name,
        weight_basis=computed.metrics.weight_basis,
        interval=interval,
        portfolio_id=snapshot.portfolio.id,
        prior_agent_artifacts=list(prior_artifacts),
    )


def _findings(extras: RiskAgentExtras) -> list[str]:
    findings: list[str] = []
    findings.extend(extras.major_risks)
    findings.extend(extras.concentration_findings)
    findings.extend(extras.diversification_findings)
    return findings


def _interpretation_prompt(
    payload: AgentInput,
    computed: ComputedPortfolioRisk,
    prior_evidence: Mapping[str, Any],
) -> str:
    bundle = {
        "request_id": payload.request_id,
        "question": payload.question,
        "symbols": payload.symbols,
        "computed": computed.model_dump(mode="json"),
        "prior_evidence": prior_evidence,
        "rules": [
            "Numeric values were calculated from the uploaded portfolio and retrieved market data.",
            "Null fields and the unavailable lists are missing. Do not fill them in.",
            "Do not cite weights, volatilities, drawdowns, or dates that are not in this payload.",
            "Treat cost_value and uploaded_weight bases as non-market when weight_basis is not market_value.",
        ],
    }
    return (
        "Interpret the following portfolio-risk evidence and return "
        "overall_risk_assessment, major_risks, concentration_findings, "
        "diversification_findings, limitations, and confidence.\n\n"
        + json.dumps(bundle, indent=2, default=str)
    )


def _gap_risk(unavailable: Sequence[str]) -> str | None:
    if not unavailable:
        return None
    return "Unavailable inputs were not estimated: " + ", ".join(unavailable) + "."


def _capped_confidence(
    confidence: float, unavailable: Sequence[str], weight_basis: WeightBasis
) -> float:
    capped = confidence
    history_gaps = {"volatility", "drawdown", "correlation", "complete_price_history", "historical_ohlc"}
    if history_gaps & set(unavailable) or any(
        item.startswith("historical_ohlc:") for item in unavailable
    ):
        capped = min(capped, 0.5)
    if weight_basis != "market_value":
        capped = min(capped, 0.6)
    if weight_basis == "insufficient_data":
        capped = min(capped, 0.4)
    return capped


def _unique(values: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen
