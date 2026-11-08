"""Unit tests for deterministic fundamental-analysis helpers."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.models.common import DataSourceMetadata
from app.models.fundamentals import FinancialStatement
from app.tools.fundamentals import (
    EARNINGS_KEYS,
    REVENUE_KEYS,
    classify_cash_generation,
    classify_financial_health,
    classify_liquidity,
    classify_profitability,
    comparison_statement,
    dated_statements,
    growth_rate,
    latest_statement,
    numeric_line_item,
    prefer,
    prior_statement,
    safe_ratio,
    year_ago_statement,
)

UTC = timezone.utc


def _source() -> DataSourceMetadata:
    return DataSourceMetadata(
        provider="unit-test",
        source="fixture",
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
    )


def _statement(
    period_end: date | None,
    revenue: float,
    *,
    cadence: str = "annual",
    fiscal_period: str | None = None,
    extra: dict | None = None,
) -> FinancialStatement:
    line_items = {"revenue": revenue, "net_income": revenue / 5}
    if extra:
        line_items.update(extra)
    return FinancialStatement(
        symbol="AAPL",
        statement_type="income",
        period=cadence,  # type: ignore[arg-type]
        period_end=period_end,
        fiscal_period=fiscal_period,
        line_items=line_items,
        source=_source(),
    )


def test_numeric_line_item_matches_canonical_and_normalized_keys() -> None:
    items = {"Total Revenue": 100.0, "net_income": "see notes", "eps": 6.4}
    assert numeric_line_item(items, REVENUE_KEYS) == 100.0
    assert numeric_line_item(items, EARNINGS_KEYS) is None
    assert numeric_line_item({"earnings-per-share": 6.4}, ("earnings_per_share",)) == 6.4
    assert numeric_line_item({}, REVENUE_KEYS) is None
    assert numeric_line_item(None, REVENUE_KEYS) is None


def test_growth_rate_and_safe_ratio_reject_missing_or_zero_bases() -> None:
    assert growth_rate(110.0, 100.0) == pytest.approx(0.1)
    assert growth_rate(110.0, 0.0) is None
    assert growth_rate(None, 100.0) is None
    assert safe_ratio(30.0, 100.0) == 0.3
    assert safe_ratio(30.0, 0.0) is None
    assert prefer(None, 2.0, 3.0) == 2.0
    assert prefer(None, None) is None


def test_latest_and_prior_statements_use_period_end_not_list_order() -> None:
    older = _statement(date(2023, 9, 30), 90.0, fiscal_period="FY2023")
    newer = _statement(date(2024, 9, 28), 100.0, fiscal_period="FY2024")
    undated = _statement(None, 50.0)
    statements = [undated, newer, older]
    latest = latest_statement(statements)
    prior = prior_statement(statements, latest)
    assert latest is newer
    assert prior is older
    assert dated_statements(statements) == [older, newer]
    assert latest_statement([undated]) is None
    assert prior_statement([newer], newer) is None


def test_year_ago_statement_is_preferred_over_adjacent_quarter() -> None:
    fy2023 = _statement(date(2023, 9, 30), 90.0)
    q3_2024 = _statement(date(2024, 6, 29), 24.0, cadence="quarterly")
    fy2024 = _statement(date(2024, 9, 28), 100.0)
    yoy = year_ago_statement([fy2023, q3_2024, fy2024], fy2024)
    assert yoy is fy2023
    comparison, basis = comparison_statement([fy2023, fy2024], fy2024)
    assert comparison is fy2023
    assert basis == "year_over_year"
    sequential = _statement(date(2024, 3, 30), 22.0, cadence="quarterly")
    latest_q = _statement(date(2024, 6, 29), 24.0, cadence="quarterly")
    comparison_q, basis_q = comparison_statement([sequential, latest_q], latest_q)
    assert comparison_q is sequential
    assert basis_q == "prior_period"


def test_classifiers_use_signs_and_do_not_invent_missing_inputs() -> None:
    assert classify_profitability(10.0) == "profitable"
    assert classify_profitability(-1.0) == "unprofitable"
    assert classify_profitability(0.0) == "breakeven"
    assert classify_profitability(None) == "insufficient_data"
    assert classify_liquidity(1.2) == "adequate"
    assert classify_liquidity(0.8) == "tight"
    assert classify_liquidity(None) == "insufficient_data"
    assert classify_cash_generation(5.0) == "positive"
    assert classify_cash_generation(-2.0) == "negative"
    assert classify_financial_health(
        profitability="profitable",
        liquidity="adequate",
        cash_generation="positive",
    ) == "healthy"
    assert classify_financial_health(
        profitability="unprofitable",
        liquidity="adequate",
        cash_generation="positive",
    ) == "stressed"
    assert classify_financial_health(
        profitability="insufficient_data",
        liquidity="insufficient_data",
        cash_generation="insufficient_data",
    ) == "insufficient_data"
