"""Map specialist `AgentOutput` payloads onto compact `InvestmentState` snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.agents.contracts import AgentOutput
from app.agents.manager import (
    FUNDAMENTAL_AGENT,
    MARKET_AGENT,
    OPTIMIZATION_AGENT,
    RISK_AGENT,
)
from app.models.common import DataSourceMetadata
from app.workflow.state import (
    AgentResultSnapshot,
    ExecutionMetadata,
    FundamentalDataSnapshot,
    MarketDataSnapshot,
    OptimizationResultSnapshot,
    RiskAnalysisSnapshot,
)

UTC = timezone.utc


def snapshot_update_from_output(
    output: AgentOutput,
    *,
    current_node: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a partial graph update from one specialist result."""
    observed = now or datetime.now(tz=UTC)
    update: dict[str, Any] = {
        "agent_results": {output.agent: result_snapshot(output)},
        "evidence": list(output.evidence),
        "execution": ExecutionMetadata(
            status="running",
            current_node=current_node,
            invoked_agents=[output.agent],
            updated_at=observed,
            llm_provider=output.llm_provider,
            llm_model=output.llm_model,
            errors=_execution_errors(output),
        ),
    }
    if output.status != "succeeded":
        return update
    if output.agent == MARKET_AGENT:
        market = market_snapshots(output)
        if market:
            update["market_data"] = market
    elif output.agent == FUNDAMENTAL_AGENT:
        fundamentals = fundamental_snapshots(output)
        if fundamentals:
            update["fundamental_data"] = fundamentals
    elif output.agent == RISK_AGENT:
        risk = risk_snapshot(output)
        if risk is not None:
            update["risk_analysis"] = risk
    elif output.agent == OPTIMIZATION_AGENT:
        optimization = optimization_snapshot(output)
        if optimization is not None:
            update["optimization_results"] = optimization
    return update


def result_snapshot(output: AgentOutput) -> AgentResultSnapshot:
    return AgentResultSnapshot(
        agent=output.agent,
        role=output.role,
        status=output.status,
        summary=output.summary,
        findings=list(output.findings),
        confidence=output.confidence,
        error_code=output.error_code,
        error_message=output.error_message,
    )


def market_snapshots(output: AgentOutput) -> dict[str, MarketDataSnapshot]:
    extras = _as_dict(output.extras)
    snapshots: dict[str, MarketDataSnapshot] = {}
    analyses = extras.get("analyses")
    if isinstance(analyses, list) and analyses:
        for item in analyses:
            data = _as_dict(item)
            symbol = data.get("symbol")
            if not symbol:
                continue
            metrics = _as_dict(data.get("supporting_metrics"))
            snapshot = _try_market_snapshot(data, metrics, extras)
            if snapshot is not None:
                snapshots[snapshot.symbol] = snapshot
        return snapshots
    metrics = _as_dict(extras.get("supporting_metrics"))
    snapshot = _try_market_snapshot(extras, metrics, extras)
    if snapshot is not None:
        snapshots[snapshot.symbol] = snapshot
    return snapshots


def fundamental_snapshots(output: AgentOutput) -> dict[str, FundamentalDataSnapshot]:
    extras = _as_dict(output.extras)
    snapshots: dict[str, FundamentalDataSnapshot] = {}
    analyses = extras.get("analyses")
    if isinstance(analyses, list) and analyses:
        for item in analyses:
            data = _as_dict(item)
            symbol = data.get("symbol")
            if not symbol:
                continue
            metrics = _as_dict(data.get("supporting_metrics"))
            snapshot = _try_fundamental_snapshot(data, metrics, extras)
            if snapshot is not None:
                snapshots[snapshot.symbol] = snapshot
        return snapshots
    metrics = _as_dict(extras.get("supporting_metrics"))
    snapshot = _try_fundamental_snapshot(extras, metrics, extras)
    if snapshot is not None:
        snapshots[snapshot.symbol] = snapshot
    return snapshots


def risk_snapshot(output: AgentOutput) -> RiskAnalysisSnapshot | None:
    extras = _as_dict(output.extras)
    metrics = _as_dict(extras.get("risk_metrics"))
    try:
        return RiskAnalysisSnapshot(
            overall_risk_assessment=extras.get("overall_risk_assessment") or output.summary,
            concentration=_as_optional_str(metrics.get("concentration")),
            diversification=_as_optional_str(metrics.get("diversification")),
            weight_basis=_as_optional_str(metrics.get("weight_basis") or extras.get("weight_basis")),
            largest_symbol=_as_optional_str(metrics.get("largest_symbol")),
            largest_weight=_as_float(metrics.get("largest_weight")),
            hhi=_as_float(metrics.get("hhi")),
            portfolio_volatility=_as_float(metrics.get("portfolio_volatility")),
            max_drawdown=_as_float(metrics.get("max_drawdown")),
            major_risks=_as_str_list(extras.get("major_risks")),
            unavailable=_as_str_list(extras.get("unavailable")),
            portfolio_id=_as_optional_str(extras.get("portfolio_id")),
        )
    except (ValidationError, TypeError, ValueError):
        return None


def optimization_snapshot(output: AgentOutput) -> OptimizationResultSnapshot | None:
    extras = _as_dict(output.extras)
    try:
        return OptimizationResultSnapshot(
            objective=_as_optional_str(extras.get("optimization_objective")),
            current_allocation=_as_float_map(extras.get("current_allocation")),
            proposed_allocation=_as_float_map(extras.get("proposed_allocation")),
            feasible=extras.get("feasible") if isinstance(extras.get("feasible"), bool) else None,
            solver_status=_as_optional_str(extras.get("solver_status")),
            warnings=_as_str_list(extras.get("warnings")),
            limitations=_as_str_list(extras.get("limitations")),
        )
    except (ValidationError, TypeError, ValueError):
        return None


def _try_market_snapshot(
    data: Mapping[str, Any],
    metrics: Mapping[str, Any],
    extras: Mapping[str, Any],
) -> MarketDataSnapshot | None:
    symbol = data.get("symbol") or metrics.get("symbol")
    if not symbol:
        return None
    try:
        return MarketDataSnapshot(
            symbol=symbol,
            current_price=_as_float(metrics.get("current_price")),
            currency=_as_optional_str(metrics.get("currency")),
            exchange=_as_optional_str(metrics.get("exchange")),
            change_percent=_as_float(metrics.get("change_percent")),
            volume=_as_float(metrics.get("volume")),
            trend=_as_optional_str(data.get("trend") or extras.get("trend")),
            volatility=_as_float(metrics.get("volatility")),
            momentum=_as_float(metrics.get("momentum")),
            as_of=_as_datetime(data.get("as_of") or metrics.get("quote_timestamp") or extras.get("as_of")),
            unavailable=_as_str_list(data.get("unavailable") or extras.get("unavailable")),
            source=_first_source(data.get("sources") or extras.get("sources")),
        )
    except (ValidationError, TypeError, ValueError):
        return None


def _try_fundamental_snapshot(
    data: Mapping[str, Any],
    metrics: Mapping[str, Any],
    extras: Mapping[str, Any],
) -> FundamentalDataSnapshot | None:
    symbol = data.get("symbol") or metrics.get("symbol")
    if not symbol:
        return None
    latest = _as_dict(metrics.get("latest_reported"))
    current_market = _as_dict(metrics.get("current_market"))
    try:
        return FundamentalDataSnapshot(
            symbol=symbol,
            company_name=_as_optional_str(metrics.get("company_name")),
            sector=_as_optional_str(metrics.get("sector")),
            industry=_as_optional_str(metrics.get("industry")),
            financial_health=_as_optional_str(
                metrics.get("financial_health") or extras.get("financial_health")
            ),
            profitability=_as_optional_str(
                metrics.get("profitability") or extras.get("profitability")
            ),
            revenue=_as_float(latest.get("revenue")),
            earnings=_as_float(latest.get("earnings")),
            pe_ratio=_as_float(current_market.get("pe_ratio")),
            reporting_period=_as_optional_str(
                data.get("reporting_period")
                or latest.get("reporting_period")
                or extras.get("reporting_period")
            ),
            as_of_kind="latest_reported" if latest else None,
            as_of=_as_datetime(
                data.get("timestamp") or extras.get("timestamp") or latest.get("timestamp")
            ),
            unavailable=_as_str_list(data.get("unavailable") or extras.get("unavailable")),
            source=_coerce_source(data.get("source") or extras.get("source"))
            or _first_source(data.get("sources") or extras.get("sources")),
        )
    except (ValidationError, TypeError, ValueError):
        return None


def _execution_errors(output: AgentOutput) -> list[str]:
    if output.status == "failed" and output.error_message:
        return [f"{output.agent}: {output.error_message}"]
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping) and not isinstance(value, (str, bytes)):
        return dict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        payload = dump(mode="json")
        if isinstance(payload, dict):
            return payload
    return {}


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            items.append(text)
    return items


def _as_float_map(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    mapped: dict[str, float] = {}
    for key, item in value.items():
        number = _as_float(item)
        if number is None:
            continue
        mapped[str(key)] = number
    return mapped


def _as_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    return None


def _first_source(value: Any) -> DataSourceMetadata | None:
    if not isinstance(value, list) or not value:
        return None
    return _coerce_source(value[0])


def _coerce_source(value: Any) -> DataSourceMetadata | None:
    if value is None:
        return None
    if isinstance(value, DataSourceMetadata):
        return value
    if isinstance(value, Mapping):
        try:
            return DataSourceMetadata.model_validate(value)
        except ValidationError:
            return None
    return None
