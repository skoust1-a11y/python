"""Deterministic fundamental-analysis calculations.

These helpers operate only on numbers already retrieved from a
`FundamentalDataProvider`. They never call a vendor, estimate missing
figures, or ask an LLM for a number. Insufficient input yields `None`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any, Literal

from app.models.fundamentals import FinancialStatement

ProfitabilityLabel = Literal["profitable", "unprofitable", "breakeven", "insufficient_data"]
LiquidityLabel = Literal["adequate", "tight", "insufficient_data"]
CashGenerationLabel = Literal["positive", "negative", "insufficient_data"]
FinancialHealthLabel = Literal["healthy", "stressed", "insufficient_data"]
GrowthBasis = Literal["year_over_year", "prior_period", "insufficient_data"]

REVENUE_KEYS = ("revenue", "total_revenue", "net_sales", "sales")
EARNINGS_KEYS = ("net_income", "net_earnings", "earnings", "profit")
EPS_KEYS = ("eps", "diluted_eps", "basic_eps", "earnings_per_share")
OPERATING_INCOME_KEYS = ("operating_income", "operating_profit", "ebit")
EBITDA_KEYS = ("ebitda",)
OPERATING_CASH_FLOW_KEYS = (
    "operating_cash_flow",
    "cash_from_operations",
    "net_cash_from_operating_activities",
)
FREE_CASH_FLOW_KEYS = ("free_cash_flow", "fcf")
TOTAL_DEBT_KEYS = ("total_debt", "net_debt", "debt", "long_term_debt")
EQUITY_KEYS = (
    "shareholders_equity",
    "stockholders_equity",
    "total_equity",
    "total_stockholders_equity",
    "total_shareholders_equity",
)
CURRENT_ASSETS_KEYS = ("current_assets", "total_current_assets")
CURRENT_LIABILITIES_KEYS = ("current_liabilities", "total_current_liabilities")

_YEAR_OVER_YEAR_MIN_DAYS = 300
_YEAR_OVER_YEAR_MAX_DAYS = 430


def normalize_line_item_key(key: str) -> str:
    """Lowercase a line-item name and treat spaces or hyphens as underscores."""
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def numeric_line_item(
    line_items: Mapping[str, Any] | None,
    keys: Sequence[str],
) -> float | None:
    """Return the first numeric value matching any canonical key.

    Non-numeric strings are ignored. Missing or empty mappings yield `None`.
    """
    if not line_items:
        return None
    indexed = {normalize_line_item_key(str(name)): value for name, value in line_items.items()}
    for key in keys:
        value = indexed.get(normalize_line_item_key(key))
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        return float(value)
    return None


def safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    """`numerator / denominator`, or `None` when either side is missing or the base is 0."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def growth_rate(current: float | None, prior: float | None) -> float | None:
    """`(current / prior) - 1`. `None` when a rate cannot be computed."""
    if current is None or prior is None or prior == 0:
        return None
    return (current / prior) - 1.0


def prefer(*values: float | None) -> float | None:
    """First non-`None` value. Used to prefer retrieved metrics over derived ratios."""
    for value in values:
        if value is not None:
            return value
    return None


def dated_statements(statements: Sequence[FinancialStatement] | None) -> list[FinancialStatement]:
    """Statements that include a `period_end`, oldest first."""
    if not statements:
        return []
    dated = [item for item in statements if item.period_end is not None]
    return sorted(dated, key=lambda item: item.period_end or date.min)


def latest_statement(statements: Sequence[FinancialStatement] | None) -> FinancialStatement | None:
    """Most recent dated filing. Undated rows are never treated as latest."""
    ordered = dated_statements(statements)
    return ordered[-1] if ordered else None


def prior_statement(
    statements: Sequence[FinancialStatement] | None,
    latest: FinancialStatement | None = None,
) -> FinancialStatement | None:
    """Previous dated filing, preferring the same reporting cadence as `latest`."""
    current = latest if latest is not None else latest_statement(statements)
    if current is None or current.period_end is None:
        return None
    older = [
        item
        for item in dated_statements(statements)
        if item.period_end is not None and item.period_end < current.period_end
    ]
    same_cadence = [item for item in older if item.period == current.period]
    pool = same_cadence or older
    return pool[-1] if pool else None


def year_ago_statement(
    statements: Sequence[FinancialStatement] | None,
    latest: FinancialStatement | None = None,
) -> FinancialStatement | None:
    """Dated filing closest to one year before `latest`, if one falls in the YoY window."""
    current = latest if latest is not None else latest_statement(statements)
    if current is None or current.period_end is None:
        return None
    target = current.period_end - timedelta(days=365)
    same_cadence = [
        item
        for item in dated_statements(statements)
        if item.period == current.period
        and item.period_end is not None
        and item.period_end < current.period_end
    ]
    window = [
        item
        for item in same_cadence
        if item.period_end is not None
        and _YEAR_OVER_YEAR_MIN_DAYS <= (current.period_end - item.period_end).days <= _YEAR_OVER_YEAR_MAX_DAYS
    ]
    if not window:
        return None
    return min(window, key=lambda item: abs((item.period_end or target) - target))


def comparison_statement(
    statements: Sequence[FinancialStatement] | None,
    latest: FinancialStatement | None = None,
) -> tuple[FinancialStatement | None, GrowthBasis]:
    """Prefer a year-ago filing for growth; otherwise the prior same-cadence period."""
    yoy = year_ago_statement(statements, latest)
    if yoy is not None:
        return yoy, "year_over_year"
    prior = prior_statement(statements, latest)
    if prior is not None:
        return prior, "prior_period"
    return None, "insufficient_data"


def classify_profitability(net_income: float | None) -> ProfitabilityLabel:
    """Sign of reported earnings. Missing earnings are not estimated."""
    if net_income is None:
        return "insufficient_data"
    if net_income > 0:
        return "profitable"
    if net_income < 0:
        return "unprofitable"
    return "breakeven"


def classify_liquidity(current_ratio: float | None) -> LiquidityLabel:
    """`current_ratio < 1` means current liabilities exceed current assets."""
    if current_ratio is None:
        return "insufficient_data"
    return "adequate" if current_ratio >= 1 else "tight"


def classify_cash_generation(operating_cash_flow: float | None) -> CashGenerationLabel:
    """Sign of operating cash flow. Missing cash flow is not estimated."""
    if operating_cash_flow is None:
        return "insufficient_data"
    return "positive" if operating_cash_flow >= 0 else "negative"


def classify_financial_health(
    *,
    profitability: ProfitabilityLabel,
    liquidity: LiquidityLabel,
    cash_generation: CashGenerationLabel,
) -> FinancialHealthLabel:
    """Composite of known signals. Any negative known signal is stressed.

    Missing signals are skipped rather than invented. If nothing is known the
    result is `insufficient_data`.
    """
    signals: list[bool] = []
    if profitability != "insufficient_data":
        signals.append(profitability != "unprofitable")
    if liquidity != "insufficient_data":
        signals.append(liquidity == "adequate")
    if cash_generation != "insufficient_data":
        signals.append(cash_generation == "positive")
    if not signals:
        return "insufficient_data"
    return "healthy" if all(signals) else "stressed"
