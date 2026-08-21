"""Shared LangGraph state schema.

`InvestmentState` is the graph payload. Nodes return partial updates; reducers
merge them so later specialists do not overwrite unrelated fields.

Compact snapshots are stored instead of raw OHLC bars, financial-statement
line items, news bodies, or vendor extras. `BoardState` remains the temporary
agent-wrapper contract until the workflow is compiled.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Annotated, Any, Literal, NotRequired, TypedDict, get_args, get_origin, get_type_hints

from pydantic import AwareDatetime, Field

from app.models.common import DataSourceMetadata, DomainModel, Evidence
from app.models.portfolio import Portfolio
from app.models.types import (
    CurrencyCode,
    Headline,
    HttpUrlString,
    NonEmptyText,
    NonNegativeFinite,
    Symbol,
    UnitInterval,
)

AnalysisType = Literal[
    "stock_analysis",
    "portfolio_risk",
    "portfolio_review",
    "portfolio_rebalancing",
]
RiskTolerance = Literal["conservative", "moderate", "aggressive"]
InvestmentHorizon = Literal["short", "medium", "long"]
WorkflowStatus = Literal["pending", "running", "completed", "failed"]
ConflictSeverity = Literal["info", "warning", "error"]
CritiqueCategory = Literal[
    "missing_evidence",
    "unsupported_recommendation",
    "agent_disagreement",
    "missing_analysis",
    "stale_or_unavailable_data",
    "constraint_violation",
]
CritiqueSeverity = Literal["info", "warning", "critical"]
AgentRunStatus = Literal["succeeded", "failed"]
AsOfKind = Literal["latest_reported", "historical", "current_market"]

Reducer = Callable[[Any, Any], Any]


class UserRequest(DomainModel):
    """Normalized user question that started the graph run."""

    text: NonEmptyText
    symbols: list[Symbol] = Field(default_factory=list)
    analysis_type: AnalysisType | None = None
    portfolio_id: str | None = None


class InvestmentProfile(DomainModel):
    """Optional investor constraints. Missing fields stay unset."""

    risk_tolerance: RiskTolerance | None = None
    horizon: InvestmentHorizon | None = None
    objective: str | None = None
    base_currency: CurrencyCode | None = None
    constraints: list[NonEmptyText] = Field(default_factory=list)


class SelectedStock(DomainModel):
    """Focus instrument for single-name analysis. Not a quote payload."""

    symbol: Symbol
    name: str | None = None


class MarketDataSnapshot(DomainModel):
    """Compact market facts. Historical bars are not stored on graph state."""

    symbol: Symbol
    current_price: float | None = None
    currency: str | None = None
    exchange: str | None = None
    change_percent: float | None = None
    volume: float | None = None
    trend: str | None = None
    volatility: float | None = None
    momentum: float | None = None
    as_of: AwareDatetime | None = None
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    source: DataSourceMetadata | None = None


class FundamentalDataSnapshot(DomainModel):
    """Compact fundamentals. Statement line items are not stored on graph state."""

    symbol: Symbol
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    financial_health: str | None = None
    profitability: str | None = None
    revenue: float | None = None
    earnings: float | None = None
    pe_ratio: float | None = None
    reporting_period: str | None = None
    as_of_kind: AsOfKind | None = None
    as_of: AwareDatetime | None = None
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    source: DataSourceMetadata | None = None


class NewsSnapshot(DomainModel):
    """Headline-level news. Article bodies and vendor extras are omitted."""

    headline: Headline
    timestamp: AwareDatetime
    source: DataSourceMetadata
    publisher: str | None = None
    symbol: Symbol | None = None
    url: HttpUrlString | None = None


class AgentResultSnapshot(DomainModel):
    """Compact specialist result. Shared evidence lives on `evidence`."""

    agent: NonEmptyText
    role: NonEmptyText
    status: AgentRunStatus
    summary: NonEmptyText
    findings: list[NonEmptyText] = Field(default_factory=list)
    confidence: UnitInterval | None = None
    error_code: str | None = None
    error_message: str | None = None


class RiskAnalysisSnapshot(DomainModel):
    """Portfolio-risk summary without pairwise matrices or price history."""

    overall_risk_assessment: NonEmptyText | None = None
    concentration: str | None = None
    diversification: str | None = None
    weight_basis: str | None = None
    largest_symbol: str | None = None
    largest_weight: float | None = None
    hhi: float | None = None
    portfolio_volatility: float | None = None
    max_drawdown: float | None = None
    major_risks: list[NonEmptyText] = Field(default_factory=list)
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    portfolio_id: str | None = None


class OptimizationResultSnapshot(DomainModel):
    """Candidate allocation produced in Python. Not a trade or order."""

    objective: str | None = None
    current_allocation: dict[str, float] = Field(default_factory=dict)
    proposed_allocation: dict[str, float] = Field(default_factory=dict)
    feasible: bool | None = None
    solver_status: str | None = None
    warnings: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)
    trade_execution: Literal["not_implemented"] = "not_implemented"


class ConflictRecord(DomainModel):
    """Disagreement or gap detected across specialist outputs."""

    description: NonEmptyText
    agents: list[NonEmptyText] = Field(default_factory=list)
    severity: ConflictSeverity = "warning"


class CritiqueRecord(DomainModel):
    """Structured reviewer finding. No hidden reasoning payload."""

    author: NonEmptyText
    message: NonEmptyText
    target: str | None = None
    category: CritiqueCategory | None = None
    severity: CritiqueSeverity = "warning"
    resolved: bool = False


class FinalRecommendation(DomainModel):
    """Manager synthesis written back to graph state. Trades are never executed."""

    summary: NonEmptyText
    recommendation: NonEmptyText
    findings: list[NonEmptyText] = Field(default_factory=list)
    risks: list[NonEmptyText] = Field(default_factory=list)
    assumptions: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)
    confidence: UnitInterval | None = None
    trade_execution: Literal["not_implemented"] = "not_implemented"


class ExecutionMetadata(DomainModel):
    """Run-level bookkeeping. `None` fields mean “leave unchanged” on merge."""

    status: WorkflowStatus | None = None
    current_node: str | None = None
    requested_agents: list[NonEmptyText] = Field(default_factory=list)
    invoked_agents: list[NonEmptyText] = Field(default_factory=list)
    started_at: AwareDatetime | None = None
    updated_at: AwareDatetime | None = None
    duration_ms: NonNegativeFinite | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    reflection_cycle: int | None = None
    errors: list[NonEmptyText] = Field(default_factory=list)


def last_value(current: Any, incoming: Any) -> Any:
    """Replace the current field with the node update."""
    return incoming


def merge_market_data(
    current: Mapping[str, Any] | None,
    incoming: Mapping[str, Any] | None,
) -> dict[str, MarketDataSnapshot]:
    """Merge per-symbol market snapshots. The same symbol is overwritten."""
    return _merge_symbol_snapshots(MarketDataSnapshot, current, incoming)


def merge_fundamental_data(
    current: Mapping[str, Any] | None,
    incoming: Mapping[str, Any] | None,
) -> dict[str, FundamentalDataSnapshot]:
    """Merge per-symbol fundamental snapshots. The same symbol is overwritten."""
    return _merge_symbol_snapshots(FundamentalDataSnapshot, current, incoming)


def merge_agent_results(
    current: Mapping[str, Any] | None,
    incoming: Mapping[str, Any] | None,
) -> dict[str, AgentResultSnapshot]:
    """Merge specialist results keyed by agent name. Later results win."""
    merged: dict[str, AgentResultSnapshot] = {}
    for mapping in (current, incoming):
        if not mapping:
            continue
        for key, value in mapping.items():
            snapshot = _coerce(AgentResultSnapshot, value)
            merged[snapshot.agent or str(key)] = snapshot
    return merged


def append_news(
    current: Sequence[Any] | None,
    incoming: Sequence[Any] | None,
) -> list[NewsSnapshot]:
    """Append headline snapshots, skipping identical items."""
    return _append_unique(
        NewsSnapshot,
        current,
        incoming,
        key=lambda item: (item.headline, item.timestamp.isoformat(), item.symbol),
    )


def append_conflicts(
    current: Sequence[Any] | None,
    incoming: Sequence[Any] | None,
) -> list[ConflictRecord]:
    """Append conflict notes, skipping identical descriptions."""
    return _append_unique(
        ConflictRecord,
        current,
        incoming,
        key=lambda item: (item.description, tuple(item.agents), item.severity),
    )


def append_critiques(
    current: Sequence[Any] | None,
    incoming: Sequence[Any] | None,
) -> list[CritiqueRecord]:
    """Append critiques. A later note with the same identity may mark resolved."""
    items = _coerce_all(CritiqueRecord, current)
    index = {
        (item.author, item.target, item.category, item.message): position
        for position, item in enumerate(items)
    }
    for item in _coerce_all(CritiqueRecord, incoming):
        key = (item.author, item.target, item.category, item.message)
        if key in index:
            items[index[key]] = item
        else:
            index[key] = len(items)
            items.append(item)
    return items


def append_evidence(
    current: Sequence[Any] | None,
    incoming: Sequence[Any] | None,
) -> list[Evidence]:
    """Append citable facts, skipping identical payloads."""
    return _append_unique(
        Evidence,
        current,
        incoming,
        key=lambda item: item.model_dump_json(),
    )


def merge_execution(
    current: ExecutionMetadata | Mapping[str, Any] | None,
    incoming: ExecutionMetadata | Mapping[str, Any] | None,
) -> ExecutionMetadata | None:
    """Merge run metadata. Lists accumulate; other set fields overwrite."""
    if incoming is None:
        return _coerce(ExecutionMetadata, current) if current is not None else None
    if current is None:
        return _coerce(ExecutionMetadata, incoming)
    left = _coerce(ExecutionMetadata, current)
    right = _coerce(ExecutionMetadata, incoming)
    return ExecutionMetadata(
        status=right.status if right.status is not None else left.status,
        current_node=(
            right.current_node if right.current_node is not None else left.current_node
        ),
        requested_agents=_unique_text(
            [*left.requested_agents, *right.requested_agents]
        ),
        invoked_agents=_unique_text([*left.invoked_agents, *right.invoked_agents]),
        started_at=left.started_at or right.started_at,
        updated_at=right.updated_at or left.updated_at,
        duration_ms=(
            right.duration_ms if right.duration_ms is not None else left.duration_ms
        ),
        llm_provider=right.llm_provider or left.llm_provider,
        llm_model=right.llm_model or left.llm_model,
        reflection_cycle=(
            right.reflection_cycle
            if right.reflection_cycle is not None
            else left.reflection_cycle
        ),
        errors=_unique_text([*left.errors, *right.errors]),
    )


class BoardState(TypedDict):
    """Stateful graph payload shared by current agent-wrapper tests."""

    request_id: str
    messages: list[dict[str, Any]]
    artifacts: NotRequired[dict[str, Any]]
    errors: NotRequired[list[str]]


class InvestmentState(TypedDict, total=False):
    """LangGraph state for the investment strategy board.

    Nodes return a subset of these keys. Annotated fields use reducers so
    incremental updates accumulate instead of replacing the whole payload.
    """

    request_id: str
    user_request: UserRequest
    investment_profile: InvestmentProfile
    portfolio: Portfolio | None
    selected_stock: SelectedStock | None
    market_data: Annotated[dict[str, MarketDataSnapshot], merge_market_data]
    fundamental_data: Annotated[dict[str, FundamentalDataSnapshot], merge_fundamental_data]
    news: Annotated[list[NewsSnapshot], append_news]
    agent_results: Annotated[dict[str, AgentResultSnapshot], merge_agent_results]
    risk_analysis: RiskAnalysisSnapshot | None
    optimization_results: OptimizationResultSnapshot | None
    conflicts: Annotated[list[ConflictRecord], append_conflicts]
    critiques: Annotated[list[CritiqueRecord], append_critiques]
    evidence: Annotated[list[Evidence], append_evidence]
    final_recommendation: FinalRecommendation | None
    execution: Annotated[ExecutionMetadata, merge_execution]


INVESTMENT_STATE_REDUCERS: dict[str, Reducer] = {
    "market_data": merge_market_data,
    "fundamental_data": merge_fundamental_data,
    "news": append_news,
    "agent_results": merge_agent_results,
    "conflicts": append_conflicts,
    "critiques": append_critiques,
    "evidence": append_evidence,
    "execution": merge_execution,
}

OVERWRITE_MODELS: dict[str, type[DomainModel]] = {
    "user_request": UserRequest,
    "investment_profile": InvestmentProfile,
    "selected_stock": SelectedStock,
    "risk_analysis": RiskAnalysisSnapshot,
    "optimization_results": OptimizationResultSnapshot,
    "final_recommendation": FinalRecommendation,
}


def create_investment_state(
    request_id: str,
    *,
    user_request: UserRequest | None = None,
    investment_profile: InvestmentProfile | None = None,
    portfolio: Portfolio | None = None,
    selected_stock: SelectedStock | None = None,
) -> InvestmentState:
    """Build a graph state with empty accumulators ready for node updates."""
    token = request_id.strip()
    if not token:
        raise ValueError("request_id is required")
    state: InvestmentState = {
        "request_id": token,
        "market_data": {},
        "fundamental_data": {},
        "news": [],
        "agent_results": {},
        "conflicts": [],
        "critiques": [],
        "evidence": [],
        "execution": ExecutionMetadata(status="pending"),
    }
    if user_request is not None:
        state["user_request"] = user_request
    if investment_profile is not None:
        state["investment_profile"] = investment_profile
    if portfolio is not None:
        state["portfolio"] = portfolio
    if selected_stock is not None:
        state["selected_stock"] = selected_stock
    return state


def merge_investment_state(
    current: InvestmentState | Mapping[str, Any],
    update: InvestmentState | Mapping[str, Any],
) -> InvestmentState:
    """Apply a partial node update using the same reducers LangGraph will use."""
    merged: dict[str, Any] = dict(current)
    for key, value in dict(update).items():
        reducer = INVESTMENT_STATE_REDUCERS.get(key)
        if reducer is None:
            merged[key] = last_value(merged.get(key), _coerce_overwrite(key, value))
        else:
            merged[key] = reducer(merged.get(key), value)
    return merged  # type: ignore[return-value]


def _merge_symbol_snapshots(
    model_cls: type[DomainModel],
    current: Mapping[str, Any] | None,
    incoming: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for mapping in (current, incoming):
        if not mapping:
            continue
        for value in mapping.values():
            snapshot = _coerce(model_cls, value)
            merged[str(getattr(snapshot, "symbol"))] = snapshot
    return merged


def _append_unique(
    model_cls: type[DomainModel],
    current: Sequence[Any] | None,
    incoming: Sequence[Any] | None,
    *,
    key: Callable[[Any], Any],
) -> list[Any]:
    items = _coerce_all(model_cls, current)
    seen = {key(item) for item in items}
    for item in _coerce_all(model_cls, incoming):
        token = key(item)
        if token in seen:
            continue
        seen.add(token)
        items.append(item)
    return items


def _coerce_overwrite(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field == "portfolio":
        return _coerce_portfolio(value)
    model_cls = OVERWRITE_MODELS.get(field)
    if model_cls is None:
        return value
    return _coerce(model_cls, value)


def _coerce_portfolio(value: Any) -> Portfolio:
    if isinstance(value, Portfolio):
        return value
    if isinstance(value, Mapping):
        payload = dict(value)
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
        return Portfolio.model_validate(payload)
    raise TypeError("portfolio update must be a Portfolio or mapping")


def _coerce(model_cls: type[DomainModel], value: Any) -> Any:
    if isinstance(value, model_cls):
        return value
    if isinstance(value, Mapping):
        return model_cls.model_validate(value)
    raise TypeError(f"{model_cls.__name__} update must be a model or mapping")


def _coerce_all(model_cls: type[DomainModel], values: Iterable[Any] | None) -> list[Any]:
    if not values:
        return []
    return [_coerce(model_cls, item) for item in values]


def _unique_text(values: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def annotated_reducer(field: str) -> Reducer | None:
    """Read the reducer from `InvestmentState` annotations (LangGraph form)."""
    hints = get_type_hints(InvestmentState, include_extras=True)
    hint = hints.get(field)
    if hint is None:
        return None
    if get_origin(hint) is Annotated:
        args = get_args(hint)
        if len(args) > 1 and callable(args[1]):
            return args[1]
    return None
