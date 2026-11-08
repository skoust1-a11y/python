"""Fundamental Analysis Agent.

Retrieves profiles, statements, key metrics, and valuation through the injected
`FundamentalDataProvider`. Numerical figures are taken from retrieved payloads
or computed in Python. The LLM interprets that structured evidence and must
not supply missing figures.

Retrieved fundamentals are labeled as latest reported, historical, or current
market. Filed financials are never presented as live market data.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal, TypeVar

from pydantic import AwareDatetime, Field

from app.agents.base import Agent, AgentMetadata, AgentRuntime
from app.agents.contracts import AgentAnalysis, AgentInput
from app.exceptions import AgentError, ProviderError
from app.models.common import DataSourceMetadata, DomainModel, Evidence
from app.models.fundamentals import (
    CompanyProfile,
    FinancialMetrics,
    FinancialStatement,
    ReportingPeriod,
    StatementType,
    ValuationMetrics,
)
from app.models.types import NonEmptyText, Symbol, UnitInterval
from app.providers.contracts import FundamentalDataProvider
from app.tools.fundamentals import (
    CURRENT_ASSETS_KEYS,
    CURRENT_LIABILITIES_KEYS,
    EARNINGS_KEYS,
    EBITDA_KEYS,
    EPS_KEYS,
    EQUITY_KEYS,
    FREE_CASH_FLOW_KEYS,
    OPERATING_CASH_FLOW_KEYS,
    OPERATING_INCOME_KEYS,
    REVENUE_KEYS,
    TOTAL_DEBT_KEYS,
    CashGenerationLabel,
    FinancialHealthLabel,
    GrowthBasis,
    LiquidityLabel,
    ProfitabilityLabel,
    classify_cash_generation,
    classify_financial_health,
    classify_liquidity,
    classify_profitability,
    comparison_statement,
    growth_rate,
    latest_statement,
    numeric_line_item,
    prefer,
    safe_ratio,
)

UTC = timezone.utc
T = TypeVar("T")

OverallProfitability = Literal[
    "profitable", "unprofitable", "breakeven", "insufficient_data", "mixed"
]
OverallHealth = Literal["healthy", "stressed", "insufficient_data", "mixed"]

SYSTEM_PROMPT = (
    "You are a fundamental-analysis interpreter. You receive structured evidence "
    "already retrieved or calculated from fundamental data. Interpret only that "
    "evidence. Do not invent revenue, earnings, EPS, margins, debt, cash flow, "
    "ROE, valuation multiples, or other figures. "
    "latest_reported figures are the most recent filed financial period and are "
    "not current market data. historical figures are earlier reporting periods. "
    "current_market figures are point-in-time valuation or market-based metrics. "
    "Never describe a filed financial as current. "
    "If a field is null or listed as unavailable, treat it as missing and say so. "
    "Do not use outside knowledge of a company's financials."
)


class LatestReportedFinancials(DomainModel):
    """Most recent filed period. These numbers are lagged, not live market data."""

    as_of_kind: Literal["latest_reported"] = "latest_reported"
    reporting_period: str | None = None
    cadence: ReportingPeriod | None = None
    fiscal_period: str | None = None
    period_end: date | None = None
    timestamp: AwareDatetime | None = None
    revenue: float | None = None
    earnings: float | None = None
    eps: float | None = None
    ebitda: float | None = None
    operating_margin: float | None = None
    profit_margin: float | None = None
    roe: float | None = None
    roa: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    total_debt: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None


class HistoricalFinancials(DomainModel):
    """Earlier reporting period used for growth. Not current and not the latest filing."""

    as_of_kind: Literal["historical"] = "historical"
    reporting_period: str | None = None
    cadence: ReportingPeriod | None = None
    fiscal_period: str | None = None
    period_end: date | None = None
    timestamp: AwareDatetime | None = None
    revenue: float | None = None
    earnings: float | None = None
    eps: float | None = None
    growth_basis: GrowthBasis = "insufficient_data"


class CurrentMarketMetrics(DomainModel):
    """Point-in-time market-based valuation. Distinct from reported financials."""

    as_of_kind: Literal["current_market"] = "current_market"
    timestamp: AwareDatetime | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    pb_ratio: float | None = None
    ps_ratio: float | None = None
    peg_ratio: float | None = None
    ev_to_ebitda: float | None = None
    dividend_yield: float | None = None


class FundamentalSupportingMetrics(DomainModel):
    """Deterministic figures derived from retrieved fundamentals. Null means missing."""

    symbol: Symbol
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    latest_reported: LatestReportedFinancials
    historical: HistoricalFinancials
    current_market: CurrentMarketMetrics
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    profitability: ProfitabilityLabel
    liquidity: LiquidityLabel
    cash_generation: CashGenerationLabel
    financial_health: FinancialHealthLabel


class ComputedSymbolAnalysis(DomainModel):
    """Per-symbol Python result before LLM interpretation."""

    symbol: Symbol
    supporting_metrics: FundamentalSupportingMetrics
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    reporting_period: str | None = None
    timestamp: AwareDatetime | None = None
    source: DataSourceMetadata | None = None
    sources: list[DataSourceMetadata] = Field(default_factory=list)
    factual_observations: list[NonEmptyText] = Field(default_factory=list)


class FundamentalInterpretation(DomainModel):
    """LLM reading of structured evidence. Must not introduce new figures."""

    fundamental_assessment: NonEmptyText
    strengths: list[NonEmptyText] = Field(default_factory=list)
    weaknesses: list[NonEmptyText] = Field(default_factory=list)
    valuation_observations: list[NonEmptyText] = Field(default_factory=list)
    financial_risks: list[NonEmptyText] = Field(default_factory=list)
    confidence: UnitInterval


class FundamentalAgentExtras(DomainModel):
    """Structured payload stored on `AgentOutput.extras`."""

    fundamental_assessment: NonEmptyText
    strengths: list[NonEmptyText] = Field(default_factory=list)
    weaknesses: list[NonEmptyText] = Field(default_factory=list)
    valuation_observations: list[NonEmptyText] = Field(default_factory=list)
    financial_risks: list[NonEmptyText] = Field(default_factory=list)
    supporting_metrics: FundamentalSupportingMetrics
    profitability: OverallProfitability
    financial_health: OverallHealth
    reporting_period: str | None = None
    timestamp: AwareDatetime | None = None
    source: DataSourceMetadata | None = None
    sources: list[DataSourceMetadata] = Field(default_factory=list)
    analyzed_at: AwareDatetime
    unavailable: list[NonEmptyText] = Field(default_factory=list)
    fundamental_data_provider: NonEmptyText
    analyses: list[ComputedSymbolAnalysis] = Field(default_factory=list)


@dataclass
class _CompanySnapshot:
    symbol: str
    profile: CompanyProfile | None = None
    income: list[FinancialStatement] = field(default_factory=list)
    balance_sheet: list[FinancialStatement] = field(default_factory=list)
    cash_flow: list[FinancialStatement] = field(default_factory=list)
    key_metrics: FinancialMetrics | None = None
    valuation: ValuationMetrics | None = None
    unavailable: list[str] = field(default_factory=list)


class FundamentalAnalysisAgent(Agent):
    """Specialist that scores filings and valuation from an injected fundamentals provider."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="fundamental-analysis",
            role="fundamental-analyst",
            description=(
                "Analyzes latest reported revenue, growth, earnings, EPS, margins, "
                "debt, cash flow, ROE, valuation, profitability, and financial health "
                "using retrieved fundamental data and deterministic Python calculations."
            ),
        )

    def analyze(self, payload: AgentInput, runtime: AgentRuntime) -> AgentAnalysis:
        if not payload.symbols:
            raise AgentError("Fundamental analysis requires at least one symbol.")

        fundamentals = runtime.providers.fundamentals
        cadences = _cadences_from_extras(payload.extras)

        analyses: list[ComputedSymbolAnalysis] = []
        for symbol in payload.symbols:
            snapshot = _load_company(fundamentals, symbol, cadences=cadences)
            computed = _compute_symbol_analysis(snapshot)
            _record_evidence(runtime, computed, snapshot)
            analyses.append(computed)

        interpretation = runtime.complete_structured(
            _interpretation_prompt(payload, analyses),
            FundamentalInterpretation,
            system=SYSTEM_PROMPT,
            metadata={"task": "fundamental-interpretation"},
        )
        extras_model = _build_extras(
            interpretation,
            analyses,
            provider_name=fundamentals.name,
        )
        return AgentAnalysis(
            summary=extras_model.fundamental_assessment,
            findings=_findings(extras_model),
            evidence=runtime.evidence.items(),
            confidence=_capped_confidence(interpretation.confidence, extras_model.unavailable),
            extras=extras_model.model_dump(mode="json"),
        )


