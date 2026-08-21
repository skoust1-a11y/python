"""Portfolio Optimization Agent.

Builds candidate allocations from an uploaded portfolio and retrieved market
history. Numerical optimization runs in Python. The LLM interprets that
structured result and must not choose weights, invent metrics, or issue trades.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, TypeVar

from pydantic import AwareDatetime, Field, ValidationError

from app.agents.base import Agent, AgentMetadata, AgentRuntime
from app.agents.contracts import AgentAnalysis, AgentInput
from app.exceptions import AgentError, ProviderError
from app.models.common import DataSourceMetadata, DomainModel, Evidence
from app.models.fundamentals import CompanyProfile
from app.models.market import MarketQuote, OhlcSeries
from app.models.portfolio import Holding, Portfolio
from app.models.types import FiniteNumber, NonEmptyText, Symbol, UnitInterval, normalize_period, normalize_symbol
from app.providers.contracts import FundamentalDataProvider, MarketDataProvider
from app.tools.optimization import (
    DEFAULT_MAX_WEIGHT,
    DEFAULT_MIN_RETURNS,
    DEFAULT_MIN_WEIGHT,
    DEFAULT_PERIODS_PER_YEAR,
    OptimizationObjective,
    OptimizationSpec,
    SleeveMetrics,
    optimize_portfolio,
)
from app.tools.risk import (
    UNCLASSIFIED_SECTOR,
    WeightBasis,
    close_map,
    resolve_weight_vector,
)

UTC = timezone.utc
T = TypeVar("T")

PRIOR_FUNDAMENTAL_KEY = "fundamental-analysis"
PRIOR_RISK_KEY = "risk-assessment"

SYSTEM_PROMPT = (
    "You are a portfolio-optimization interpreter. You receive a candidate "
    "allocation already computed in Python from an uploaded portfolio and "
    "retrieved market history. Interpret only that evidence. "
    "Do not invent weights, expected returns, volatilities, HHI values, or "
    "other figures. Do not change the proposed allocation. "
    "If a field is null or listed as unavailable, treat it as missing and say so. "
    "The proposed sleeve is a candidate for a later Manager Agent to evaluate; "
    "it is not a trade, order, or executed rebalance. "
    "Do not recommend brokerage actions or fill in missing prices from outside knowledge."
)

OBJECTIVES: tuple[OptimizationObjective, ...] = (
    "minimum_volatility",
    "risk_adjusted_return",
)


class PositionAllocation(DomainModel):
    """Current versus proposed weight for one holding."""

    symbol: Symbol
    current_weight: UnitInterval | None = None
    proposed_weight: UnitInterval | None = None
    weight_change: FiniteNumber | None = None
    sector: str | None = None
    optimized: bool = True


class OptimizationInterpretation(DomainModel):
    """LLM reading of the optimizer result. Must not introduce new figures."""

    allocation_assessment: NonEmptyText
    comparison_findings: list[NonEmptyText] = Field(default_factory=list)
    constraint_findings: list[NonEmptyText] = Field(default_factory=list)
    manager_notes: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)
    confidence: UnitInterval


class OptimizationAgentExtras(DomainModel):
    """Structured payload stored on `AgentOutput.extras`."""

    current_allocation: dict[str, float]
    proposed_allocation: dict[str, float]
    optimization_objective: OptimizationObjective
    constraints: dict[str, Any]
    calculated_metrics: dict[str, Any]
    warnings: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)
    candidate_allocations: list[dict[str, Any]] = Field(default_factory=list)
    positions: list[PositionAllocation] = Field(default_factory=list)
    allocation_assessment: NonEmptyText
    comparison_findings: list[NonEmptyText] = Field(default_factory=list)
    constraint_findings: list[NonEmptyText] = Field(default_factory=list)
    manager_notes: list[NonEmptyText] = Field(default_factory=list)
    solver_status: NonEmptyText
    feasible: bool
    weight_basis: WeightBasis
    as_of: AwareDatetime | None = None
    analyzed_at: AwareDatetime
    sources: list[DataSourceMetadata] = Field(default_factory=list)
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    market_data_provider: NonEmptyText
    fundamental_data_provider: NonEmptyText
    interval: NonEmptyText
    portfolio_id: str | None = None
    trade_execution: Literal["not_implemented"] = "not_implemented"


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
    unavailable: list[str] = field(default_factory=list)


class PortfolioOptimizationAgent(Agent):
    """Specialist that proposes candidate allocations without executing trades."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="portfolio-optimization",
            role="portfolio-optimizer",
            description=(
                "Produces deterministic candidate allocations from uploaded holdings "
                "and retrieved market history using a bounded mean-variance optimizer. "
                "Does not execute trades."
            ),
        )

    def analyze(self, payload: AgentInput, runtime: AgentRuntime) -> AgentAnalysis:
        portfolio = _portfolio_from_extras(payload.extras)
        spec = _spec_from_extras(payload.extras)
        interval = _interval_from_extras(payload.extras)
        start, end = _history_bounds(payload.extras)
        prior_evidence = _prior_evidence_from_extras(payload.extras)

        snapshot = _load_portfolio(
            runtime.providers.market_data,
            runtime.providers.fundamentals,
            portfolio,
            start=start,
            end=end,
            interval=interval,
            prior_evidence=prior_evidence,
        )
        weights, basis, mixed_currency = _current_weights(snapshot)
        symbols = [item.holding.symbol for item in snapshot.holdings]
        sectors = [item.sector for item in snapshot.holdings]
        closes_by_symbol = {
            item.holding.symbol: close_map(item.history)
            for item in snapshot.holdings
            if item.history is not None and item.history.prices
        }
        computation = optimize_portfolio(
            symbols=symbols,
            current_weights=weights,
            closes_by_symbol=closes_by_symbol,
            sectors=sectors,
            spec=spec,
        )
        unavailable = _unavailable(snapshot, mixed_currency, basis, computation.frozen_symbols)
        sources = _sources(snapshot)
        as_of = _as_of(snapshot)
        _record_evidence(runtime, computation, snapshot, sources, as_of)

        interpretation = runtime.complete_structured(
            _interpretation_prompt(payload, computation, basis, unavailable),
            OptimizationInterpretation,
            system=SYSTEM_PROMPT,
            metadata={"task": "optimization-interpretation"},
        )
        extras_model = _build_extras(
            interpretation,
            computation,
            snapshot,
            positions=_positions(snapshot, computation),
            basis=basis,
            unavailable=unavailable,
            sources=sources,
            as_of=as_of,
            interval=interval,
            provider_name=runtime.providers.market_data.name,
            fundamental_provider_name=runtime.providers.fundamentals.name,
        )
        return AgentAnalysis(
            summary=extras_model.allocation_assessment,
            findings=_findings(extras_model),
            evidence=runtime.evidence.items(),
            confidence=_capped_confidence(
                interpretation.confidence,
                extras_model.unavailable,
                extras_model.feasible,
                extras_model.weight_basis,
            ),
            extras=extras_model.model_dump(mode="json"),
        )


def _portfolio_from_extras(extras: dict[str, Any]) -> Portfolio:
    raw = extras.get("portfolio")
    if raw is None:
        raise AgentError("Portfolio optimization requires uploaded portfolio data.")
    if isinstance(raw, Portfolio):
        return raw
    if isinstance(raw, dict):
        try:
            return Portfolio.model_validate(_portable_portfolio_payload(raw))
        except ValidationError as exc:
            raise AgentError("portfolio extras must be a confirmed Portfolio payload.") from exc
    raise AgentError("portfolio extras must be a confirmed Portfolio payload.")


def _portable_portfolio_payload(raw: dict[str, Any]) -> dict[str, Any]:
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


def _spec_from_extras(extras: dict[str, Any]) -> OptimizationSpec:
    objective = _objective_from_extras(extras)
    min_weight = _unit_interval(extras, "min_weight", DEFAULT_MIN_WEIGHT, allow_zero=True)
    max_weight = _unit_interval(extras, "max_weight", DEFAULT_MAX_WEIGHT, allow_zero=False)
    if min_weight > max_weight:
        raise AgentError("min_weight must be less than or equal to max_weight.")
    min_returns = _positive_int(extras, "min_volatility_returns", DEFAULT_MIN_RETURNS)
    if min_returns < 2:
        raise AgentError("min_volatility_returns must be at least 2.")
    return OptimizationSpec(
        objective=objective,
        min_weight=min_weight,
        max_weight=max_weight,
        min_weights=_weight_overrides(extras, "min_weights"),
        max_weights=_weight_overrides(extras, "max_weights"),
        sector_limits=_sector_limits(extras),
        target_risk=_optional_positive_float(extras, "target_risk"),
        min_effective_n=_optional_positive_float(extras, "min_effective_n"),
        max_hhi=_optional_unit_interval(extras, "max_hhi"),
        risk_free_rate=_optional_finite_float(extras, "risk_free_rate", 0.0),
        periods_per_year=_positive_int(extras, "periods_per_year", DEFAULT_PERIODS_PER_YEAR),
        min_returns=min_returns,
    )


def _objective_from_extras(extras: dict[str, Any]) -> OptimizationObjective:
    raw = extras.get("optimization_objective", extras.get("objective", "minimum_volatility"))
    if raw is None or raw == "":
        return "minimum_volatility"
    if not isinstance(raw, str):
        raise AgentError("optimization_objective must be a string.")
    value = raw.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "min_volatility": "minimum_volatility",
        "minimum_vol": "minimum_volatility",
        "min_vol": "minimum_volatility",
        "sharpe": "risk_adjusted_return",
        "risk_adjusted": "risk_adjusted_return",
        "risk_adjusted_returns": "risk_adjusted_return",
    }
    value = aliases.get(value, value)
    if value not in OBJECTIVES:
        raise AgentError(
            "optimization_objective must be minimum_volatility or risk_adjusted_return."
        )
    return value  # type: ignore[return-value]


def _weight_overrides(extras: dict[str, Any], key: str) -> dict[str, float]:
    raw = extras.get(key)
    if raw is None or raw == {}:
        return {}
    if not isinstance(raw, Mapping):
        raise AgentError(f"{key} must be a mapping of symbol to weight.")
    parsed: dict[str, float] = {}
    for symbol, value in raw.items():
        try:
            token = normalize_symbol(str(symbol))
            weight = float(value)
        except (TypeError, ValueError) as exc:
            raise AgentError(f"{key} must map symbols to weights between 0 and 1.") from exc
        if not 0 <= weight <= 1:
            raise AgentError(f"{key} must map symbols to weights between 0 and 1.")
        parsed[token] = weight
    return parsed


def _sector_limits(extras: dict[str, Any]) -> dict[str, float]:
    raw = extras.get("sector_limits")
    if raw is None or raw == {}:
        return {}
    if not isinstance(raw, Mapping):
        raise AgentError("sector_limits must be a mapping of sector to maximum weight.")
    parsed: dict[str, float] = {}
    for sector, value in raw.items():
        if not isinstance(sector, str) or not sector.strip():
            raise AgentError("sector_limits keys must be sector names.")
        try:
            weight = float(value)
        except (TypeError, ValueError) as exc:
            raise AgentError("sector_limits values must be weights between 0 and 1.") from exc
        if not 0 < weight <= 1:
            raise AgentError("sector_limits values must be weights between 0 and 1.")
        parsed[sector.strip()] = weight
    return parsed


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


def _unit_interval(
    extras: dict[str, Any],
    key: str,
    default: float,
    *,
    allow_zero: bool,
) -> float:
    if key not in extras or extras[key] is None:
        return default
    try:
        value = float(extras[key])
    except (TypeError, ValueError) as exc:
        raise AgentError(f"{key} must be a number between 0 and 1.") from exc
    if not math.isfinite(value) or value < 0 or value > 1 or (not allow_zero and value <= 0):
        raise AgentError(f"{key} must be a number between 0 and 1.")
    return value


def _optional_unit_interval(extras: dict[str, Any], key: str) -> float | None:
    if key not in extras or extras[key] is None or extras[key] == "":
        return None
    return _unit_interval(extras, key, 1.0, allow_zero=False)


def _optional_positive_float(extras: dict[str, Any], key: str) -> float | None:
    if key not in extras or extras[key] is None or extras[key] == "":
        return None
    try:
        value = float(extras[key])
    except (TypeError, ValueError) as exc:
        raise AgentError(f"{key} must be a positive number.") from exc
    if value <= 0 or not math.isfinite(value):
        raise AgentError(f"{key} must be a positive number.")
    return value


def _optional_finite_float(extras: dict[str, Any], key: str, default: float) -> float:
    if key not in extras or extras[key] is None or extras[key] == "":
        return default
    try:
        value = float(extras[key])
    except (TypeError, ValueError) as exc:
        raise AgentError(f"{key} must be a finite number.") from exc
    if not math.isfinite(value):
        raise AgentError(f"{key} must be a finite number.")
    return value


def _interval_from_extras(extras: dict[str, Any]) -> str:
    raw = extras.get("interval", "1d")
    if not isinstance(raw, str) or not raw.strip():
        raise AgentError("interval must be a non-empty period token.")
    try:
        return normalize_period(raw)
    except ValueError as exc:
        raise AgentError("interval must be a non-empty period token.") from exc


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
    for key in (PRIOR_FUNDAMENTAL_KEY, PRIOR_RISK_KEY):
        artifact = extras.get(key)
        if isinstance(artifact, dict) and artifact:
            prior[key] = artifact
    return prior


def _load_portfolio(
    market: MarketDataProvider,
    fundamentals: FundamentalDataProvider,
    portfolio: Portfolio,
    *,
    start: datetime | None,
    end: datetime | None,
    interval: str,
    prior_evidence: Mapping[str, Any],
) -> _PortfolioSnapshot:
    holdings: list[_HoldingSnapshot] = []
    unavailable: list[str] = []
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
        unavailable.extend(f"{label}:{holding.symbol}" for label in snapshot.unavailable)
    return _PortfolioSnapshot(
        portfolio=portfolio,
        holdings=holdings,
        unavailable=_unique(unavailable),
    )


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


def _sector_from_prior(prior_evidence: Mapping[str, Any], symbol: str) -> str | None:
    artifact = prior_evidence.get(PRIOR_FUNDAMENTAL_KEY)
    if not isinstance(artifact, dict):
        return None
    extras = artifact.get("extras")
    if not isinstance(extras, dict):
        extras = artifact
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
    return None


def _fetch(operation: Callable[[], T], unavailable: list[str], label: str) -> T | None:
    try:
        return operation()
    except ProviderError:
        unavailable.append(label)
        return None


def _current_weights(
    snapshot: _PortfolioSnapshot,
) -> tuple[list[float], WeightBasis, bool]:
    mixed_currency = _mixed_currency(snapshot.holdings)
    market_values: list[float | None] = []
    uploaded: list[float | None] = []
    cost_values: list[float | None] = []
    for item in snapshot.holdings:
        price = item.quote.value if item.quote is not None else None
        market_values.append(item.holding.quantity * price if price is not None else None)
        uploaded.append(item.holding.weight)
        cost_values.append(item.holding.cost_value)
    weights, basis = resolve_weight_vector(
        market_values=market_values,
        uploaded_weights=uploaded,
        cost_values=cost_values,
        mixed_currency=mixed_currency,
    )
    if weights is None:
        equal = 1.0 / len(snapshot.holdings) if snapshot.holdings else 0.0
        return [equal] * len(snapshot.holdings), "insufficient_data", mixed_currency
    return weights, basis, mixed_currency


def _mixed_currency(holdings: Sequence[_HoldingSnapshot]) -> bool:
    currencies: set[str] = set()
    for item in holdings:
        for value in (
            item.holding.currency,
            item.quote.currency if item.quote is not None else None,
            item.profile.currency if item.profile is not None else None,
        ):
            if value:
                currencies.add(value)
    return len(currencies) > 1


def _unavailable(
    snapshot: _PortfolioSnapshot,
    mixed_currency: bool,
    basis: WeightBasis,
    frozen: Sequence[str],
) -> list[str]:
    labels = list(snapshot.unavailable)
    if mixed_currency:
        labels.append("fx_conversion")
    if basis != "market_value":
        labels.append("market_value_weights")
    if frozen:
        labels.append("complete_price_history")
    return _unique(labels)


def _sources(snapshot: _PortfolioSnapshot) -> list[DataSourceMetadata]:
    seen: list[DataSourceMetadata] = []
    keys: set[str] = set()
    for item in snapshot.holdings:
        for payload in (item.quote, item.history, item.profile):
            source = getattr(payload, "source", None)
            if source is None:
                continue
            key = source.model_dump_json()
            if key not in keys:
                keys.add(key)
                seen.append(source)
    return seen


def _as_of(snapshot: _PortfolioSnapshot) -> datetime | None:
    timestamps = [
        item.quote.timestamp
        for item in snapshot.holdings
        if item.quote is not None
    ]
    return max(timestamps) if timestamps else None


def _positions(
    snapshot: _PortfolioSnapshot,
    computation: Any,
) -> list[PositionAllocation]:
    current = computation.current_allocation
    proposed = computation.proposed_allocation
    frozen = set(computation.frozen_symbols)
    rows: list[PositionAllocation] = []
    for item in snapshot.holdings:
        symbol = item.holding.symbol
        current_weight = current.get(symbol)
        proposed_weight = proposed.get(symbol)
        change = None
        if current_weight is not None and proposed_weight is not None:
            change = proposed_weight - current_weight
        rows.append(
            PositionAllocation(
                symbol=symbol,
                current_weight=current_weight,
                proposed_weight=proposed_weight,
                weight_change=change,
                sector=item.sector or UNCLASSIFIED_SECTOR,
                optimized=symbol not in frozen,
            )
        )
    return rows


def _record_evidence(
    runtime: AgentRuntime,
    computation: Any,
    snapshot: _PortfolioSnapshot,
    sources: Sequence[DataSourceMetadata],
    as_of: datetime | None,
) -> None:
    derived = DataSourceMetadata(
        provider="portfolio-optimization",
        source="deterministic-optimizer",
        timestamp=as_of or datetime.now(tz=UTC),
        raw_reference=computation.objective,
    )
    runtime.evidence.add(
        Evidence(
            source=derived,
            field="optimization_objective",
            value=computation.objective,
        )
    )
    runtime.evidence.add(
        Evidence(
            source=derived,
            field="solver_status",
            value=computation.solver_status,
        )
    )
    proposed_vol = computation.proposed_metrics.volatility
    if proposed_vol is not None:
        runtime.evidence.add(
            Evidence(source=derived, field="proposed_volatility", value=proposed_vol)
        )
    current_vol = computation.current_metrics.volatility
    if current_vol is not None:
        runtime.evidence.add(
            Evidence(source=derived, field="current_volatility", value=current_vol)
        )
    for symbol, weight in computation.proposed_allocation.items():
        runtime.evidence.add(
            Evidence(
                source=derived,
                symbol=symbol,
                field="proposed_weight",
                value=weight,
            )
        )
    for symbol, weight in computation.current_allocation.items():
        runtime.evidence.add(
            Evidence(
                source=derived,
                symbol=symbol,
                field="current_weight",
                value=weight,
            )
        )
    if sources:
        runtime.evidence.add(
            Evidence(
                source=sources[0],
                field="market_history",
                value=len(sources),
            )
        )


def _build_extras(
    interpretation: OptimizationInterpretation,
    computation: Any,
    snapshot: _PortfolioSnapshot,
    *,
    positions: list[PositionAllocation],
    basis: WeightBasis,
    unavailable: Sequence[str],
    sources: Sequence[DataSourceMetadata],
    as_of: datetime | None,
    interval: str,
    provider_name: str,
    fundamental_provider_name: str,
) -> OptimizationAgentExtras:
    warnings = list(computation.warnings)
    if unavailable:
        gap = "Unavailable inputs were not estimated: " + ", ".join(unavailable) + "."
        if gap not in warnings:
            warnings.append(gap)
    limitations = _unique([*computation.limitations, *interpretation.limitations])
    candidates = [
        {
            "candidate_id": item.candidate_id,
            "label": item.label,
            "objective": item.objective,
            "weights": item.weights,
            "metrics": _sleeve_payload(item.metrics),
            "notes": list(item.notes),
        }
        for item in computation.candidates
    ]
    return OptimizationAgentExtras(
        current_allocation=computation.current_allocation,
        proposed_allocation=computation.proposed_allocation,
        optimization_objective=computation.objective,
        constraints=computation.constraints,
        calculated_metrics=computation.calculated_metrics,
        warnings=_unique(warnings),
        limitations=limitations,
        candidate_allocations=candidates,
        positions=positions,
        allocation_assessment=interpretation.allocation_assessment,
        comparison_findings=list(interpretation.comparison_findings),
        constraint_findings=list(interpretation.constraint_findings),
        manager_notes=list(interpretation.manager_notes),
        solver_status=computation.solver_status,
        feasible=computation.feasible,
        weight_basis=basis,
        as_of=as_of,
        analyzed_at=datetime.now(tz=UTC),
        sources=list(sources),
        unavailable=list(unavailable),
        market_data_provider=provider_name,
        fundamental_data_provider=fundamental_provider_name,
        interval=interval,
        portfolio_id=snapshot.portfolio.id,
    )


def _sleeve_payload(metrics: SleeveMetrics) -> dict[str, Any]:
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


def _findings(extras: OptimizationAgentExtras) -> list[str]:
    findings: list[str] = []
    findings.extend(extras.comparison_findings)
    findings.extend(extras.constraint_findings)
    findings.extend(extras.manager_notes)
    return findings


def _interpretation_prompt(
    payload: AgentInput,
    computation: Any,
    basis: WeightBasis,
    unavailable: Sequence[str],
) -> str:
    bundle = {
        "request_id": payload.request_id,
        "question": payload.question,
        "symbols": payload.symbols,
        "weight_basis": basis,
        "unavailable": list(unavailable),
        "computed": {
            "current_allocation": computation.current_allocation,
            "proposed_allocation": computation.proposed_allocation,
            "optimization_objective": computation.objective,
            "constraints": computation.constraints,
            "calculated_metrics": computation.calculated_metrics,
            "warnings": list(computation.warnings),
            "limitations": list(computation.limitations),
            "candidate_allocations": [
                {
                    "candidate_id": item.candidate_id,
                    "label": item.label,
                    "objective": item.objective,
                    "weights": item.weights,
                    "notes": list(item.notes),
                }
                for item in computation.candidates
            ],
            "solver_status": computation.solver_status,
            "feasible": computation.feasible,
            "trade_execution": "not_implemented",
        },
        "rules": [
            "Numeric values were calculated by the Python optimizer from uploaded holdings and retrieved market data.",
            "Null fields and unavailable lists are missing. Do not fill them in.",
            "Do not cite weights or metrics that are not in this payload.",
            "Do not treat the proposed allocation as a trade or executed rebalance.",
        ],
    }
    return (
        "Interpret the following portfolio-optimization evidence and return "
        "allocation_assessment, comparison_findings, constraint_findings, "
        "manager_notes, limitations, and confidence.\n\n"
        + json.dumps(bundle, indent=2, default=str)
    )


def _capped_confidence(
    confidence: float,
    unavailable: Sequence[str],
    feasible: bool,
    weight_basis: WeightBasis,
) -> float:
    capped = confidence
    if not feasible:
        capped = min(capped, 0.4)
    if "complete_price_history" in unavailable:
        capped = min(capped, 0.55)
    if weight_basis != "market_value":
        capped = min(capped, 0.6)
    if weight_basis == "insufficient_data":
        capped = min(capped, 0.35)
    return capped


def _unique(values: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen
