"""Market Analysis Agent.

Retrieves quotes, history, volume, and index context through the injected
`MarketDataProvider`. Numerical indicators are computed in Python. The LLM
interprets that structured evidence and must not supply missing figures.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, TypeVar

from pydantic import AwareDatetime, Field

from app.agents.base import Agent, AgentMetadata, AgentRuntime
from app.agents.contracts import AgentAnalysis, AgentInput
from app.exceptions import AgentError, ProviderError
from app.models.common import DataSourceMetadata, DomainModel, Evidence
from app.models.market import (
    HistoricalPrice,
    MarketIndex,
    MarketInfo,
    MarketQuote,
    OhlcSeries,
    VolumeSnapshot,
)
from app.models.types import NonEmptyText, Symbol, UnitInterval, normalize_period, normalize_symbol
from app.providers.contracts import MarketDataProvider
from app.tools.market import (
    DEFAULT_LONG_WINDOW,
    DEFAULT_MIN_VOLATILITY_RETURNS,
    DEFAULT_MOMENTUM_LOOKBACK,
    DEFAULT_PERIODS_PER_YEAR,
    DEFAULT_SHORT_WINDOW,
    aligned_closes,
    classify_trend,
    mean,
    price_extremes,
    price_momentum,
    relative_performance,
    realized_volatility,
    simple_moving_average,
    sorted_bars,
    total_return,
    volume_ratio,
)

UTC = timezone.utc
T = TypeVar("T")

TrendDirection = Literal["uptrend", "downtrend", "sideways", "insufficient_data"]
OverallTrend = Literal["uptrend", "downtrend", "sideways", "insufficient_data", "mixed"]

SYSTEM_PROMPT = (
    "You are a market-analysis interpreter. You receive structured evidence "
    "already calculated from retrieved market data. Interpret only that evidence. "
    "Do not invent prices, volumes, timestamps, index levels, or indicator values. "
    "If a field is null or listed as unavailable, treat it as missing and say so. "
    "Do not use outside knowledge of current market prices."
)


class MarketSupportingMetrics(DomainModel):
    """Deterministic figures derived from retrieved market data. Null means missing."""

    symbol: Symbol
    current_price: float | None = None
    currency: str | None = None
    exchange: str | None = None
    change: float | None = None
    change_percent: float | None = None
    quote_timestamp: AwareDatetime | None = None
    historical_start_price: float | None = None
    historical_end_price: float | None = None
    historical_return: float | None = None
    historical_high: float | None = None
    historical_low: float | None = None
    bar_count: int | None = None
    history_start: AwareDatetime | None = None
    history_end: AwareDatetime | None = None
    volume: float | None = None
    average_volume: float | None = None
    volume_ratio: float | None = None
    volume_timestamp: AwareDatetime | None = None
    index_symbol: str | None = None
    index_name: str | None = None
    index_level: float | None = None
    index_change_percent: float | None = None
    index_timestamp: AwareDatetime | None = None
    short_sma: float | None = None
    long_sma: float | None = None
    volatility: float | None = None
    momentum: float | None = None
    relative_performance: float | None = None


class ComputedSymbolAnalysis(DomainModel):
    """Per-symbol Python result before LLM interpretation."""

    symbol: Symbol
    trend: TrendDirection
    supporting_metrics: MarketSupportingMetrics
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    as_of: AwareDatetime | None = None
    sources: list[DataSourceMetadata] = Field(default_factory=list)
    factual_observations: list[NonEmptyText] = Field(default_factory=list)


class MarketInterpretation(DomainModel):
    """LLM reading of structured evidence. Must not introduce new figures."""

    market_assessment: NonEmptyText
    risks: list[NonEmptyText] = Field(default_factory=list)
    key_observations: list[NonEmptyText] = Field(default_factory=list)
    confidence: UnitInterval


class MarketAgentExtras(DomainModel):
    """Structured payload stored on `AgentOutput.extras`."""

    market_assessment: NonEmptyText
    trend: OverallTrend
    supporting_metrics: MarketSupportingMetrics
    risks: list[NonEmptyText] = Field(default_factory=list)
    key_observations: list[NonEmptyText] = Field(default_factory=list)
    as_of: AwareDatetime | None = None
    analyzed_at: AwareDatetime
    sources: list[DataSourceMetadata] = Field(default_factory=list)
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    market_data_provider: NonEmptyText
    interval: NonEmptyText
    analyses: list[ComputedSymbolAnalysis] = Field(default_factory=list)


@dataclass
class _Windows:
    short: int = DEFAULT_SHORT_WINDOW
    long: int = DEFAULT_LONG_WINDOW
    momentum: int = DEFAULT_MOMENTUM_LOOKBACK
    min_volatility_returns: int = DEFAULT_MIN_VOLATILITY_RETURNS
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR


@dataclass
class _InstrumentSnapshot:
    symbol: str
    quote: MarketQuote | None = None
    history: OhlcSeries | None = None
    volume: VolumeSnapshot | None = None
    market_info: MarketInfo | None = None
    index: MarketIndex | None = None
    index_history: OhlcSeries | None = None
    unavailable: list[str] = field(default_factory=list)


class MarketAnalysisAgent(Agent):
    """Specialist that scores price action from an injected market-data provider."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="market-analysis",
            role="market-analyst",
            description=(
                "Analyzes current price, historical movement, volume, index context, "
                "trend, volatility, momentum, and relative performance using retrieved "
                "market data and deterministic Python indicators."
            ),
        )

    def analyze(self, payload: AgentInput, runtime: AgentRuntime) -> AgentAnalysis:
        if not payload.symbols:
            raise AgentError("Market analysis requires at least one symbol.")

        market = runtime.providers.market_data
        windows = _windows_from_extras(payload.extras)
        interval = _interval_from_extras(payload.extras)
        index_symbol = _index_symbol_from_extras(payload.extras)
        start, end = _history_bounds(payload.extras)

        index, index_history, index_unavailable = _load_index_context(
            market,
            index_symbol,
            start=start,
            end=end,
            interval=interval,
        )

        analyses: list[ComputedSymbolAnalysis] = []
        for symbol in payload.symbols:
            snapshot = _load_instrument(
                market,
                symbol,
                start=start,
                end=end,
                interval=interval,
                index=index,
                index_history=index_history,
                index_unavailable=index_unavailable,
            )
            computed = _compute_symbol_analysis(snapshot, windows)
            _record_evidence(runtime, computed, snapshot)
            analyses.append(computed)

        interpretation = runtime.complete_structured(
            _interpretation_prompt(payload, analyses),
            MarketInterpretation,
            system=SYSTEM_PROMPT,
            metadata={"task": "market-interpretation"},
        )
        extras_model = _build_extras(
            interpretation,
            analyses,
            provider_name=market.name,
            interval=interval,
        )
        return AgentAnalysis(
            summary=extras_model.market_assessment,
            findings=list(extras_model.key_observations),
            evidence=runtime.evidence.items(),
            confidence=_capped_confidence(interpretation.confidence, extras_model.unavailable),
            extras=extras_model.model_dump(mode="json"),
        )


