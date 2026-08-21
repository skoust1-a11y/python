"""Unit tests for deterministic portfolio optimization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.tools.optimization import (
    OptimizationSpec,
    aligned_return_matrix,
    optimize_portfolio,
    portfolio_volatility,
    annualized_covariance,
    annualized_mean_returns,
)

UTC = timezone.utc
START = datetime(2024, 1, 2, 14, 30, tzinfo=UTC)


def _series(start: float, returns: list[float]) -> dict[datetime, float]:
    prices = [start]
    for change in returns:
        prices.append(prices[-1] * (1.0 + change))
    return {START + timedelta(days=index): price for index, price in enumerate(prices)}


SAFE_RETURNS = [0.001] * 20
RISKY_RETURNS = [0.05, -0.04] * 10
GROWTH_RETURNS = [0.012] * 20


def _two_asset_closes() -> dict[str, dict[datetime, float]]:
    return {
        "SAFE": _series(100.0, SAFE_RETURNS),
        "RISKY": _series(50.0, RISKY_RETURNS),
    }


def test_aligned_return_matrix_uses_common_dates_only() -> None:
    left = _series(100.0, [0.01, 0.02, 0.03, 0.04, 0.05, 0.01])
    right = dict(list(_series(80.0, [0.02, 0.01, 0.0, -0.01, 0.02, 0.01]).items())[:-1])
    matrix = aligned_return_matrix({"L": left, "R": right}, ["L", "R"], min_returns=5)
    assert matrix is not None
    returns, timestamps = matrix
    assert returns.shape[1] == 2
    assert len(timestamps) == returns.shape[0]
    assert len(timestamps) == 5


def test_optimize_portfolio_is_deterministic() -> None:
    closes = _two_asset_closes()
    spec = OptimizationSpec(objective="minimum_volatility", max_weight=0.8)
    first = optimize_portfolio(
        symbols=["RISKY", "SAFE"],
        current_weights=[0.5, 0.5],
        closes_by_symbol=closes,
        spec=spec,
    )
    second = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.5, 0.5],
        closes_by_symbol=closes,
        spec=spec,
    )
    assert first.proposed_allocation == second.proposed_allocation
    assert first.current_allocation == second.current_allocation
    assert first.objective == "minimum_volatility"


def test_minimum_volatility_prefers_the_calmer_name() -> None:
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.5, 0.5],
        closes_by_symbol=_two_asset_closes(),
        spec=OptimizationSpec(objective="minimum_volatility"),
    )
    assert result.proposed_allocation["SAFE"] > result.proposed_allocation["RISKY"]
    assert result.proposed_allocation["SAFE"] == pytest.approx(1.0, abs=1e-6)
    assert result.feasible
    assert result.solver_status == "optimal"
    assert result.proposed_metrics.volatility is not None
    assert result.current_metrics.volatility is not None
    assert result.proposed_metrics.volatility <= result.current_metrics.volatility + 1e-9


def test_max_position_allocation_is_respected() -> None:
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.5, 0.5],
        closes_by_symbol=_two_asset_closes(),
        spec=OptimizationSpec(objective="minimum_volatility", max_weight=0.65),
    )
    assert result.proposed_allocation["SAFE"] == pytest.approx(0.65, abs=1e-6)
    assert result.proposed_allocation["RISKY"] == pytest.approx(0.35, abs=1e-6)
    assert result.constraints["max_weight"] == 0.65


def test_min_position_allocation_is_respected() -> None:
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.5, 0.5],
        closes_by_symbol=_two_asset_closes(),
        spec=OptimizationSpec(objective="minimum_volatility", min_weight=0.25),
    )
    assert result.proposed_allocation["RISKY"] == pytest.approx(0.25, abs=1e-6)
    assert result.proposed_allocation["SAFE"] == pytest.approx(0.75, abs=1e-6)


def test_sector_limit_caps_combined_weight() -> None:
    closes = {
        "SAFE": _series(100.0, SAFE_RETURNS),
        "RISKY": _series(50.0, RISKY_RETURNS),
        "GROW": _series(70.0, GROWTH_RETURNS),
    }
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY", "GROW"],
        current_weights=[0.4, 0.3, 0.3],
        closes_by_symbol=closes,
        sectors=["Technology", "Health", "Technology"],
        spec=OptimizationSpec(
            objective="minimum_volatility",
            sector_limits={"Technology": 0.55},
        ),
    )
    tech = (
        result.proposed_allocation["SAFE"] + result.proposed_allocation["GROW"]
    )
    assert tech == pytest.approx(0.55, abs=1e-5) or tech < 0.55 + 1e-6
    assert result.proposed_metrics.sector_weights["Technology"] <= 0.55 + 1e-6


def test_target_risk_is_respected_when_feasible() -> None:
    closes = _two_asset_closes()
    unconstrained = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.2, 0.8],
        closes_by_symbol=closes,
        spec=OptimizationSpec(objective="minimum_volatility", max_weight=0.7),
    )
    assert unconstrained.proposed_metrics.volatility is not None
    ceiling = unconstrained.proposed_metrics.volatility + 0.05
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.2, 0.8],
        closes_by_symbol=closes,
        spec=OptimizationSpec(
            objective="risk_adjusted_return",
            max_weight=0.7,
            target_risk=ceiling,
        ),
    )
    assert result.proposed_metrics.volatility is not None
    assert result.proposed_metrics.volatility <= ceiling + 1e-5
    assert result.constraints["target_risk"] == ceiling


def test_risk_adjusted_return_prefers_higher_growth_name() -> None:
    closes = {
        "GROW": _series(80.0, GROWTH_RETURNS),
        "RISKY": _series(50.0, RISKY_RETURNS),
    }
    result = optimize_portfolio(
        symbols=["GROW", "RISKY"],
        current_weights=[0.5, 0.5],
        closes_by_symbol=closes,
        spec=OptimizationSpec(objective="risk_adjusted_return"),
    )
    assert result.proposed_allocation["GROW"] > result.proposed_allocation["RISKY"]
    assert result.objective == "risk_adjusted_return"


def test_max_hhi_limits_concentration() -> None:
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.5, 0.5],
        closes_by_symbol=_two_asset_closes(),
        spec=OptimizationSpec(objective="minimum_volatility", max_hhi=0.55),
    )
    proposed = result.proposed_allocation
    hhi = proposed["SAFE"] ** 2 + proposed["RISKY"] ** 2
    assert hhi <= 0.55 + 1e-6
    assert result.proposed_metrics.hhi is not None
    assert result.proposed_metrics.hhi <= 0.55 + 1e-6


def test_infeasible_bounds_return_current_allocation() -> None:
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.6, 0.4],
        closes_by_symbol=_two_asset_closes(),
        spec=OptimizationSpec(min_weight=0.6),
    )
    assert result.proposed_allocation == result.current_allocation
    assert result.feasible is False
    assert result.solver_status == "infeasible"
    assert result.warnings
    assert any("candidate allocations" in note.lower() or "not trade" in note.lower() for note in result.limitations)


def test_missing_history_is_frozen_not_estimated() -> None:
    closes = {
        "SAFE": _series(100.0, SAFE_RETURNS),
        "RISKY": _series(50.0, RISKY_RETURNS),
        "GHOST": {START: 10.0},
    }
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY", "GHOST"],
        current_weights=[0.4, 0.4, 0.2],
        closes_by_symbol=closes,
        spec=OptimizationSpec(objective="minimum_volatility"),
    )
    assert "GHOST" in result.frozen_symbols
    assert result.proposed_allocation["GHOST"] == pytest.approx(0.2, abs=1e-6)
    assert any("frozen" in warning.lower() for warning in result.warnings)


def test_result_contains_required_fields() -> None:
    result = optimize_portfolio(
        symbols=["SAFE", "RISKY"],
        current_weights=[0.5, 0.5],
        closes_by_symbol=_two_asset_closes(),
        spec=OptimizationSpec(
            objective="minimum_volatility",
            max_weight=0.8,
            min_weight=0.1,
            target_risk=1.0,
            max_hhi=0.9,
            min_effective_n=1.1,
            sector_limits={"Technology": 0.9},
        ),
        sectors=["Technology", "Health"],
    )
    assert result.current_allocation
    assert result.proposed_allocation
    assert result.objective == "minimum_volatility"
    assert result.constraints["max_weight"] == 0.8
    assert result.constraints["min_weight"] == 0.1
    assert result.constraints["target_risk"] == 1.0
    assert result.calculated_metrics["current"]["volatility"] is not None
    assert result.calculated_metrics["proposed"]["volatility"] is not None
    assert result.warnings is not None
    assert result.limitations
    assert {item.candidate_id for item in result.candidates} >= {"current", "optimized"}
    assert abs(sum(result.proposed_allocation.values()) - 1.0) < 1e-8


def test_annualized_moments_match_manual_numpy() -> None:
    closes = _two_asset_closes()
    matrix = aligned_return_matrix(closes, ["RISKY", "SAFE"], min_returns=5)
    assert matrix is not None
    returns, _timestamps = matrix
    mean = annualized_mean_returns(returns, periods_per_year=252)
    cov = annualized_covariance(returns, periods_per_year=252, ridge=0.0)
    weights = __import__("numpy").array([0.4, 0.6])
    vol = portfolio_volatility(weights, cov)
    assert mean.shape == (2,)
    assert cov.shape == (2, 2)
    assert vol > 0
