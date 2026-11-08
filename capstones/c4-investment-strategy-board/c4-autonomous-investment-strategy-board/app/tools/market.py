"""Deterministic market-indicator calculations.

These helpers operate only on numeric series already retrieved from a
`MarketDataProvider`. They never call a vendor, estimate missing prices, or
ask an LLM for a number. Insufficient input yields `None`.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Literal

from app.models.market import HistoricalPrice, OhlcSeries

TrendLabel = Literal["uptrend", "downtrend", "sideways"]

DEFAULT_SHORT_WINDOW = 5
DEFAULT_LONG_WINDOW = 20
DEFAULT_MOMENTUM_LOOKBACK = 10
DEFAULT_MIN_VOLATILITY_RETURNS = 5
DEFAULT_PERIODS_PER_YEAR = 252


def sorted_bars(series: OhlcSeries | None) -> list[HistoricalPrice]:
    """Return OHLC bars ordered by timestamp. Empty when the series is missing."""
    if series is None or not series.prices:
        return []
    return sorted(series.prices, key=lambda bar: bar.timestamp)


def closes(series: OhlcSeries | None) -> list[float]:
    """Closing prices in chronological order."""
    return [bar.close for bar in sorted_bars(series)]


def simple_returns(prices: Sequence[float]) -> list[float] | None:
    """Period-to-period simple returns. `None` if a ratio cannot be formed."""
    if len(prices) < 2:
        return None
    returns: list[float] = []
    for previous, current in zip(prices, prices[1:]):
        if previous == 0:
            return None
        returns.append((current / previous) - 1.0)
    return returns


def total_return(prices: Sequence[float]) -> float | None:
    """`(last / first) - 1`. `None` when a return cannot be computed."""
    if len(prices) < 2 or prices[0] == 0:
        return None
    return (prices[-1] / prices[0]) - 1.0


def simple_moving_average(values: Sequence[float], window: int) -> float | None:
    """Trailing SMA over `window` observations, or `None` if too short."""
    if window < 1 or len(values) < window:
        return None
    return statistics.fmean(values[-window:])


def mean(values: Sequence[float]) -> float | None:
    """Arithmetic mean, or `None` when `values` is empty."""
    if not values:
        return None
    return statistics.fmean(values)


def realized_volatility(
    prices: Sequence[float],
    *,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
    min_returns: int = DEFAULT_MIN_VOLATILITY_RETURNS,
) -> float | None:
    """Annualized sample standard deviation of simple returns.

    Returns `None` unless at least `min_returns` valid returns are present.
    """
    if periods_per_year < 1 or min_returns < 2:
        return None
    returns = simple_returns(prices)
    if returns is None or len(returns) < min_returns:
        return None
    return statistics.stdev(returns) * math.sqrt(periods_per_year)


def price_momentum(
    prices: Sequence[float],
    lookback: int = DEFAULT_MOMENTUM_LOOKBACK,
) -> float | None:
    """Rate of change versus the close `lookback` periods earlier."""
    if lookback < 1 or len(prices) <= lookback:
        return None
    start = prices[-(lookback + 1)]
    if start == 0:
        return None
    return (prices[-1] / start) - 1.0


def relative_performance(
    asset_prices: Sequence[float],
    benchmark_prices: Sequence[float],
) -> float | None:
    """Asset total return minus benchmark total return over the same window."""
    asset_return = total_return(asset_prices)
    benchmark_return = total_return(benchmark_prices)
    if asset_return is None or benchmark_return is None:
        return None
    return asset_return - benchmark_return


def classify_trend(
    prices: Sequence[float],
    *,
    short_window: int = DEFAULT_SHORT_WINDOW,
    long_window: int = DEFAULT_LONG_WINDOW,
) -> TrendLabel | None:
    """Classify trend from trailing SMAs and the last price.

    `None` when the series is shorter than `long_window`.
    """
    if short_window < 1 or long_window < short_window:
        return None
    short = simple_moving_average(prices, short_window)
    long = simple_moving_average(prices, long_window)
    if short is None or long is None:
        return None
    last = prices[-1]
    if short > long and last > long:
        return "uptrend"
    if short < long and last < long:
        return "downtrend"
    return "sideways"


def volume_ratio(current: float, average: float | None) -> float | None:
    """Current volume divided by average volume. `None` if average is missing or 0."""
    if average is None or average == 0:
        return None
    return current / average


def price_extremes(
    bars: Sequence[HistoricalPrice],
) -> tuple[float, float] | None:
    """Highest high and lowest low in the bar set."""
    if not bars:
        return None
    return max(bar.high for bar in bars), min(bar.low for bar in bars)


def aligned_closes(
    asset: OhlcSeries | None,
    benchmark: OhlcSeries | None,
) -> tuple[list[float], list[float]] | None:
    """Pair closes that share an exact timestamp. No interpolation."""
    asset_bars = sorted_bars(asset)
    benchmark_bars = sorted_bars(benchmark)
    if not asset_bars or not benchmark_bars:
        return None
    asset_by_ts: Mapping[datetime, float] = {bar.timestamp: bar.close for bar in asset_bars}
    benchmark_by_ts: Mapping[datetime, float] = {bar.timestamp: bar.close for bar in benchmark_bars}
    common = sorted(set(asset_by_ts) & set(benchmark_by_ts))
    if len(common) < 2:
        return None
    return [asset_by_ts[ts] for ts in common], [benchmark_by_ts[ts] for ts in common]