def _windows_from_extras(extras: dict[str, Any]) -> _Windows:
    windows = _Windows(
        short=_positive_int(extras, "short_window", DEFAULT_SHORT_WINDOW),
        long=_positive_int(extras, "long_window", DEFAULT_LONG_WINDOW),
        momentum=_positive_int(extras, "momentum_lookback", DEFAULT_MOMENTUM_LOOKBACK),
        min_volatility_returns=_positive_int(
            extras, "min_volatility_returns", DEFAULT_MIN_VOLATILITY_RETURNS
        ),
        periods_per_year=_positive_int(extras, "periods_per_year", DEFAULT_PERIODS_PER_YEAR),
    )
    if windows.long < windows.short:
        raise AgentError("long_window must be greater than or equal to short_window.")
    if windows.min_volatility_returns < 2:
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
        return None, None, ["market_index", "relative_performance"]

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
        unavailable.append("relative_performance")
    return index, index_history, _unique(unavailable)


def _load_instrument(
    market: MarketDataProvider,
    symbol: str,
    *,
    start: datetime | None,
    end: datetime | None,
    interval: str,
    index: MarketIndex | None,
    index_history: OhlcSeries | None,
    index_unavailable: list[str],
) -> _InstrumentSnapshot:
    unavailable = list(index_unavailable)
    quote = _fetch(lambda: market.get_quote(symbol), unavailable, "current_price")
    history = _fetch(
        lambda: market.get_historical_ohlc(symbol, start=start, end=end, interval=interval),
        unavailable,
        "historical_ohlc",
    )
    if history is not None and not history.prices:
        unavailable.append("historical_ohlc")
        history = None
    volume = _fetch(lambda: market.get_volume(symbol), unavailable, "volume")
    market_info = _fetch(lambda: market.get_market_info(symbol), unavailable, "market_info")
    return _InstrumentSnapshot(
        symbol=symbol,
        quote=quote,
        history=history,
        volume=volume,
        market_info=market_info,
        index=index,
        index_history=index_history,
        unavailable=_unique(unavailable),
    )


def _fetch(operation: Callable[[], T], unavailable: list[str], label: str) -> T | None:
    try:
        return operation()
    except ProviderError:
        unavailable.append(label)
        return None


def _compute_symbol_analysis(
    snapshot: _InstrumentSnapshot, windows: _Windows
) -> ComputedSymbolAnalysis:
    unavailable = list(snapshot.unavailable)
    quote = snapshot.quote
    history = snapshot.history
    volume = snapshot.volume
    info = snapshot.market_info
    bars = sorted_bars(history)
    asset_closes = [bar.close for bar in bars]

    current_price = quote.value if quote is not None else None
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

    historical_return = total_return(asset_closes)
    extremes = price_extremes(bars)
    short_sma = simple_moving_average(asset_closes, windows.short)
    long_sma = simple_moving_average(asset_closes, windows.long)
    volatility = realized_volatility(
        asset_closes,
        periods_per_year=windows.periods_per_year,
        min_returns=windows.min_volatility_returns,
    )
    momentum = price_momentum(asset_closes, windows.momentum)
    trend_label = classify_trend(
        asset_closes, short_window=windows.short, long_window=windows.long
    )
    trend: TrendDirection = trend_label if trend_label is not None else "insufficient_data"

    aligned = aligned_closes(history, snapshot.index_history)
    rel_perf = relative_performance(*aligned) if aligned is not None else None

    average_volume = volume.average_volume if volume is not None else None
    if average_volume is None:
        historical_volumes = [bar.volume for bar in bars if bar.volume is not None]
        average_volume = mean(historical_volumes)
    current_volume = volume.value if volume is not None else None
    ratio = (
        volume_ratio(current_volume, average_volume) if current_volume is not None else None
    )

    _mark_missing(unavailable, "historical_return", historical_return, history is not None)
    _mark_missing(unavailable, "volatility", volatility, history is not None)
    _mark_missing(unavailable, "momentum", momentum, history is not None)
    _mark_missing(
        unavailable, "relative_performance", rel_perf, snapshot.index_history is not None
    )
    _mark_missing(unavailable, "volume_ratio", ratio, current_volume is not None)

    metrics = MarketSupportingMetrics(
        symbol=snapshot.symbol,
        current_price=current_price,
        currency=currency,
        exchange=exchange,
        change=quote.change if quote is not None else None,
        change_percent=quote.change_percent if quote is not None else None,
        quote_timestamp=quote.timestamp if quote is not None else None,
        historical_start_price=asset_closes[0] if asset_closes else None,
        historical_end_price=asset_closes[-1] if asset_closes else None,
        historical_return=historical_return,
        historical_high=extremes[0] if extremes is not None else None,
        historical_low=extremes[1] if extremes is not None else None,
        bar_count=len(bars) if bars else None,
        history_start=bars[0].timestamp if bars else None,
        history_end=bars[-1].timestamp if bars else None,
        volume=current_volume,
        average_volume=average_volume,
        volume_ratio=ratio,
        volume_timestamp=volume.timestamp if volume is not None else None,
        index_symbol=snapshot.index.symbol if snapshot.index is not None else None,
        index_name=snapshot.index.name if snapshot.index is not None else None,
        index_level=snapshot.index.value if snapshot.index is not None else None,
        index_change_percent=(
            snapshot.index.change_percent if snapshot.index is not None else None
        ),
        index_timestamp=snapshot.index.timestamp if snapshot.index is not None else None,
        short_sma=short_sma,
        long_sma=long_sma,
        volatility=volatility,
        momentum=momentum,
        relative_performance=rel_perf,
    )
    unavailable = _unique(unavailable)
    as_of = _as_of(snapshot, bars)
    return ComputedSymbolAnalysis(
        symbol=snapshot.symbol,
        trend=trend,
        supporting_metrics=metrics,
        unavailable=unavailable,
        as_of=as_of,
        sources=_sources(snapshot),
        factual_observations=_factual_observations(metrics, trend, unavailable),
    )


def _mark_missing(unavailable: list[str], label: str, value: Any, relevant: bool) -> None:
    if relevant and value is None and label not in unavailable:
        unavailable.append(label)


def _first_present(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _as_of(snapshot: _InstrumentSnapshot, bars: list[HistoricalPrice]) -> datetime | None:
    timestamps: list[datetime] = []
    if snapshot.quote is not None:
        timestamps.append(snapshot.quote.timestamp)
    if snapshot.volume is not None:
        timestamps.append(snapshot.volume.timestamp)
    if snapshot.index is not None:
        timestamps.append(snapshot.index.timestamp)
    if bars:
        timestamps.append(bars[-1].timestamp)
    return max(timestamps) if timestamps else None


def _sources(snapshot: _InstrumentSnapshot) -> list[DataSourceMetadata]:
    payloads = [
        snapshot.quote,
        snapshot.history,
        snapshot.volume,
        snapshot.market_info,
        snapshot.index,
        snapshot.index_history,
    ]
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


def _factual_observations(
    metrics: MarketSupportingMetrics,
    trend: TrendDirection,
    unavailable: list[str],
) -> list[str]:
    observations: list[str] = []
    symbol = metrics.symbol
    if metrics.current_price is not None:
        stamped = _stamp(metrics.quote_timestamp)
        currency = f" {metrics.currency}" if metrics.currency else ""
        observations.append(
            f"{symbol} current price is {metrics.current_price}{currency} as of {stamped}."
        )
    if metrics.historical_return is not None and metrics.bar_count:
        observations.append(
            f"{symbol} historical return over {metrics.bar_count} bars is "
            f"{metrics.historical_return}."
        )
    if metrics.volume is not None:
        observations.append(f"{symbol} traded volume is {metrics.volume}.")
    if metrics.volume_ratio is not None:
        observations.append(
            f"{symbol} volume ratio versus average is {metrics.volume_ratio}."
        )
    if metrics.index_level is not None and metrics.index_symbol:
        observations.append(
            f"Index {metrics.index_symbol} level is {metrics.index_level} "
            f"as of {_stamp(metrics.index_timestamp)}."
        )
    observations.append(f"{symbol} trend is {trend}.")
    if metrics.volatility is not None:
        observations.append(
            f"{symbol} annualized realized volatility is {metrics.volatility}."
        )
    if metrics.momentum is not None:
        observations.append(f"{symbol} momentum is {metrics.momentum}.")
    if metrics.relative_performance is not None:
        observations.append(
            f"{symbol} relative performance versus the benchmark is "
            f"{metrics.relative_performance}."
        )
    if unavailable:
        observations.append("Unavailable and not estimated: " + ", ".join(unavailable) + ".")
    return observations


def _stamp(value: datetime | None) -> str:
    if value is None:
        return "unknown time"
    return value.isoformat()


def _record_evidence(
    runtime: AgentRuntime,
    computed: ComputedSymbolAnalysis,
    snapshot: _InstrumentSnapshot,
) -> None:
    metrics = computed.supporting_metrics
    if snapshot.quote is not None:
        runtime.evidence.add(
            Evidence(
                source=snapshot.quote.source,
                symbol=computed.symbol,
                field="price",
                value=snapshot.quote.value,
            )
        )
    if snapshot.volume is not None:
        runtime.evidence.add(
            Evidence(
                source=snapshot.volume.source,
                symbol=computed.symbol,
                field="volume",
                value=snapshot.volume.value,
            )
        )
    if snapshot.history is not None and metrics.historical_end_price is not None:
        runtime.evidence.add(
            Evidence(
                source=snapshot.history.source,
                symbol=computed.symbol,
                period=snapshot.history.period,
                field="historical_close",
                value=metrics.historical_end_price,
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
    derived_source = DataSourceMetadata(
        provider=runtime.providers.market_data.name,
        source="derived-indicator",
        timestamp=computed.as_of or datetime.now(tz=UTC),
    )
    derived = (
        ("historical_return", metrics.historical_return),
        ("short_sma", metrics.short_sma),
        ("long_sma", metrics.long_sma),
        ("volatility", metrics.volatility),
        ("momentum", metrics.momentum),
        ("relative_performance", metrics.relative_performance),
        ("volume_ratio", metrics.volume_ratio),
    )
    for field_name, value in derived:
        if value is None:
            continue
        runtime.evidence.add(
            Evidence(
                source=derived_source,
                symbol=computed.symbol,
                field=field_name,
                value=value,
            )
        )
    runtime.evidence.add(
        Evidence(
            source=derived_source,
            symbol=computed.symbol,
            field="trend",
            value=computed.trend,
        )
    )


def _build_extras(
    interpretation: MarketInterpretation,
    analyses: list[ComputedSymbolAnalysis],
    *,
    provider_name: str,
    interval: str,
) -> MarketAgentExtras:
    risks = list(interpretation.risks)
    gap_risk = _gap_risk(analyses)
    if gap_risk and gap_risk not in risks:
        risks.append(gap_risk)
    return MarketAgentExtras(
        market_assessment=interpretation.market_assessment,
        trend=_overall_trend(analyses),
        supporting_metrics=analyses[0].supporting_metrics,
        risks=risks,
        key_observations=list(interpretation.key_observations),
        as_of=_latest_as_of(analyses),
        analyzed_at=datetime.now(tz=UTC),
        sources=_merge_sources(analyses),
        unavailable=_merge_unavailable(analyses),
        market_data_provider=provider_name,
        interval=interval,
        analyses=analyses,
    )


def _interpretation_prompt(payload: AgentInput, analyses: list[ComputedSymbolAnalysis]) -> str:
    bundle = {
        "request_id": payload.request_id,
        "question": payload.question,
        "symbols": payload.symbols,
        "analyses": [item.model_dump(mode="json") for item in analyses],
        "rules": [
            "Numeric values were calculated from retrieved market data.",
            "Null fields and the unavailable lists are missing. Do not fill them in.",
            "Do not cite prices, volumes, or dates that are not in this payload.",
        ],
    }
    return (
        "Interpret the following market evidence and return market_assessment, "
        "risks, key_observations, and confidence.\n\n"
        + json.dumps(bundle, indent=2)
    )


def _gap_risk(analyses: list[ComputedSymbolAnalysis]) -> str | None:
    missing = _merge_unavailable(analyses)
    if not missing:
        return None
    return "Unavailable inputs were not estimated: " + ", ".join(missing) + "."


def _overall_trend(analyses: list[ComputedSymbolAnalysis]) -> OverallTrend:
    labels = {item.trend for item in analyses}
    if len(labels) == 1:
        return next(iter(labels))
    return "mixed"


def _merge_sources(analyses: list[ComputedSymbolAnalysis]) -> list[DataSourceMetadata]:
    merged: list[DataSourceMetadata] = []
    seen: set[str] = set()
    for analysis in analyses:
        for source in analysis.sources:
            key = source.model_dump_json()
            if key not in seen:
                seen.add(key)
                merged.append(source)
    return merged


def _merge_unavailable(analyses: list[ComputedSymbolAnalysis]) -> list[str]:
    merged: list[str] = []
    for analysis in analyses:
        for item in analysis.unavailable:
            if item not in merged:
                merged.append(item)
    return merged


def _latest_as_of(analyses: list[ComputedSymbolAnalysis]) -> datetime | None:
    timestamps = [item.as_of for item in analyses if item.as_of is not None]
    return max(timestamps) if timestamps else None


def _capped_confidence(confidence: float, unavailable: list[str]) -> float:
    if {"current_price", "historical_ohlc"} & set(unavailable):
        return min(confidence, 0.5)
    return confidence


def _unique(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen
