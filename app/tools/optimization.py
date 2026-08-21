"""Deterministic mean-variance portfolio optimization.

This module produces candidate allocations from uploaded weights and retrieved
price history. It never calls a vendor, never asks an LLM for a number, and
never emits trade orders. Missing history is frozen at the current weight
instead of being estimated.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Literal

import numpy as np
from scipy.optimize import minimize

from app.tools.market import simple_returns
from app.tools.risk import (
    UNCLASSIFIED_SECTOR,
    classify_diversification,
    effective_n,
    herfindahl_hirschman_index,
    largest_share,
    normalized_weights,
    sector_weights,
)

OptimizationObjective = Literal["minimum_volatility", "risk_adjusted_return"]
SolverStatus = Literal["optimal", "relaxed", "infeasible", "skipped"]

DEFAULT_MIN_WEIGHT = 0.0
DEFAULT_MAX_WEIGHT = 1.0
DEFAULT_MIN_RETURNS = 5
DEFAULT_PERIODS_PER_YEAR = 252
DEFAULT_RIDGE = 1e-10
DEFAULT_WEIGHT_DECIMALS = 10
SUM_TOLERANCE = 1e-8
SOLVER_FTOL = 1e-12
SOLVER_MAXITER = 500

STANDARD_LIMITATIONS = (
    "Optimization uses historical sample means and covariance, not a forecast.",
    "This is a long-only mean-variance prototype; factor models, Black-Litterman, and shrinkage estimators are not used.",
    "Transaction costs, taxes, turnover, and liquidity are ignored.",
    "Proposed weights are candidate allocations for later evaluation, not trade orders or executed positions.",
    "Cash is not a separate sleeve; candidate weights are constrained to sum to 1.",
)


@dataclass(frozen=True)
class OptimizationSpec:
    """Bounded prototype constraints. Unset optional limits are not applied."""

    objective: OptimizationObjective = "minimum_volatility"
    min_weight: float = DEFAULT_MIN_WEIGHT
    max_weight: float = DEFAULT_MAX_WEIGHT
    min_weights: dict[str, float] = field(default_factory=dict)
    max_weights: dict[str, float] = field(default_factory=dict)
    sector_limits: dict[str, float] = field(default_factory=dict)
    target_risk: float | None = None
    min_effective_n: float | None = None
    max_hhi: float | None = None
    risk_free_rate: float = 0.0
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR
    min_returns: int = DEFAULT_MIN_RETURNS
    ridge: float = DEFAULT_RIDGE
    long_only: bool = True
    fully_invested: bool = True


@dataclass(frozen=True)
class SleeveMetrics:
    """Risk/return figures for one weight vector. Null means it could not be formed."""

    expected_return: float | None
    volatility: float | None
    risk_adjusted_return: float | None
    hhi: float | None
    effective_n: float | None
    largest_weight: float | None
    largest_symbol: str | None
    sector_weights: dict[str, float]
    diversification: str


@dataclass(frozen=True)
class CandidateAllocation:
    """One evaluated sleeve the Manager Agent can compare later."""

    candidate_id: str
    label: str
    objective: OptimizationObjective | Literal["current"]
    weights: dict[str, float]
    metrics: SleeveMetrics
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class OptimizationComputation:
    """Python optimizer result before LLM interpretation."""

    current_allocation: dict[str, float]
    proposed_allocation: dict[str, float]
    objective: OptimizationObjective
    constraints: dict[str, Any]
    current_metrics: SleeveMetrics
    proposed_metrics: SleeveMetrics
    calculated_metrics: dict[str, Any]
    candidates: tuple[CandidateAllocation, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    solver_status: SolverStatus
    feasible: bool
    optimized_symbols: tuple[str, ...]
    frozen_symbols: tuple[str, ...]
    return_observations: int | None
    periods_per_year: int


def aligned_return_matrix(
    closes_by_symbol: Mapping[str, Mapping[datetime, float]],
    symbols: Sequence[str],
    *,
    min_returns: int = DEFAULT_MIN_RETURNS,
) -> tuple[np.ndarray, list[datetime]] | None:
    """Simple returns on timestamps shared by every symbol. No interpolation."""
    if not symbols or min_returns < 2:
        return None
    if any(not closes_by_symbol.get(symbol) for symbol in symbols):
        return None
    common = set(closes_by_symbol[symbols[0]])
    for symbol in symbols[1:]:
        common &= set(closes_by_symbol[symbol])
    timestamps = sorted(common)
    if len(timestamps) < min_returns + 1:
        return None
    prices = np.array(
        [[closes_by_symbol[symbol][timestamp] for symbol in symbols] for timestamp in timestamps],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(prices)) or np.any(prices[:-1] == 0):
        return None
    returns = prices[1:] / prices[:-1] - 1.0
    if returns.shape[0] < min_returns or not np.all(np.isfinite(returns)):
        return None
    return returns, timestamps[1:]


def annualized_mean_returns(returns: np.ndarray, *, periods_per_year: int) -> np.ndarray:
    """Arithmetic mean of period returns, annualized by `periods_per_year`."""
    return returns.mean(axis=0) * float(periods_per_year)


def annualized_covariance(
    returns: np.ndarray,
    *,
    periods_per_year: int,
    ridge: float = DEFAULT_RIDGE,
) -> np.ndarray:
    """Sample covariance of period returns, annualized, with a tiny diagonal ridge."""
    columns = returns.shape[1]
    if columns == 1:
        variance = float(np.var(returns[:, 0], ddof=1))
        cov = np.array([[variance]], dtype=np.float64)
    else:
        cov = np.atleast_2d(np.cov(returns, rowvar=False, ddof=1)).astype(np.float64)
    if cov.shape != (columns, columns):
        cov = np.eye(columns, dtype=np.float64) * float(np.var(returns, ddof=1))
    if ridge > 0:
        cov = cov + ridge * np.eye(columns, dtype=np.float64)
    return cov * float(periods_per_year)


def portfolio_variance(weights: np.ndarray, covariance: np.ndarray) -> float:
    return float(weights @ covariance @ weights)


def portfolio_volatility(weights: np.ndarray, covariance: np.ndarray) -> float:
    variance = max(portfolio_variance(weights, covariance), 0.0)
    return math.sqrt(variance)


def portfolio_expected_return(weights: np.ndarray, mean_returns: np.ndarray) -> float:
    return float(weights @ mean_returns)


def risk_adjusted_return(
    weights: np.ndarray,
    mean_returns: np.ndarray,
    covariance: np.ndarray,
    *,
    risk_free_rate: float = 0.0,
) -> float | None:
    """Excess return per unit of volatility. `None` when volatility is 0."""
    vol = portfolio_volatility(weights, covariance)
    if vol <= 0:
        return None
    return (portfolio_expected_return(weights, mean_returns) - risk_free_rate) / vol


def optimize_portfolio(
    *,
    symbols: Sequence[str],
    current_weights: Sequence[float],
    closes_by_symbol: Mapping[str, Mapping[datetime, float]],
    sectors: Sequence[str | None] | None = None,
    spec: OptimizationSpec | None = None,
) -> OptimizationComputation:
    """Solve a bounded long-only allocation. Identical inputs yield identical weights."""
    spec = spec or OptimizationSpec()
    ordered = _ordered_symbols(symbols)
    current = _aligned_current_weights(ordered, symbols, current_weights)
    sector_labels = _aligned_sectors(ordered, symbols, sectors)
    warnings: list[str] = []
    limitations = list(STANDARD_LIMITATIONS)

    if spec.ridge > 0:
        limitations.append(
            "A tiny diagonal ridge is added to the sample covariance for numerical stability."
        )

    current_map = _weight_map(ordered, current)
    if abs(sum(current) - 1.0) > SUM_TOLERANCE:
        warnings.append("Current weights were renormalized so they sum to 1.")

    frozen, tradable = _partition_universe(
        ordered, closes_by_symbol, min_returns=spec.min_returns
    )
    if frozen:
        warnings.append(
            "Positions without a complete overlapping return history were frozen at "
            "their current weights: " + ", ".join(frozen) + "."
        )
        warnings.append(
            "Target-risk and diversification constraints are applied to the optimized sleeve only."
        )

    matrix = (
        aligned_return_matrix(
            closes_by_symbol, tradable, min_returns=spec.min_returns
        )
        if tradable
        else None
    )
    if matrix is None:
        warnings.append(
            "A sample covariance could not be formed, so the current allocation was returned."
        )
        current_metrics = _metrics_without_moments(
            current, ordered, sector_labels, spec.risk_free_rate
        )
        return _skipped_result(
            ordered,
            current_map,
            spec,
            current_metrics,
            warnings,
            limitations,
            frozen=tuple(frozen),
        )

    returns, _timestamps = matrix
    mean_returns = annualized_mean_returns(returns, periods_per_year=spec.periods_per_year)
    covariance = annualized_covariance(
        returns, periods_per_year=spec.periods_per_year, ridge=spec.ridge
    )
    tradable_index = {symbol: index for index, symbol in enumerate(tradable)}
    full_mean, full_cov = _embed_moments(
        ordered, tradable_index, mean_returns, covariance
    )
    current_metrics = _sleeve_metrics(
        current, ordered, sector_labels, full_mean, full_cov, spec.risk_free_rate
    )

    proposed, status, solve_warnings = _solve_with_relaxation(
        ordered=ordered,
        tradable=tradable,
        frozen=frozen,
        current=current,
        sector_labels=sector_labels,
        tradable_mean=mean_returns,
        tradable_cov=covariance,
        spec=spec,
    )
    warnings.extend(solve_warnings)
    if proposed is None:
        proposed = current.copy()
        status = "infeasible"
        warnings.append(
            "Requested constraints were infeasible; the current allocation is the candidate."
        )

    proposed_metrics = _sleeve_metrics(
        proposed, ordered, sector_labels, full_mean, full_cov, spec.risk_free_rate
    )
    proposed_map = _weight_map(ordered, proposed)
    constraints = _constraint_snapshot(spec, ordered, sector_labels)
    calculated = _calculated_metrics(
        current_metrics,
        proposed_metrics,
        status=status,
        feasible=status in {"optimal", "relaxed"},
        return_observations=int(returns.shape[0]),
        periods_per_year=spec.periods_per_year,
    )
    candidates = (
        CandidateAllocation(
            candidate_id="current",
            label="Current allocation",
            objective="current",
            weights=current_map,
            metrics=current_metrics,
            notes=("Baseline sleeve. Not a proposed change.",),
        ),
        CandidateAllocation(
            candidate_id="optimized",
            label=_candidate_label(spec.objective),
            objective=spec.objective,
            weights=proposed_map,
            metrics=proposed_metrics,
            notes=(
                "Candidate only. The Manager Agent should evaluate this sleeve; it is not an order.",
            ),
        ),
    )
    return OptimizationComputation(
        current_allocation=current_map,
        proposed_allocation=proposed_map,
        objective=spec.objective,
        constraints=constraints,
        current_metrics=current_metrics,
        proposed_metrics=proposed_metrics,
        calculated_metrics=calculated,
        candidates=candidates,
        warnings=tuple(_unique(warnings)),
        limitations=tuple(_unique(limitations)),
        solver_status=status,
        feasible=status in {"optimal", "relaxed"},
        optimized_symbols=tuple(tradable),
        frozen_symbols=tuple(frozen),
        return_observations=int(returns.shape[0]),
        periods_per_year=spec.periods_per_year,
    )


def _ordered_symbols(symbols: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for symbol in symbols:
        token = str(symbol).strip().upper()
        if token and token not in seen:
            seen.append(token)
    return sorted(seen)


def _aligned_current_weights(
    ordered: Sequence[str],
    symbols: Sequence[str],
    current_weights: Sequence[float],
) -> np.ndarray:
    raw = {str(symbol).strip().upper(): float(weight) for symbol, weight in zip(symbols, current_weights)}
    values = [raw.get(symbol, 0.0) for symbol in ordered]
    normalized = normalized_weights(values)
    if normalized is None:
        equal = 1.0 / len(ordered) if ordered else 0.0
        return np.full(len(ordered), equal, dtype=np.float64)
    return np.array(normalized, dtype=np.float64)


def _aligned_sectors(
    ordered: Sequence[str],
    symbols: Sequence[str],
    sectors: Sequence[str | None] | None,
) -> list[str | None]:
    raw: dict[str, str | None] = {}
    if sectors is not None:
        for symbol, sector in zip(symbols, sectors):
            raw[str(symbol).strip().upper()] = sector
    return [raw.get(symbol) for symbol in ordered]


def _partition_universe(
    ordered: Sequence[str],
    closes_by_symbol: Mapping[str, Mapping[datetime, float]],
    *,
    min_returns: int,
) -> tuple[list[str], list[str]]:
    frozen: list[str] = []
    tradable: list[str] = []
    for symbol in ordered:
        series = closes_by_symbol.get(symbol) or {}
        if len(series) < min_returns + 1:
            frozen.append(symbol)
            continue
        prices = [series[timestamp] for timestamp in sorted(series)]
        if simple_returns(prices) is None:
            frozen.append(symbol)
            continue
        tradable.append(symbol)
    if not tradable:
        return list(ordered), []
    if aligned_return_matrix(closes_by_symbol, tradable, min_returns=min_returns) is None:
        still_frozen = list(ordered)
        return still_frozen, []
    return frozen, tradable


def _embed_moments(
    ordered: Sequence[str],
    tradable_index: Mapping[str, int],
    mean_returns: np.ndarray,
    covariance: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n = len(ordered)
    full_mean = np.zeros(n, dtype=np.float64)
    full_cov = np.zeros((n, n), dtype=np.float64)
    for row, symbol in enumerate(ordered):
        if symbol not in tradable_index:
            continue
        source_row = tradable_index[symbol]
        full_mean[row] = mean_returns[source_row]
        for column, other in enumerate(ordered):
            if other not in tradable_index:
                continue
            full_cov[row, column] = covariance[source_row, tradable_index[other]]
    return full_mean, full_cov


def _solve_with_relaxation(
    *,
    ordered: Sequence[str],
    tradable: Sequence[str],
    frozen: Sequence[str],
    current: np.ndarray,
    sector_labels: Sequence[str | None],
    tradable_mean: np.ndarray,
    tradable_cov: np.ndarray,
    spec: OptimizationSpec,
) -> tuple[np.ndarray | None, SolverStatus, list[str]]:
    attempts = _relaxation_attempts(spec)
    warnings: list[str] = []
    for attempt_name, attempt_spec in attempts:
        solved = _solve_once(
            ordered=ordered,
            tradable=tradable,
            frozen=frozen,
            current=current,
            sector_labels=sector_labels,
            tradable_mean=tradable_mean,
            tradable_cov=tradable_cov,
            spec=attempt_spec,
        )
        if solved is None:
            continue
        status: SolverStatus = "optimal" if attempt_name == "requested" else "relaxed"
        if status == "relaxed":
            warnings.append(
                f"The solver relaxed constraints ({attempt_name.replace('_', ' ')}) to obtain a candidate."
            )
        return solved, status, warnings
    return None, "infeasible", warnings


def _relaxation_attempts(spec: OptimizationSpec) -> list[tuple[str, OptimizationSpec]]:
    attempts: list[tuple[str, OptimizationSpec]] = [("requested", spec)]
    working = spec
    if working.target_risk is not None:
        working = replace(working, target_risk=None)
        attempts.append(("without_target_risk", working))
    if working.max_hhi is not None or working.min_effective_n is not None:
        working = replace(working, max_hhi=None, min_effective_n=None)
        attempts.append(("without_diversification_limits", working))
    if working.sector_limits:
        working = replace(working, sector_limits={})
        attempts.append(("without_sector_limits", working))
    return attempts


def _solve_once(
    *,
    ordered: Sequence[str],
    tradable: Sequence[str],
    frozen: Sequence[str],
    current: np.ndarray,
    sector_labels: Sequence[str | None],
    tradable_mean: np.ndarray,
    tradable_cov: np.ndarray,
    spec: OptimizationSpec,
) -> np.ndarray | None:
    if not tradable:
        return None
    ordered_index = {symbol: index for index, symbol in enumerate(ordered)}
    frozen_weight = float(sum(current[ordered_index[symbol]] for symbol in frozen))
    remaining = 1.0 - frozen_weight
    if remaining <= SUM_TOLERANCE and frozen:
        if remaining < -SUM_TOLERANCE:
            return None
        return current.copy()

    mins = np.array([_floor(spec, symbol) for symbol in tradable], dtype=np.float64)
    maxs = np.array([_ceiling(spec, symbol) for symbol in tradable], dtype=np.float64)
    if spec.long_only:
        mins = np.maximum(mins, 0.0)
        maxs = np.maximum(maxs, mins)
    if float(mins.sum()) - remaining > SUM_TOLERANCE:
        return None
    if remaining - float(maxs.sum()) > SUM_TOLERANCE:
        return None

    current_tradable = np.array(
        [current[ordered_index[symbol]] for symbol in tradable], dtype=np.float64
    )
    x0 = _starting_weights(current_tradable, mins, maxs, remaining)
    if x0 is None:
        return None

    constraints = _solver_constraints(
        tradable,
        tradable_cov,
        sector_labels_for=dict(zip(ordered, sector_labels)),
        spec=spec,
        remaining=remaining,
    )
    bounds = list(zip(mins.tolist(), maxs.tolist()))
    objective, jacobian = _objective_functions(spec, tradable_mean, tradable_cov)
    result = minimize(
        objective,
        x0,
        method="SLSQP",
        jac=jacobian,
        bounds=bounds,
        constraints=constraints,
        options={"ftol": SOLVER_FTOL, "maxiter": SOLVER_MAXITER, "disp": False},
    )
    if not result.success:
        return None
    solved = np.asarray(result.x, dtype=np.float64)
    if not _tradable_feasible(
        solved,
        tradable,
        sector_labels_for=dict(zip(ordered, sector_labels)),
        spec=spec,
        remaining=remaining,
        covariance=tradable_cov,
        mins=mins,
        maxs=maxs,
    ):
        return None
    cleaned = _sanitize_weights(solved, mins, maxs, remaining)
    if cleaned is None:
        return None
    full = np.zeros(len(ordered), dtype=np.float64)
    for symbol in frozen:
        full[ordered_index[symbol]] = current[ordered_index[symbol]]
    for index, symbol in enumerate(tradable):
        full[ordered_index[symbol]] = cleaned[index]
    return _weight_vector(ordered, full)


def _objective_functions(
    spec: OptimizationSpec,
    mean_returns: np.ndarray,
    covariance: np.ndarray,
) -> tuple[Any, Any]:
    if spec.objective == "risk_adjusted_return":

        def objective(weights: np.ndarray) -> float:
            score = risk_adjusted_return(
                weights,
                mean_returns,
                covariance,
                risk_free_rate=spec.risk_free_rate,
            )
            return 0.0 if score is None else -float(score)

        def jacobian(weights: np.ndarray) -> np.ndarray:
            vol = portfolio_volatility(weights, covariance)
            if vol <= 0:
                return np.zeros_like(weights)
            excess = portfolio_expected_return(weights, mean_returns) - spec.risk_free_rate
            cov_w = covariance @ weights
            return -(mean_returns / vol - excess * cov_w / (vol ** 3))

        return objective, jacobian

    def objective(weights: np.ndarray) -> float:
        return portfolio_variance(weights, covariance)

    def jacobian(weights: np.ndarray) -> np.ndarray:
        return 2.0 * (covariance @ weights)

    return objective, jacobian


def _solver_constraints(
    tradable: Sequence[str],
    covariance: np.ndarray,
    *,
    sector_labels_for: Mapping[str, str | None],
    spec: OptimizationSpec,
    remaining: float,
) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = [
        {
            "type": "eq",
            "fun": lambda weights, budget=remaining: float(np.sum(weights) - budget),
            "jac": lambda weights, budget=remaining: np.ones(len(weights), dtype=np.float64),
        }
    ]
    if spec.target_risk is not None and spec.target_risk > 0:
        limit = spec.target_risk ** 2

        def _risk_fun(weights: np.ndarray, cap: float = limit) -> float:
            return float(cap - portfolio_variance(weights, covariance))

        def _risk_jac(weights: np.ndarray) -> np.ndarray:
            return -2.0 * (covariance @ weights)

        constraints.append({"type": "ineq", "fun": _risk_fun, "jac": _risk_jac})

    hhi_cap = _hhi_cap(spec)
    if hhi_cap is not None:

        def _hhi_fun(weights: np.ndarray, cap: float = hhi_cap) -> float:
            return float(cap - float(weights @ weights))

        def _hhi_jac(weights: np.ndarray) -> np.ndarray:
            return -2.0 * weights

        constraints.append({"type": "ineq", "fun": _hhi_fun, "jac": _hhi_jac})

    for sector, cap in sorted(spec.sector_limits.items()):
        indexes = [
            index
            for index, symbol in enumerate(tradable)
            if _sector_label(sector_labels_for.get(symbol)) == sector
        ]
        if not indexes:
            continue

        def _sector_fun(
            weights: np.ndarray,
            cols: list[int] = indexes,
            limit: float = cap,
        ) -> float:
            return float(limit - float(sum(weights[col] for col in cols)))

        def _sector_jac(
            weights: np.ndarray,
            cols: list[int] = indexes,
        ) -> np.ndarray:
            grad = np.zeros(len(weights), dtype=np.float64)
            grad[cols] = -1.0
            return grad

        constraints.append({"type": "ineq", "fun": _sector_fun, "jac": _sector_jac})
    return constraints


def _tradable_feasible(
    weights: np.ndarray,
    tradable: Sequence[str],
    *,
    sector_labels_for: Mapping[str, str | None],
    spec: OptimizationSpec,
    remaining: float,
    covariance: np.ndarray,
    mins: np.ndarray,
    maxs: np.ndarray,
) -> bool:
    if np.any(weights < mins - 1e-6) or np.any(weights > maxs + 1e-6):
        return False
    if abs(float(weights.sum()) - remaining) > 1e-5:
        return False
    if spec.target_risk is not None and spec.target_risk > 0:
        if portfolio_volatility(weights, covariance) > spec.target_risk + 1e-5:
            return False
    hhi_cap = _hhi_cap(spec)
    if hhi_cap is not None and float(weights @ weights) > hhi_cap + 1e-6:
        return False
    grouped = sector_weights(weights.tolist(), [_sector_label(sector_labels_for.get(symbol)) for symbol in tradable])
    if grouped and spec.sector_limits:
        for sector, cap in spec.sector_limits.items():
            if grouped.get(sector, 0.0) > cap + 1e-6:
                return False
    return True


def _starting_weights(
    current: np.ndarray,
    mins: np.ndarray,
    maxs: np.ndarray,
    remaining: float,
) -> np.ndarray | None:
    clipped = np.clip(current, mins, maxs)
    if abs(float(clipped.sum()) - remaining) <= 1e-6 and np.all(clipped >= mins - 1e-12):
        return clipped
    return _feasible_start(mins, maxs, remaining)


def _feasible_start(mins: np.ndarray, maxs: np.ndarray, remaining: float) -> np.ndarray | None:
    if remaining < -SUM_TOLERANCE:
        return None
    if float(mins.sum()) - remaining > SUM_TOLERANCE:
        return None
    if remaining - float(maxs.sum()) > SUM_TOLERANCE:
        return None
    weights = mins.copy()
    leftover = remaining - float(weights.sum())
    headroom = maxs - weights
    while leftover > 1e-15 and float(headroom.sum()) > 1e-15:
        add = headroom * (leftover / float(headroom.sum()))
        add = np.minimum(add, headroom)
        weights = weights + add
        leftover = remaining - float(weights.sum())
        headroom = maxs - weights
        if float(np.max(add)) < 1e-18:
            break
    if abs(float(weights.sum()) - remaining) > 1e-6:
        return None
    return weights


def _sanitize_weights(
    weights: np.ndarray,
    mins: np.ndarray,
    maxs: np.ndarray,
    remaining: float,
) -> np.ndarray | None:
    cleaned = np.clip(np.asarray(weights, dtype=np.float64), mins, maxs)
    total = float(cleaned.sum())
    if total <= 0:
        return None
    cleaned = cleaned * (remaining / total)
    cleaned = np.clip(cleaned, mins, maxs)
    total = float(cleaned.sum())
    if total <= 0:
        return None
    cleaned = cleaned * (remaining / total)
    return np.round(cleaned, DEFAULT_WEIGHT_DECIMALS)


def _weight_vector(symbols: Sequence[str], weights: Sequence[float]) -> np.ndarray:
    mapping = _weight_map(symbols, weights)
    return np.array([mapping[symbol] for symbol in symbols], dtype=np.float64)


def _weight_map(symbols: Sequence[str], weights: Sequence[float]) -> dict[str, float]:
    values = [round(float(weight), DEFAULT_WEIGHT_DECIMALS) for weight in weights]
    if not values:
        return {}
    drift = round(1.0 - sum(values), DEFAULT_WEIGHT_DECIMALS)
    pivot = max(range(len(values)), key=lambda index: (values[index], -index))
    values[pivot] = round(values[pivot] + drift, DEFAULT_WEIGHT_DECIMALS)
    return {symbol: value for symbol, value in zip(symbols, values)}


def _floor(spec: OptimizationSpec, symbol: str) -> float:
    return float(spec.min_weights.get(symbol, spec.min_weight))


def _ceiling(spec: OptimizationSpec, symbol: str) -> float:
    return float(spec.max_weights.get(symbol, spec.max_weight))


def _hhi_cap(spec: OptimizationSpec) -> float | None:
    caps: list[float] = []
    if spec.max_hhi is not None and spec.max_hhi > 0:
        caps.append(spec.max_hhi)
    if spec.min_effective_n is not None and spec.min_effective_n > 0:
        caps.append(1.0 / spec.min_effective_n)
    if not caps:
        return None
    return min(caps)


def _sector_label(sector: str | None) -> str:
    if isinstance(sector, str) and sector.strip():
        return sector.strip()
    return UNCLASSIFIED_SECTOR


def _sleeve_metrics(
    weights: np.ndarray,
    symbols: Sequence[str],
    sectors: Sequence[str | None],
    mean_returns: np.ndarray,
    covariance: np.ndarray,
    risk_free_rate: float,
) -> SleeveMetrics:
    expected = portfolio_expected_return(weights, mean_returns)
    vol = portfolio_volatility(weights, covariance)
    sharpe = risk_adjusted_return(
        weights, mean_returns, covariance, risk_free_rate=risk_free_rate
    )
    hhi = herfindahl_hirschman_index(weights.tolist())
    effective = effective_n(weights.tolist())
    largest = largest_share(weights.tolist())
    largest_symbol = None
    if largest is not None:
        for symbol, weight in zip(symbols, weights):
            if abs(float(weight) - largest) <= 1e-12:
                largest_symbol = symbol
                break
    grouped = sector_weights(weights.tolist(), sectors) or {}
    diversification = classify_diversification(
        effective_n_value=effective,
        holding_count=len(symbols),
    )
    return SleeveMetrics(
        expected_return=expected,
        volatility=vol,
        risk_adjusted_return=sharpe,
        hhi=hhi,
        effective_n=effective,
        largest_weight=largest,
        largest_symbol=largest_symbol,
        sector_weights=grouped,
        diversification=diversification,
    )


def _metrics_without_moments(
    weights: np.ndarray,
    symbols: Sequence[str],
    sectors: Sequence[str | None],
    risk_free_rate: float,
) -> SleeveMetrics:
    del risk_free_rate
    hhi = herfindahl_hirschman_index(weights.tolist())
    effective = effective_n(weights.tolist())
    largest = largest_share(weights.tolist())
    largest_symbol = None
    if largest is not None:
        for symbol, weight in zip(symbols, weights):
            if abs(float(weight) - largest) <= 1e-12:
                largest_symbol = symbol
                break
    grouped = sector_weights(weights.tolist(), sectors) or {}
    diversification = classify_diversification(
        effective_n_value=effective,
        holding_count=len(symbols),
    )
    return SleeveMetrics(
        expected_return=None,
        volatility=None,
        risk_adjusted_return=None,
        hhi=hhi,
        effective_n=effective,
        largest_weight=largest,
        largest_symbol=largest_symbol,
        sector_weights=grouped,
        diversification=diversification,
    )


def _calculated_metrics(
    current: SleeveMetrics,
    proposed: SleeveMetrics,
    *,
    status: SolverStatus,
    feasible: bool,
    return_observations: int | None,
    periods_per_year: int,
) -> dict[str, Any]:
    return {
        "current": _sleeve_dict(current),
        "proposed": _sleeve_dict(proposed),
        "volatility_change": _delta(proposed.volatility, current.volatility),
        "expected_return_change": _delta(proposed.expected_return, current.expected_return),
        "risk_adjusted_return_change": _delta(
            proposed.risk_adjusted_return, current.risk_adjusted_return
        ),
        "hhi_change": _delta(proposed.hhi, current.hhi),
        "solver_status": status,
        "feasible": feasible,
        "return_observations": return_observations,
        "periods_per_year": periods_per_year,
    }


def _sleeve_dict(metrics: SleeveMetrics) -> dict[str, Any]:
    return {
        "expected_return": metrics.expected_return,
        "volatility": metrics.volatility,
        "risk_adjusted_return": metrics.risk_adjusted_return,
        "hhi": metrics.hhi,
        "effective_n": metrics.effective_n,
        "largest_weight": metrics.largest_weight,
        "largest_symbol": metrics.largest_symbol,
        "sector_weights": metrics.sector_weights,
        "diversification": metrics.diversification,
    }


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _constraint_snapshot(
    spec: OptimizationSpec,
    symbols: Sequence[str],
    sectors: Sequence[str | None],
) -> dict[str, Any]:
    return {
        "objective": spec.objective,
        "min_weight": spec.min_weight,
        "max_weight": spec.max_weight,
        "min_weights": {symbol: _floor(spec, symbol) for symbol in symbols},
        "max_weights": {symbol: _ceiling(spec, symbol) for symbol in symbols},
        "sector_limits": dict(sorted(spec.sector_limits.items())),
        "target_risk": spec.target_risk,
        "min_effective_n": spec.min_effective_n,
        "max_hhi": spec.max_hhi,
        "risk_free_rate": spec.risk_free_rate,
        "long_only": spec.long_only,
        "fully_invested": spec.fully_invested,
        "sectors": {
            symbol: _sector_label(sector) for symbol, sector in zip(symbols, sectors)
        },
    }


def _skipped_result(
    ordered: Sequence[str],
    current_map: dict[str, float],
    spec: OptimizationSpec,
    current_metrics: SleeveMetrics,
    warnings: list[str],
    limitations: list[str],
    *,
    frozen: tuple[str, ...],
) -> OptimizationComputation:
    constraints = _constraint_snapshot(spec, ordered, [None] * len(ordered))
    calculated = _calculated_metrics(
        current_metrics,
        current_metrics,
        status="skipped",
        feasible=False,
        return_observations=None,
        periods_per_year=spec.periods_per_year,
    )
    candidate = CandidateAllocation(
        candidate_id="current",
        label="Current allocation",
        objective="current",
        weights=current_map,
        metrics=current_metrics,
        notes=("Optimization was skipped; the current sleeve is the only candidate.",),
    )
    return OptimizationComputation(
        current_allocation=current_map,
        proposed_allocation=dict(current_map),
        objective=spec.objective,
        constraints=constraints,
        current_metrics=current_metrics,
        proposed_metrics=current_metrics,
        calculated_metrics=calculated,
        candidates=(candidate,),
        warnings=tuple(_unique(warnings)),
        limitations=tuple(_unique(limitations)),
        solver_status="skipped",
        feasible=False,
        optimized_symbols=(),
        frozen_symbols=frozen,
        return_observations=None,
        periods_per_year=spec.periods_per_year,
    )


def _candidate_label(objective: OptimizationObjective) -> str:
    if objective == "risk_adjusted_return":
        return "Risk-adjusted return candidate"
    return "Minimum-volatility candidate"


def _unique(values: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen
