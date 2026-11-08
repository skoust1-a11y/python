"""Unit tests for deterministic market-indicator helpers."""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta, timezone

import pytest

from app.models.common import DataSourceMetadata
from app.models.market import HistoricalPrice, OhlcSeries
from app.tools.market import (
    aligned_closes,
    classify_trend,
    closes,
    mean,
    price_extremes,
    price_momentum,
    relative_performance,
    realized_volatility,
    simple_moving_average,
    simple_returns,
    sorted_bars,
    total_return,
    volume_ratio,
)

UTC = timezone.utc


def _source() -> DataSourceMetadata:
    return DataSourceMetadata(
        provider="unit-test",
        source="fixture",
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
    )


def _series(symbol: str, values: list[tuple[datetime, float]]) -> OhlcSeries:
    prices = [
        HistoricalPrice(
            symbol=symbol,
            timestamp=ts,
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
            period="1d",
            volume=1000,
            source=_source(),
        )
        for ts, close in values
    ]
    return OhlcSeries(symbol=symbol, period="1d", prices=prices, source=_source())


def test_total_return_is_last_over_first_minus_one() -> None:
    assert total_return([100.0, 110.0]) == pytest.approx(0.1)
    assert total_return([100.0]) is None
    assert total_return([0.0, 10.0]) is None
    assert total_return([]) is None


def test_simple_returns_reject_zero_base_price() -> None:
    assert simple_returns([100.0, 110.0, 121.0]) == pytest.approx([0.1, 0.1])
    assert simple_returns([100.0]) is None
    assert simple_returns([0.0, 10.0]) is None


def test_simple_moving_average_uses_trailing_window() -> None:
    assert simple_moving_average([1.0, 2.0, 3.0, 4.0, 5.0], 3) == 4.0
    assert simple_moving_average([1.0, 2.0], 3) is None
    assert simple_moving_average([1.0, 2.0], 0) is None


def test_realized_volatility_annualizes_sample_stdev() -> None:
    constant_growth = [100.0, 110.0, 121.0]
    assert realized_volatility(constant_growth, min_returns=2) == 0.0
    assert realized_volatility([100.0, 110.0], min_returns=2) is None

    prices = [100.0, 101.0, 99.0, 102.0, 104.0, 103.0]
    returns = simple_returns(prices)
    assert returns is not None
    expected = statistics.stdev(returns) * math.sqrt(252)
    assert realized_volatility(prices) == expected


def test_price_momentum_uses_lookback_close() -> None:
    assert price_momentum([100.0, 101.0, 110.0], lookback=2) == pytest.approx(0.1)
    assert price_momentum([100.0, 110.0], lookback=2) is None
    assert price_momentum([0.0, 1.0, 2.0], lookback=2) is None


def test_relative_performance_is_return_gap() -> None:
    assert relative_performance([100.0, 120.0], [100.0, 110.0]) == pytest.approx(0.1)
    assert relative_performance([100.0], [100.0, 110.0]) is None


def test_classify_trend_from_sma_relationship() -> None:
    uptrend = [float(i) for i in range(1, 21)]
    downtrend = [float(i) for i in range(20, 0, -1)]
    flat = [10.0] * 20
    assert classify_trend(uptrend) == "uptrend"
    assert classify_trend(downtrend) == "downtrend"
    assert classify_trend(flat) == "sideways"
    assert classify_trend(uptrend[:10]) is None


def test_volume_ratio_requires_nonzero_average() -> None:
    assert volume_ratio(200.0, 100.0) == 2.0
    assert volume_ratio(200.0, 0.0) is None
    assert volume_ratio(200.0, None) is None


def test_aligned_closes_require_shared_timestamps_and_do_not_interpolate() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    asset = _series(
        "AAPL",
        [
            (start, 100.0),
            (start + timedelta(days=1), 110.0),
            (start + timedelta(days=2), 120.0),
        ],
    )
    benchmark = _series(
        "^TEST",
        [
            (start, 1000.0),
            (start + timedelta(days=2), 1010.0),
            (start + timedelta(days=3), 1020.0),
        ],
    )
    aligned = aligned_closes(asset, benchmark)
    assert aligned == ([100.0, 120.0], [1000.0, 1010.0])
    assert aligned_closes(asset, None) is None


def test_sorted_bars_and_extremes_use_ohlc_not_close_only() -> None:
    start = datetime(2024, 6, 1, tzinfo=UTC)
    later = start + timedelta(days=1)
    earlier_bar = HistoricalPrice(
        symbol="MSFT",
        timestamp=later,
        open=10.0,
        high=12.0,
        low=9.0,
        close=11.0,
        period="1d",
        source=_source(),
    )
    later_bar = HistoricalPrice(
        symbol="MSFT",
        timestamp=start,
        open=8.0,
        high=15.0,
        low=7.5,
        close=9.0,
        period="1d",
        source=_source(),
    )
    series = OhlcSeries(
        symbol="MSFT",
        period="1d",
        prices=[earlier_bar, later_bar],
        source=_source(),
    )
    ordered = sorted_bars(series)
    assert ordered[0].timestamp == start
    assert closes(series) == [9.0, 11.0]
    assert price_extremes(ordered) == (15.0, 7.5)
    assert mean([2.0, 4.0]) == 3.0
    assert mean([]) is None