def _cadences_from_extras(extras: dict[str, Any]) -> tuple[ReportingPeriod, ...]:
    raw = extras.get("statement_period", extras.get("reporting_period"))
    if raw is None or raw == "":
        return ("annual", "quarterly")
    if not isinstance(raw, str):
        raise AgentError("statement_period must be annual, quarterly, or latest.")
    token = raw.strip().lower()
    if token in {"both", "latest", "all"}:
        return ("annual", "quarterly")
    if token == "annual":
        return ("annual",)
    if token == "quarterly":
        return ("quarterly",)
    raise AgentError("statement_period must be annual, quarterly, or latest.")


def _load_company(
    fundamentals: FundamentalDataProvider,
    symbol: str,
    *,
    cadences: Sequence[ReportingPeriod],
) -> _CompanySnapshot:
    unavailable: list[str] = []
    profile = _fetch(lambda: fundamentals.get_company_profile(symbol), unavailable, "company_profile")
    key_metrics = _fetch(lambda: fundamentals.get_key_metrics(symbol), unavailable, "key_metrics")
    valuation = _fetch(
        lambda: fundamentals.get_valuation_metrics(symbol), unavailable, "valuation"
    )

    income: list[FinancialStatement] = []
    balance_sheet: list[FinancialStatement] = []
    cash_flow: list[FinancialStatement] = []
    for cadence in cadences:
        income.extend(
            _fetch_statements(
                fundamentals, symbol, "income", cadence, unavailable, "income_statement"
            )
        )
        balance_sheet.extend(
            _fetch_statements(
                fundamentals,
                symbol,
                "balance_sheet",
                cadence,
                unavailable,
                "balance_sheet",
            )
        )
        cash_flow.extend(
            _fetch_statements(
                fundamentals, symbol, "cash_flow", cadence, unavailable, "cash_flow"
            )
        )

    if not income:
        unavailable.append("income_statement")
    if not balance_sheet:
        unavailable.append("balance_sheet")
    if not cash_flow:
        unavailable.append("cash_flow")

    return _CompanySnapshot(
        symbol=symbol,
        profile=profile,
        income=income,
        balance_sheet=balance_sheet,
        cash_flow=cash_flow,
        key_metrics=key_metrics,
        valuation=valuation,
        unavailable=_unique(unavailable),
    )


def _fetch_statements(
    fundamentals: FundamentalDataProvider,
    symbol: str,
    statement_type: StatementType,
    cadence: ReportingPeriod,
    unavailable: list[str],
    label: str,
) -> list[FinancialStatement]:
    statements = _fetch(
        lambda: fundamentals.get_financial_statements(
            symbol, statement_type=statement_type, period=cadence
        ),
        unavailable,
        f"{label}_{cadence}",
    )
    if statements is None:
        return []
    return [item for item in statements if item.symbol == symbol]


def _fetch(operation: Callable[[], T], unavailable: list[str], label: str) -> T | None:
    try:
        return operation()
    except ProviderError:
        unavailable.append(label)
        return None


def _compute_symbol_analysis(snapshot: _CompanySnapshot) -> ComputedSymbolAnalysis:
    unavailable = list(snapshot.unavailable)
    metrics = snapshot.key_metrics
    latest_income = latest_statement(snapshot.income)
    latest_balance = latest_statement(snapshot.balance_sheet)
    latest_cash = latest_statement(snapshot.cash_flow)
    comparison, growth_basis = comparison_statement(snapshot.income, latest_income)

    statement_revenue = numeric_line_item(
        latest_income.line_items if latest_income else None, REVENUE_KEYS
    )
    statement_earnings = numeric_line_item(
        latest_income.line_items if latest_income else None, EARNINGS_KEYS
    )
    statement_eps = numeric_line_item(
        latest_income.line_items if latest_income else None, EPS_KEYS
    )
    operating_income = numeric_line_item(
        latest_income.line_items if latest_income else None, OPERATING_INCOME_KEYS
    )
    statement_ebitda = numeric_line_item(
        latest_income.line_items if latest_income else None, EBITDA_KEYS
    )
    total_debt = numeric_line_item(
        latest_balance.line_items if latest_balance else None, TOTAL_DEBT_KEYS
    )
    equity = numeric_line_item(
        latest_balance.line_items if latest_balance else None, EQUITY_KEYS
    )
    current_assets = numeric_line_item(
        latest_balance.line_items if latest_balance else None, CURRENT_ASSETS_KEYS
    )
    current_liabilities = numeric_line_item(
        latest_balance.line_items if latest_balance else None, CURRENT_LIABILITIES_KEYS
    )
    operating_cash_flow = numeric_line_item(
        latest_cash.line_items if latest_cash else None, OPERATING_CASH_FLOW_KEYS
    )
    free_cash_flow = numeric_line_item(
        latest_cash.line_items if latest_cash else None, FREE_CASH_FLOW_KEYS
    )

    revenue = prefer(metrics.revenue if metrics is not None else None, statement_revenue)
    earnings = prefer(metrics.net_income if metrics is not None else None, statement_earnings)
    eps = prefer(metrics.eps if metrics is not None else None, statement_eps)
    ebitda = prefer(metrics.ebitda if metrics is not None else None, statement_ebitda)
    operating_margin = prefer(
        metrics.operating_margin if metrics is not None else None,
        safe_ratio(operating_income, statement_revenue),
    )
    profit_margin = prefer(
        metrics.profit_margin if metrics is not None else None,
        safe_ratio(statement_earnings, statement_revenue),
    )
    roe = prefer(
        metrics.roe if metrics is not None else None,
        safe_ratio(statement_earnings, equity),
    )
    roa = metrics.roa if metrics is not None else None
    debt_to_equity = prefer(
        metrics.debt_to_equity if metrics is not None else None,
        safe_ratio(total_debt, equity),
    )
    current_ratio = prefer(
        metrics.current_ratio if metrics is not None else None,
        safe_ratio(current_assets, current_liabilities),
    )

    historical_revenue = numeric_line_item(
        comparison.line_items if comparison else None, REVENUE_KEYS
    )
    historical_earnings = numeric_line_item(
        comparison.line_items if comparison else None, EARNINGS_KEYS
    )
    historical_eps = numeric_line_item(
        comparison.line_items if comparison else None, EPS_KEYS
    )
    revenue_growth = growth_rate(statement_revenue, historical_revenue)
    earnings_growth = growth_rate(statement_earnings, historical_earnings)

    valuation = snapshot.valuation
    current_market = CurrentMarketMetrics(
        timestamp=_first_timestamp(
            valuation.timestamp if valuation is not None else None,
            metrics.timestamp if metrics is not None else None,
        ),
        market_cap=prefer(
            valuation.market_cap if valuation is not None else None,
            metrics.market_cap if metrics is not None else None,
        ),
        enterprise_value=prefer(
            valuation.enterprise_value if valuation is not None else None,
            metrics.enterprise_value if metrics is not None else None,
        ),
        pe_ratio=prefer(
            valuation.pe_ratio if valuation is not None else None,
            metrics.pe_ratio if metrics is not None else None,
        ),
        forward_pe=prefer(
            valuation.forward_pe if valuation is not None else None,
            metrics.forward_pe if metrics is not None else None,
        ),
        pb_ratio=prefer(
            valuation.pb_ratio if valuation is not None else None,
            metrics.pb_ratio if metrics is not None else None,
        ),
        ps_ratio=prefer(
            valuation.ps_ratio if valuation is not None else None,
            metrics.ps_ratio if metrics is not None else None,
        ),
        peg_ratio=prefer(
            valuation.peg_ratio if valuation is not None else None,
            metrics.peg_ratio if metrics is not None else None,
        ),
        ev_to_ebitda=prefer(
            valuation.ev_to_ebitda if valuation is not None else None,
            metrics.ev_to_ebitda if metrics is not None else None,
        ),
        dividend_yield=prefer(
            valuation.dividend_yield if valuation is not None else None,
            metrics.dividend_yield if metrics is not None else None,
        ),
    )

    latest_anchor = _latest_reported_anchor(metrics, latest_income, latest_balance, latest_cash)
    latest_reported = LatestReportedFinancials(
        reporting_period=latest_anchor["reporting_period"],
        cadence=latest_anchor["cadence"],
        fiscal_period=latest_anchor["fiscal_period"],
        period_end=latest_anchor["period_end"],
        timestamp=latest_anchor["timestamp"],
        revenue=revenue,
        earnings=earnings,
        eps=eps,
        ebitda=ebitda,
        operating_margin=operating_margin,
        profit_margin=profit_margin,
        roe=roe,
        roa=roa,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,
        total_debt=total_debt,
        operating_cash_flow=operating_cash_flow,
        free_cash_flow=free_cash_flow,
    )
    historical = HistoricalFinancials(
        reporting_period=_format_reporting_period(
            comparison.period if comparison else None,
            comparison.fiscal_period if comparison else None,
            comparison.period_end if comparison else None,
        ),
        cadence=comparison.period if comparison else None,
        fiscal_period=comparison.fiscal_period if comparison else None,
        period_end=comparison.period_end if comparison else None,
        timestamp=comparison.timestamp if comparison else None,
        revenue=historical_revenue,
        earnings=historical_earnings,
        eps=historical_eps,
        growth_basis=growth_basis,
    )

    profitability = classify_profitability(earnings)
    liquidity = classify_liquidity(current_ratio)
    cash_generation = classify_cash_generation(operating_cash_flow)
    financial_health = classify_financial_health(
        profitability=profitability,
        liquidity=liquidity,
        cash_generation=cash_generation,
    )

    _mark_missing(unavailable, "revenue", revenue, True)
    _mark_missing(unavailable, "earnings", earnings, True)
    _mark_missing(unavailable, "eps", eps, True)
    _mark_missing(
        unavailable,
        "margins",
        prefer(operating_margin, profit_margin),
        True,
    )
    _mark_missing(unavailable, "debt", prefer(debt_to_equity, total_debt), True)
    _mark_missing(
        unavailable, "cash_flow", prefer(operating_cash_flow, free_cash_flow), True
    )
    _mark_missing(unavailable, "roe", roe, True)
    _mark_missing(unavailable, "revenue_growth", revenue_growth, True)
    _mark_missing(
        unavailable,
        "valuation",
        prefer(current_market.pe_ratio, current_market.market_cap, current_market.pb_ratio),
        True,
    )
    if profitability == "insufficient_data":
        unavailable.append("profitability")
    if financial_health == "insufficient_data":
        unavailable.append("company_financial_health")

    supporting = FundamentalSupportingMetrics(
        symbol=snapshot.symbol,
        company_name=snapshot.profile.name if snapshot.profile is not None else None,
        sector=snapshot.profile.sector if snapshot.profile is not None else None,
        industry=snapshot.profile.industry if snapshot.profile is not None else None,
        currency=_first_present(
            metrics.currency if metrics is not None else None,
            latest_income.currency if latest_income is not None else None,
            latest_balance.currency if latest_balance is not None else None,
            latest_cash.currency if latest_cash is not None else None,
            snapshot.profile.currency if snapshot.profile is not None else None,
            valuation.currency if valuation is not None else None,
        ),
        latest_reported=latest_reported,
        historical=historical,
        current_market=current_market,
        revenue_growth=revenue_growth,
        earnings_growth=earnings_growth,
        profitability=profitability,
        liquidity=liquidity,
        cash_generation=cash_generation,
        financial_health=financial_health,
    )
    unavailable = _unique(unavailable)
    sources = _sources(snapshot)
    timestamp = _as_of(snapshot, latest_reported, current_market, historical)
    return ComputedSymbolAnalysis(
        symbol=snapshot.symbol,
        supporting_metrics=supporting,
        unavailable=unavailable,
        reporting_period=latest_reported.reporting_period,
        timestamp=timestamp,
        source=sources[0] if sources else None,
        sources=sources,
        factual_observations=_factual_observations(supporting, unavailable),
    )


def _latest_reported_anchor(
    metrics: FinancialMetrics | None,
    income: FinancialStatement | None,
    balance: FinancialStatement | None,
    cash: FinancialStatement | None,
) -> dict[str, Any]:
    dated = [item for item in (income, balance, cash) if item is not None and item.period_end]
    latest_filing = (
        max(dated, key=lambda item: item.period_end or date.min) if dated else income or balance or cash
    )
    cadence = latest_filing.period if latest_filing is not None else None
    fiscal_period = latest_filing.fiscal_period if latest_filing is not None else None
    period_end = latest_filing.period_end if latest_filing is not None else None
    if metrics is not None and metrics.period and fiscal_period is None and period_end is None:
        fiscal_period = metrics.period
    timestamp = _first_timestamp(
        latest_filing.timestamp if latest_filing is not None else None,
        metrics.timestamp if metrics is not None else None,
    )
    return {
        "cadence": cadence,
        "fiscal_period": fiscal_period,
        "period_end": period_end,
        "timestamp": timestamp,
        "reporting_period": _format_reporting_period(cadence, fiscal_period, period_end)
        or (metrics.period if metrics is not None else None),
    }


def _format_reporting_period(
    cadence: str | None,
    fiscal_period: str | None,
    period_end: date | None,
) -> str | None:
    parts: list[str] = []
    if cadence:
        parts.append(cadence)
    if fiscal_period:
        parts.append(fiscal_period)
    if period_end is not None:
        parts.append(period_end.isoformat())
    return " ".join(parts) if parts else None


def _mark_missing(unavailable: list[str], label: str, value: Any, relevant: bool) -> None:
    if relevant and value is None and label not in unavailable:
        unavailable.append(label)


def _first_present(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _first_timestamp(*values: datetime | None) -> datetime | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _as_of(
    snapshot: _CompanySnapshot,
    latest_reported: LatestReportedFinancials,
    current_market: CurrentMarketMetrics,
    historical: HistoricalFinancials,
) -> datetime | None:
    timestamps: list[datetime] = []
    for value in (
        latest_reported.timestamp,
        current_market.timestamp,
        historical.timestamp,
        snapshot.profile.timestamp if snapshot.profile is not None else None,
        snapshot.key_metrics.timestamp if snapshot.key_metrics is not None else None,
        snapshot.valuation.timestamp if snapshot.valuation is not None else None,
    ):
        if value is not None:
            timestamps.append(value)
    for statement in (*snapshot.income, *snapshot.balance_sheet, *snapshot.cash_flow):
        if statement.timestamp is not None:
            timestamps.append(statement.timestamp)
    return max(timestamps) if timestamps else None


def _sources(snapshot: _CompanySnapshot) -> list[DataSourceMetadata]:
    payloads: list[Any] = [
        snapshot.profile,
        snapshot.key_metrics,
        snapshot.valuation,
        *snapshot.income,
        *snapshot.balance_sheet,
        *snapshot.cash_flow,
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
    metrics: FundamentalSupportingMetrics,
    unavailable: list[str],
) -> list[str]:
    observations: list[str] = []
    symbol = metrics.symbol
    reported = metrics.latest_reported
    historical = metrics.historical
    market = metrics.current_market
    period = reported.reporting_period or "an unspecified filed period"
    if reported.revenue is not None:
        observations.append(
            f"{symbol} latest reported revenue is {reported.revenue} "
            f"for {period}. This is a filed figure, not a current market metric."
        )
    if reported.earnings is not None:
        observations.append(
            f"{symbol} latest reported earnings are {reported.earnings} for {period}."
        )
    if reported.eps is not None:
        observations.append(f"{symbol} latest reported EPS is {reported.eps} for {period}.")
    if reported.operating_margin is not None:
        observations.append(
            f"{symbol} latest reported operating margin is {reported.operating_margin} "
            f"for {period}."
        )
    if reported.profit_margin is not None:
        observations.append(
            f"{symbol} latest reported profit margin is {reported.profit_margin} for {period}."
        )
    if reported.roe is not None:
        observations.append(f"{symbol} latest reported ROE is {reported.roe} for {period}.")
    if reported.debt_to_equity is not None:
        observations.append(
            f"{symbol} latest reported debt-to-equity is {reported.debt_to_equity} for {period}."
        )
    if reported.operating_cash_flow is not None:
        observations.append(
            f"{symbol} latest reported operating cash flow is {reported.operating_cash_flow} "
            f"for {period}."
        )
    if historical.revenue is not None:
        hist_period = historical.reporting_period or "a prior filed period"
        observations.append(
            f"{symbol} historical revenue is {historical.revenue} for {hist_period}."
        )
    if metrics.revenue_growth is not None:
        observations.append(
            f"{symbol} revenue growth versus the {historical.growth_basis.replace('_', ' ')} "
            f"is {metrics.revenue_growth}."
        )
    if metrics.earnings_growth is not None:
        observations.append(
            f"{symbol} earnings growth versus the {historical.growth_basis.replace('_', ' ')} "
            f"is {metrics.earnings_growth}."
        )
    if market.market_cap is not None:
        observations.append(
            f"{symbol} current market capitalization is {market.market_cap} "
            f"as of {_stamp(market.timestamp)}."
        )
    if market.pe_ratio is not None:
        observations.append(
            f"{symbol} current market PE ratio is {market.pe_ratio} "
            f"as of {_stamp(market.timestamp)}."
        )
    observations.append(f"{symbol} profitability is {metrics.profitability}.")
    observations.append(f"{symbol} company financial health is {metrics.financial_health}.")
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
    snapshot: _CompanySnapshot,
) -> None:
    metrics = computed.supporting_metrics
    reported = metrics.latest_reported
    reported_period = reported.fiscal_period or reported.cadence
    if snapshot.key_metrics is not None:
        _add_metric_evidence(
            runtime,
            snapshot.key_metrics.source,
            computed.symbol,
            reported_period or snapshot.key_metrics.period,
            (
                ("revenue", snapshot.key_metrics.revenue),
                ("earnings", snapshot.key_metrics.net_income),
                ("eps", snapshot.key_metrics.eps),
                ("operating_margin", snapshot.key_metrics.operating_margin),
                ("profit_margin", snapshot.key_metrics.profit_margin),
                ("roe", snapshot.key_metrics.roe),
                ("debt_to_equity", snapshot.key_metrics.debt_to_equity),
            ),
        )
    latest_income = latest_statement(snapshot.income)
    latest_balance = latest_statement(snapshot.balance_sheet)
    latest_cash = latest_statement(snapshot.cash_flow)
    if latest_income is not None:
        _add_metric_evidence(
            runtime,
            latest_income.source,
            computed.symbol,
            latest_income.fiscal_period or latest_income.period,
            (
                ("revenue", numeric_line_item(latest_income.line_items, REVENUE_KEYS)),
                ("earnings", numeric_line_item(latest_income.line_items, EARNINGS_KEYS)),
                ("eps", numeric_line_item(latest_income.line_items, EPS_KEYS)),
            ),
        )
    if latest_balance is not None:
        _add_metric_evidence(
            runtime,
            latest_balance.source,
            computed.symbol,
            latest_balance.fiscal_period or latest_balance.period,
            (
                ("total_debt", reported.total_debt),
                ("debt_to_equity", reported.debt_to_equity if snapshot.key_metrics is None else None),
            ),
        )
    if latest_cash is not None:
        _add_metric_evidence(
            runtime,
            latest_cash.source,
            computed.symbol,
            latest_cash.fiscal_period or latest_cash.period,
            (
                ("operating_cash_flow", reported.operating_cash_flow),
                ("free_cash_flow", reported.free_cash_flow),
            ),
        )
    if snapshot.valuation is not None:
        _add_metric_evidence(
            runtime,
            snapshot.valuation.source,
            computed.symbol,
            None,
            (
                ("market_cap", snapshot.valuation.market_cap),
                ("pe_ratio", snapshot.valuation.pe_ratio),
                ("pb_ratio", snapshot.valuation.pb_ratio),
                ("ps_ratio", snapshot.valuation.ps_ratio),
            ),
        )
    derived_source = DataSourceMetadata(
        provider=runtime.providers.fundamentals.name,
        source="derived-metric",
        timestamp=computed.timestamp or datetime.now(tz=UTC),
    )
    derived = (
        ("revenue_growth", metrics.revenue_growth),
        ("earnings_growth", metrics.earnings_growth),
        ("operating_margin", reported.operating_margin if snapshot.key_metrics is None else None),
        ("profit_margin", reported.profit_margin if snapshot.key_metrics is None else None),
        ("roe", reported.roe if snapshot.key_metrics is None else None),
        ("debt_to_equity", reported.debt_to_equity if snapshot.key_metrics is None else None),
        ("current_ratio", reported.current_ratio if snapshot.key_metrics is None else None),
    )
    _add_metric_evidence(
        runtime,
        derived_source,
        computed.symbol,
        reported_period,
        derived,
    )
    runtime.evidence.add(
        Evidence(
            source=derived_source,
            symbol=computed.symbol,
            period=reported_period,
            field="profitability",
            value=metrics.profitability,
        )
    )
    runtime.evidence.add(
        Evidence(
            source=derived_source,
            symbol=computed.symbol,
            period=reported_period,
            field="financial_health",
            value=metrics.financial_health,
        )
    )


def _add_metric_evidence(
    runtime: AgentRuntime,
    source: DataSourceMetadata,
    symbol: str,
    period: str | None,
    fields: Sequence[tuple[str, float | None]],
) -> None:
    for field_name, value in fields:
        if value is None:
            continue
        runtime.evidence.add(
            Evidence(
                source=source,
                symbol=symbol,
                period=period,
                field=field_name,
                value=value,
            )
        )


def _build_extras(
    interpretation: FundamentalInterpretation,
    analyses: list[ComputedSymbolAnalysis],
    *,
    provider_name: str,
) -> FundamentalAgentExtras:
    risks = list(interpretation.financial_risks)
    gap_risk = _gap_risk(analyses)
    if gap_risk and gap_risk not in risks:
        risks.append(gap_risk)
    primary = analyses[0]
    return FundamentalAgentExtras(
        fundamental_assessment=interpretation.fundamental_assessment,
        strengths=list(interpretation.strengths),
        weaknesses=list(interpretation.weaknesses),
        valuation_observations=list(interpretation.valuation_observations),
        financial_risks=risks,
        supporting_metrics=primary.supporting_metrics,
        profitability=_overall_label([item.supporting_metrics.profitability for item in analyses]),
        financial_health=_overall_label(
            [item.supporting_metrics.financial_health for item in analyses]
        ),
        reporting_period=primary.reporting_period,
        timestamp=primary.timestamp,
        source=primary.source,
        sources=_merge_sources(analyses),
        analyzed_at=datetime.now(tz=UTC),
        unavailable=_merge_unavailable(analyses),
        fundamental_data_provider=provider_name,
        analyses=analyses,
    )


def _findings(extras: FundamentalAgentExtras) -> list[str]:
    findings: list[str] = []
    findings.extend(extras.strengths)
    findings.extend(extras.weaknesses)
    findings.extend(extras.valuation_observations)
    return findings


def _interpretation_prompt(payload: AgentInput, analyses: list[ComputedSymbolAnalysis]) -> str:
    bundle = {
        "request_id": payload.request_id,
        "question": payload.question,
        "symbols": payload.symbols,
        "analyses": [item.model_dump(mode="json") for item in analyses],
        "rules": [
            "Numeric values were retrieved from fundamental data or calculated in Python.",
            "latest_reported is the most recent filed period, not current market data.",
            "historical is an earlier reporting period used for growth.",
            "current_market is point-in-time valuation. Do not mix these clocks.",
            "Null fields and the unavailable lists are missing. Do not fill them in.",
            "Do not cite figures or dates that are not in this payload.",
        ],
    }
    return (
        "Interpret the following fundamental evidence and return "
        "fundamental_assessment, strengths, weaknesses, valuation_observations, "
        "financial_risks, and confidence.\n\n"
        + json.dumps(bundle, indent=2, default=str)
    )


def _gap_risk(analyses: list[ComputedSymbolAnalysis]) -> str | None:
    missing = _merge_unavailable(analyses)
    if not missing:
        return None
    return "Unavailable inputs were not estimated: " + ", ".join(missing) + "."


def _overall_label(labels: list[str]) -> Any:
    unique = {label for label in labels}
    if len(unique) == 1:
        return next(iter(unique))
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


def _capped_confidence(confidence: float, unavailable: list[str]) -> float:
    if {"revenue", "earnings"} & set(unavailable):
        return min(confidence, 0.5)
    return confidence


def _unique(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen
