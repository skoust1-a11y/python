"""Unit tests for deterministic portfolio-risk helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.common import DataSourceMetadata
from app.models.market import HistoricalPrice, OhlcSeries
from app.tools.market import simple_returns
from app.tools.risk import (
    UNCLASSIFIED_SECTOR,
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
    top_n_share,
    tracking_error,
)

UTC = timezone.utc
START = datetime(2024, 1, 2, 14, 30, tzinfo=UTC)


def _source() -> DataSourceMetadata:
    return DataSourceMetadata(
        provider="unit-test",
        source="fixture",
        timestamp=START,
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


def test_herfindahl_and_effective_n_from_normalized_weights() -> None:
    weights = [0.5, 0.3, 0.2]
    assert herfindahl_hirschman_index(weights) == pytest.approx(0.38)
    assert effective_n(weights) == pytest.approx(1 / 0.38)
    assert largest_share(weights) == pytest.approx(0.5)
    assert top_n_share(weights, 2) == pytest.approx(0.8)
    assert herfindahl_hirschman_index([]) is None
    assert herfindahl_hirschman_index([-0.1, 1.1]) is None
    assert top_n_share(weights, 0) is None


def test_resolve_weight_vector_prefers_complete_market_values() -> None:
    weights, basis = resolve_weight_vector(
        market_values=[100.0, 100.0],
        uploaded_weights=[0.8, 0.2],
        cost_values=[50.0, 150.0],
    )
    assert basis == "market_value"
    assert weights == pytest.approx([0.5, 0.5])


def test_resolve_weight_vector_falls_back_without_mixing_bases() -> None:
    uploaded, uploaded_basis = resolve_weight_vector(
        market_values=[100.0, None],
        uploaded_weights=[0.25, 0.75],
        cost_values=[10.0, 90.0],
    )
    assert uploaded_basis == "uploaded_weight"
    assert uploaded == pytest.approx([0.25, 0.75])

    cost, cost_basis = resolve_weight_vector(
        market_values=[None, 50.0],
        uploaded_weights=[None, 1.0],
        cost_values=[25.0, 75.0],
    )
    assert cost_basis == "cost_value"
    assert cost == pytest.approx([0.25, 0.75])

    missing, missing_basis = resolve_weight_vector(
        market_values=[None, 10.0],
        uploaded_weights=[0.4, None],
        cost_values=[None, 5.0],
    )
    assert missing is None
    assert missing_basis == "insufficient_data"


def test_mixed_currency_skips_market_and_cost_values() -> None:
    weights, basis = resolve_weight_vector(
        market_values=[100.0, 100.0],
        uploaded_weights=[0.6, 0.4],
        cost_values=[80.0, 20.0],
        mixed_currency=True,
    )
    assert basis == "uploaded_weight"
    assert weights == pytest.approx([0.6, 0.4])

    missing, missing_basis = resolve_weight_vector(
        market_values=[100.0, 100.0],
        uploaded_weights=[None, 1.0],
        cost_values=[50.0, 50.0],
        mixed_currency=True,
    )
    assert missing is None
    assert missing_basis == "insufficient_data"


def test_sector_weights_bucket_missing_labels() -> None:
    grouped = sector_weights([0.5, 0.3, 0.2], ["Technology", None, "Technology"])
    assert grouped == pytest.approx({"Technology": 0.7, UNCLASSIFIED_SECTOR: 0.3})
    assert sector_weights([0.5, 0.5], ["Tech"]) is None


def test_classify_concentration_and_diversification() -> None:
    assert classify_concentration(hhi=0.10, largest=0.12) == "low"
    assert classify_concentration(hhi=0.20, largest=0.22) == "moderate"
    assert classify_concentration(hhi=0.50, largest=0.50) == "high"
    assert classify_concentration() == "insufficient_data"

    assert (
        classify_diversification(effective_n_value=8.0, holding_count=10, average_correlation=0.2)
        == "diversified"
    )
    assert classify_diversification(effective_n_value=3.0, average_correlation=0.5) == "moderate"
    assert classify_diversification(effective_n_value=1.2, average_correlation=0.9) == "concentrated"
    assert classify_diversification() == "insufficient_data"


def test_max_drawdown_is_peak_to_trough_and_rejects_short_or_nonpositive_series() -> None:
    assert max_drawdown([100.0, 110.0, 88.0, 99.0]) == pytest.approx((88.0 / 110.0) - 1.0)
    assert max_drawdown([100.0, 101.0, 102.0]) == 0.0
    assert max_drawdown([100.0]) is None
    assert max_drawdown([100.0, 0.0, 80.0]) is None
    assert max_drawdown([]) is None


def test_aligned_portfolio_values_require_shared_timestamps_and_do_not_interpolate() -> None:
    day0, day1, day2, day3 = START, START + timedelta(days=1), START + timedelta(days=2), START + timedelta(days=3)
    result = aligned_portfolio_values(
        {"AAPL": 2.0, "MSFT": 1.0},
        {
            "AAPL": {day0: 10.0, day1: 11.0, day2: 12.0},
            "MSFT": {day0: 20.0, day2: 22.0, day3: 24.0},
        },
    )
    assert result is not None
    timestamps, values = result
    assert timestamps == [day0, day2]
    assert values == pytest.approx([40.0, 46.0])
    assert aligned_portfolio_values({"AAPL": 1.0}, {}) is None


def test_pairwise_correlation_uses_overlapping_returns_only() -> None:
    day0, day1, day2 = START, START + timedelta(days=1), START + timedelta(days=2)
    left = {day0: 100.0, day1: 110.0, day2: 99.0}
    right = {day0: 50.0, day1: 40.0, day2: 60.0}
    corr, overlap = pairwise_correlation(left, right, min_returns=2)
    expected_left = simple_returns([100.0, 110.0, 99.0])
    expected_right = simple_returns([50.0, 40.0, 60.0])
    assert expected_left is not None and expected_right is not None
    assert corr == pytest.approx(pearson_correlation(expected_left, expected_right, min_observations=2))
    assert overlap == 2

    short = {day0: 100.0, day1: 101.0}
    assert pairwise_correlation(left, short, min_returns=5) == (None, 1)


def test_mean_pairwise_correlation_skips_pairs_that_cannot_be_formed() -> None:
    day0, day1, day2, day3, day4, day5, day6 = (
        START + timedelta(days=offset) for offset in range(7)
    )
    identical = {
        day0: 100.0,
        day1: 101.0,
        day2: 102.0,
        day3: 103.0,
        day4: 104.0,
        day5: 105.0,
        day6: 106.0,
    }
    mean = mean_pairwise_correlation(
        {"AAPL": identical, "MSFT": identical, "GOOG": {day0: 10.0}},
        min_returns=5,
    )
    assert mean == pytest.approx(1.0)
    assert mean_pairwise_correlation({"AAPL": identical}) is None


def test_beta_and_tracking_error_require_enough_aligned_returns() -> None:
    asset = [0.01, 0.02, -0.01, 0.00, 0.03, 0.01]
    bench = [0.01, 0.015, -0.005, 0.00, 0.02, 0.005]
    assert beta(asset, bench, min_returns=5) is not None
    assert tracking_error(asset, bench, min_returns=5) is not None
    assert beta(asset[:3], bench[:3], min_returns=5) is None
    assert tracking_error(asset[:3], bench[:3], min_returns=5) is None
    assert aligned_return_pair({START: 100.0}, {START: 1000.0}) is None


def test_beta_is_one_when_asset_matches_benchmark() -> None:
    returns = [0.01, -0.02, 0.015, 0.0, 0.005, 0.01]
    assert beta(returns, returns, min_returns=5) == pytest.approx(1.0)
    assert tracking_error(returns, returns, min_returns=5) == pytest.approx(0.0)


def test_diversification_and_relative_volatility_guard_zero_denominators() -> None:
    assert diversification_ratio(0.20, 0.10) == pytest.approx(2.0)
    assert diversification_ratio(0.20, 0.0) is None
    assert diversification_ratio(None, 0.10) is None
    assert relative_volatility(0.20, 0.10) == pytest.approx(2.0)
    assert relative_volatility(0.20, 0.0) is None


def test_oversized_symbols_and_equal_weight() -> None:
    assert equal_weight(4) == 0.25
    assert equal_weight(0) is None
    assert oversized_symbols({"AAPL": 0.45, "MSFT": 0.10, "GOOG": None}, threshold=0.20) == ["AAPL"]
    assert oversized_symbols({"AAPL": 0.10}, threshold=0.20) == []


def test_close_map_and_series_drawdown_follow_timestamp_order() -> None:
    later = START + timedelta(days=1)
    series = _series("MSFT", [(later, 80.0), (START, 100.0)])
    mapped = close_map(series)
    assert mapped[START] == 100.0
    assert mapped[later] == 80.0
    assert list(mapped) == [START, later]
    assert series_drawdown(mapped) == pytest.approx(-0.2)
    assert close_map(None) == {}
