"""Deterministic portfolio-risk calculations.

These helpers operate only on uploaded holdings and numeric series already
retrieved from providers. They never call a vendor, estimate missing prices,
or ask an LLM for a number. Insufficient input yields `None`.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Literal

from app.models.market import OhlcSeries
from app.tools.market import realized_volatility, simple_returns, sorted_bars

WeightBasis = Literal["market_value", "uploaded_weight", "cost_value", "insufficient_data"]
ConcentrationLabel = Literal["low", "moderate", "high", "insufficient_data"]
DiversificationLabel = Literal["diversified", "moderate", "concentrated", "insufficient_data"]

UNCLASSIFIED_SECTOR = "unclassified"

DEFAULT_MIN_RETURNS = 5
DEFAULT_PERIODS_PER_YEAR = 252
DEFAULT_LARGE_POSITION_THRESHOLD = 0.20
DEFAULT_TOP_N = 3
HHI_LOW = 0.15
HHI_HIGH = 0.25
HIGH_CONCENTRATION_WEIGHT = 0.40
HIGH_CORRELATION = 0.70
MODERATE_CORRELATION = 0.40
CONCENTRATED_EFFECTIVE_N = 2.0
MODERATE_EFFECTIVE_N = 4.0


def close_map(series: OhlcSeries | None) -> dict[datetime, float]:
    """Timestamp-to-close mapping. Empty when the series is missing."""
    return {bar.timestamp: bar.close for bar in sorted_bars(series)}


def normalized_weights(values: Sequence[float]) -> list[float] | None:
    """Scale non-negative values so they sum to 1. `None` if a weight cannot be formed."""
    if not values:
        return None
    if any(not math.isfinite(value) or value < 0 for value in values):
        return None
    total = sum(values)
    if total <= 0:
        return None
    return [value / total for value in values]


def _complete(values: Sequence[float | None], *, allow_zero: bool) -> list[float] | None:
    completed: list[float] = []
    for value in values:
        if value is None or not math.isfinite(value):
            return None
        if value < 0 or (not allow_zero and value == 0):
            return None
        completed.append(value)
    return completed or None


def resolve_weight_vector(
    *,
    market_values: Sequence[float | None],
    uploaded_weights: Sequence[float | None],
    cost_values: Sequence[float | None],
    mixed_currency: bool = False,
) -> tuple[list[float] | None, WeightBasis]:
    """Choose one complete weight basis. Missing legs are not mixed together.

    Market values and cost values are skipped when holdings use more than one
    currency, because this layer does not convert FX.
    """
    if not mixed_currency:
        market = _complete(market_values, allow_zero=False)
        if market is not None:
            weights = normalized_weights(market)
            if weights is not None:
                return weights, "market_value"
    uploaded = _complete(uploaded_weights, allow_zero=True)
    if uploaded is not None:
        weights = normalized_weights(uploaded)
        if weights is not None:
            return weights, "uploaded_weight"
    if not mixed_currency:
        cost = _complete(cost_values, allow_zero=False)
        if cost is not None:
            weights = normalized_weights(cost)
            if weights is not None:
                return weights, "cost_value"
    return None, "insufficient_data"


def herfindahl_hirschman_index(weights: Sequence[float]) -> float | None:
    """Sum of squared weights. `None` when weights are missing or invalid."""
    normalized = normalized_weights(weights)
    if normalized is None:
        return None
    return sum(weight * weight for weight in normalized)


def effective_n(weights: Sequence[float]) -> float | None:
    """`1 / HHI`, the effective number of holdings. `None` if HHI is missing or 0."""
    hhi = herfindahl_hirschman_index(weights)
    if hhi is None or hhi == 0:
        return None
    return 1.0 / hhi


def largest_share(weights: Sequence[float]) -> float | None:
    """Largest normalized weight."""
    normalized = normalized_weights(weights)
    if normalized is None:
        return None
    return max(normalized)


def top_n_share(weights: Sequence[float], n: int) -> float | None:
    """Sum of the `n` largest normalized weights."""
    if n < 1:
        return None
    normalized = normalized_weights(weights)
    if normalized is None:
        return None
    leading = sorted(normalized, reverse=True)[:n]
    return sum(leading)


def sector_weights(
    weights: Sequence[float],
    sectors: Sequence[str | None],
) -> dict[str, float] | None:
    """Aggregate position weights by sector. Missing sectors become `unclassified`."""
    if len(weights) != len(sectors):
        return None
    normalized = normalized_weights(weights)
    if normalized is None:
        return None
    grouped: dict[str, float] = {}
    for weight, sector in zip(normalized, sectors):
        label = sector.strip() if isinstance(sector, str) and sector.strip() else UNCLASSIFIED_SECTOR
        grouped[label] = grouped.get(label, 0.0) + weight
    return grouped


def classify_concentration(
    *,
    hhi: float | None = None,
    largest: float | None = None,
    large_position_threshold: float = DEFAULT_LARGE_POSITION_THRESHOLD,
) -> ConcentrationLabel:
    """Severity from HHI and the largest weight. Missing inputs are skipped, not filled."""
    ranks: list[int] = []
    if hhi is not None:
        if hhi >= HHI_HIGH:
            ranks.append(2)
        elif hhi >= HHI_LOW:
            ranks.append(1)
        else:
            ranks.append(0)
    if largest is not None:
        high_weight = max(HIGH_CONCENTRATION_WEIGHT, large_position_threshold * 2)
        if largest >= high_weight:
            ranks.append(2)
        elif largest >= large_position_threshold:
            ranks.append(1)
        else:
            ranks.append(0)
    if not ranks:
        return "insufficient_data"
    worst = max(ranks)
    if worst >= 2:
        return "high"
    if worst == 1:
        return "moderate"
    return "low"


def classify_diversification(
    *,
    effective_n_value: float | None = None,
    holding_count: int | None = None,
    average_correlation: float | None = None,
) -> DiversificationLabel:
    """Diversification from effective N and average pairwise correlation."""
    labels: list[DiversificationLabel] = []
    if effective_n_value is not None:
        if holding_count is not None and holding_count <= 1:
            labels.append("concentrated")
        elif effective_n_value < CONCENTRATED_EFFECTIVE_N:
            labels.append("concentrated")
        elif effective_n_value < MODERATE_EFFECTIVE_N:
            labels.append("moderate")
        else:
            labels.append("diversified")
    if average_correlation is not None:
        if average_correlation >= HIGH_CORRELATION:
            labels.append("concentrated")
        elif average_correlation >= MODERATE_CORRELATION:
            labels.append("moderate")
        else:
            labels.append("diversified")
    if not labels:
        return "insufficient_data"
    if "concentrated" in labels:
        return "concentrated"
    if "moderate" in labels:
        return "moderate"
    return "diversified"


def equal_weight(holding_count: int) -> float | None:
    """`1 / n`. `None` when there are no holdings."""
    if holding_count < 1:
        return None
    return 1.0 / holding_count


def oversized_symbols(
    weights_by_symbol: Mapping[str, float | None],
    *,
    threshold: float = DEFAULT_LARGE_POSITION_THRESHOLD,
) -> list[str]:
    """Symbols whose weight meets or exceeds the position-size threshold."""
    if threshold <= 0:
        return []
    flagged = [
        symbol
        for symbol, weight in weights_by_symbol.items()
        if weight is not None and weight >= threshold
    ]
    return sorted(flagged)


def max_drawdown(values: Sequence[float]) -> float | None:
    """Worst peak-to-trough decline as a negative fraction. `None` if unsafe."""
    if len(values) < 2:
        return None
    peak = values[0]
    if peak <= 0:
        return None
    worst = 0.0
    for value in values:
        if value <= 0 or not math.isfinite(value):
            return None
        if value > peak:
            peak = value
        drawdown = (value / peak) - 1.0
        if drawdown < worst:
            worst = drawdown
    return worst


def aligned_portfolio_values(
    quantities: Mapping[str, float],
    closes_by_symbol: Mapping[str, Mapping[datetime, float]],
) -> tuple[list[datetime], list[float]] | None:
    """Portfolio market values on timestamps shared by every included series.

    Symbols absent from `closes_by_symbol` are excluded. Dates are never
    interpolated. `None` unless at least two strictly positive values exist.
    """
    symbols = [
        symbol
        for symbol, quantity in quantities.items()
        if quantity > 0 and closes_by_symbol.get(symbol)
    ]
    if not symbols:
        return None
    common = set(closes_by_symbol[symbols[0]])
    for symbol in symbols[1:]:
        common &= set(closes_by_symbol[symbol])
    if len(common) < 2:
        return None
    timestamps = sorted(common)
    values: list[float] = []
    for timestamp in timestamps:
        total = 0.0
        for symbol in symbols:
            total += quantities[symbol] * closes_by_symbol[symbol][timestamp]
        if total <= 0 or not math.isfinite(total):
            return None
        values.append(total)
    return timestamps, values


def pearson_correlation(
    left: Sequence[float],
    right: Sequence[float],
    *,
    min_observations: int = DEFAULT_MIN_RETURNS,
) -> float | None:
    """Sample Pearson correlation. `None` if the series is too short or degenerate."""
    if min_observations < 2 or len(left) != len(right) or len(left) < min_observations:
        return None
    try:
        return statistics.correlation(left, right)
    except statistics.StatisticsError:
        return None


def pairwise_correlation(
    left_closes: Mapping[datetime, float],
    right_closes: Mapping[datetime, float],
    *,
    min_returns: int = DEFAULT_MIN_RETURNS,
) -> tuple[float | None, int]:
    """Correlation of simple returns on shared timestamps. No interpolation."""
    common = sorted(set(left_closes) & set(right_closes))
    if len(common) < 2:
        return None, 0
    left_returns = simple_returns([left_closes[ts] for ts in common])
    right_returns = simple_returns([right_closes[ts] for ts in common])
    if left_returns is None or right_returns is None:
        return None, 0
    overlapping = len(left_returns)
    return pearson_correlation(
        left_returns, right_returns, min_observations=min_returns
    ), overlapping


def mean_pairwise_correlation(
    closes_by_symbol: Mapping[str, Mapping[datetime, float]],
    *,
    min_returns: int = DEFAULT_MIN_RETURNS,
) -> float | None:
    """Average of computable pairwise return correlations. Pairs are not filled in."""
    symbols = [symbol for symbol, series in closes_by_symbol.items() if series]
    if len(symbols) < 2:
        return None
    observed: list[float] = []
    for index, left in enumerate(symbols):
        for right in symbols[index + 1 :]:
            corr, _overlap = pairwise_correlation(
                closes_by_symbol[left], closes_by_symbol[right], min_returns=min_returns
            )
            if corr is not None:
                observed.append(corr)
    if not observed:
        return None
    return statistics.fmean(observed)


def sample_covariance(left: Sequence[float], right: Sequence[float]) -> float | None:
    """Sample covariance. `None` unless both series have at least two points."""
    if len(left) != len(right) or len(left) < 2:
        return None
    try:
        return statistics.covariance(left, right)
    except statistics.StatisticsError:
        return None


def beta(
    asset_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    *,
    min_returns: int = DEFAULT_MIN_RETURNS,
) -> float | None:
    """`cov(asset, benchmark) / var(benchmark)`. `None` if variance is 0 or short."""
    if (
        min_returns < 2
        or len(asset_returns) != len(benchmark_returns)
        or len(asset_returns) < min_returns
    ):
        return None
    covariance = sample_covariance(asset_returns, benchmark_returns)
    try:
        variance = statistics.variance(benchmark_returns)
    except statistics.StatisticsError:
        return None
    if covariance is None or variance == 0:
        return None
    return covariance / variance


def tracking_error(
    asset_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    *,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
    min_returns: int = DEFAULT_MIN_RETURNS,
) -> float | None:
    """Annualized standard deviation of active returns."""
    if (
        periods_per_year < 1
        or min_returns < 2
        or len(asset_returns) != len(benchmark_returns)
        or len(asset_returns) < min_returns
    ):
        return None
    active = [asset - bench for asset, bench in zip(asset_returns, benchmark_returns)]
    try:
        return statistics.stdev(active) * math.sqrt(periods_per_year)
    except statistics.StatisticsError:
        return None


def aligned_return_pair(
    asset_closes: Mapping[datetime, float],
    benchmark_closes: Mapping[datetime, float],
) -> tuple[list[float], list[float]] | None:
    """Simple returns on shared timestamps. No interpolation."""
    common = sorted(set(asset_closes) & set(benchmark_closes))
    if len(common) < 2:
        return None
    asset_returns = simple_returns([asset_closes[ts] for ts in common])
    benchmark_returns = simple_returns([benchmark_closes[ts] for ts in common])
    if asset_returns is None or benchmark_returns is None:
        return None
    return asset_returns, benchmark_returns


def diversification_ratio(
    weighted_average_volatility: float | None,
    portfolio_volatility: float | None,
) -> float | None:
    """Weighted average asset vol divided by portfolio vol. `None` if unsafe."""
    if (
        weighted_average_volatility is None
        or portfolio_volatility is None
        or portfolio_volatility <= 0
        or weighted_average_volatility < 0
    ):
        return None
    return weighted_average_volatility / portfolio_volatility


def relative_volatility(
    portfolio_volatility: float | None,
    benchmark_volatility: float | None,
) -> float | None:
    """Portfolio vol divided by benchmark vol. `None` if the benchmark vol is 0."""
    if (
        portfolio_volatility is None
        or benchmark_volatility is None
        or benchmark_volatility <= 0
        or portfolio_volatility < 0
    ):
        return None
    return portfolio_volatility / benchmark_volatility


def weighted_average(
    values: Sequence[float | None],
    weights: Sequence[float],
) -> float | None:
    """Weight only positions whose value is present. `None` if no pair remains."""
    if len(values) != len(weights):
        return None
    total_weight = 0.0
    total = 0.0
    for value, weight in zip(values, weights):
        if value is None or not math.isfinite(weight) or weight < 0:
            continue
        total += value * weight
        total_weight += weight
    if total_weight <= 0:
        return None
    return total / total_weight


def series_volatility(
    closes: Mapping[datetime, float],
    *,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
    min_returns: int = DEFAULT_MIN_RETURNS,
) -> float | None:
    """Annualized realized volatility of a close map."""
    if not closes:
        return None
    ordered = [closes[ts] for ts in sorted(closes)]
    return realized_volatility(
        ordered, periods_per_year=periods_per_year, min_returns=min_returns
    )


def series_drawdown(closes: Mapping[datetime, float]) -> float | None:
    """Max drawdown of a close map ordered by timestamp."""
    if not closes:
        return None
    ordered = [closes[ts] for ts in sorted(closes)]
    return max_drawdown(ordered)
