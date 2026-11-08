from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class UnknownTemplate(Exception):
    pass


class SlotError(Exception):
    pass


@dataclass
class Slot:
    name: str
    kind: str  # int | float | str | enum
    required: bool = False
    default: Any = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    choices: Optional[List[str]] = None
    nullable: bool = True


@dataclass
class SqlTemplate:
    query_id: str
    description: str
    tables: List[str]
    sql: str
    rbac: str  # portfolio_id | asset_via_holdings | none
    slots: Dict[str, Slot] = field(default_factory=dict)


RISK_LEVELS = ["Low", "Medium", "High", "Moderate"]
RISK_TYPES = [
    "Market Volatility",
    "Liquidity Risk",
    "Regulatory Risk",
    "Credit Risk",
    "Geopolitical Risk",
    "Market Risk",
]


def _t(query_id: str, description: str, tables: List[str], sql: str, rbac: str, slots: List[Slot]) -> SqlTemplate:
    return SqlTemplate(
        query_id=query_id,
        description=description,
        tables=tables,
        sql=sql,
        rbac=rbac,
        slots={s.name: s for s in slots},
    )


TEMPLATES: Dict[str, SqlTemplate] = {
    t.query_id: t
    for t in [
        _t(
            "portfolios.by_risk_category",
            "Portfolios with a given risk_category",
            ["portfolios"],
            "SELECT portfolio_id, portfolio_name, portfolio_manager, risk_category, total_value, benchmark_index "
            "FROM portfolios WHERE risk_category = :risk_category AND {RBAC} ORDER BY portfolio_id LIMIT :limit",
            "portfolio_id",
            [
                Slot("risk_category", "enum", required=True, choices=RISK_LEVELS, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "portfolios.by_manager",
            "Portfolios by manager name",
            ["portfolios"],
            "SELECT portfolio_id, portfolio_name, portfolio_manager, risk_category, total_value, benchmark_index "
            "FROM portfolios WHERE lower(portfolio_manager) LIKE :manager AND {RBAC} ORDER BY portfolio_id LIMIT :limit",
            "portfolio_id",
            [
                Slot("manager", "str", required=True, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "portfolios.by_benchmark",
            "Portfolios tracking a benchmark index",
            ["portfolios"],
            "SELECT portfolio_id, portfolio_name, portfolio_manager, risk_category, total_value, benchmark_index "
            "FROM portfolios WHERE benchmark_index = :benchmark AND {RBAC} ORDER BY portfolio_id LIMIT :limit",
            "portfolio_id",
            [
                Slot("benchmark", "str", required=True, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "portfolios.all_in_scope",
            "All portfolios visible to the caller",
            ["portfolios"],
            "SELECT portfolio_id, portfolio_name, portfolio_manager, risk_category, total_value, benchmark_index "
            "FROM portfolios WHERE {RBAC} ORDER BY portfolio_id LIMIT :limit",
            "portfolio_id",
            [Slot("limit", "int", default=100, minimum=1, maximum=200)],
        ),
        _t(
            "holdings.by_portfolio",
            "Holdings of given portfolio ids",
            ["portfolio_holdings"],
            "SELECT holding_id, portfolio_id, asset_name, asset_type, sector, allocation_percentage, market_value, buy_price, buy_date, last_updated "
            "FROM portfolio_holdings WHERE {RBAC} ORDER BY market_value DESC LIMIT :limit",
            "portfolio_id",
            [Slot("limit", "int", default=100, minimum=1, maximum=200)],
        ),
        _t(
            "holdings.by_sector",
            "Holdings in a sector across scope",
            ["portfolio_holdings"],
            "SELECT holding_id, portfolio_id, asset_name, asset_type, sector, allocation_percentage, market_value, buy_price, buy_date, last_updated "
            "FROM portfolio_holdings WHERE sector = :sector AND {RBAC} ORDER BY allocation_percentage DESC LIMIT :limit",
            "portfolio_id",
            [
                Slot("sector", "str", required=True, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "holdings.by_allocation_threshold",
            "Holdings with allocation_percentage above N",
            ["portfolio_holdings"],
            "SELECT holding_id, portfolio_id, asset_name, asset_type, sector, allocation_percentage, market_value, buy_price, buy_date, last_updated "
            "FROM portfolio_holdings WHERE allocation_percentage >= :min_allocation AND {RBAC} "
            "ORDER BY allocation_percentage DESC LIMIT :limit",
            "portfolio_id",
            [
                Slot("min_allocation", "float", required=True, minimum=0, maximum=100, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "holdings.sector_concentration_by_portfolio",
            "SUM(allocation) grouped by portfolio+sector",
            ["portfolio_holdings"],
            "SELECT portfolio_id, sector, SUM(allocation_percentage) AS sector_allocation, SUM(market_value) AS sector_value "
            "FROM portfolio_holdings WHERE {RBAC} GROUP BY portfolio_id, sector "
            "HAVING sector = :sector OR :sector IS NULL "
            "ORDER BY sector_allocation DESC LIMIT :limit",
            "portfolio_id",
            [
                Slot("sector", "str", nullable=True, default=None),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "holdings.top_by_market_value",
            "Top-N holdings by market_value",
            ["portfolio_holdings"],
            "SELECT holding_id, portfolio_id, asset_name, asset_type, sector, allocation_percentage, market_value, buy_price, buy_date, last_updated "
            "FROM portfolio_holdings WHERE {RBAC} ORDER BY market_value DESC LIMIT :limit",
            "portfolio_id",
            [Slot("limit", "int", default=5, minimum=1, maximum=200)],
        ),
        _t(
            "risk_logs.by_score_threshold",
            "Asset risk log entries with risk_score at or above a threshold",
            ["asset_risk_logs"],
            "SELECT risk_id, asset_name, risk_type, risk_score, risk_level, risk_description, assessment_date, escalation_flag "
            "FROM asset_risk_logs WHERE risk_score >= :min_score AND {RBAC} ORDER BY risk_score DESC LIMIT :limit",
            "asset_via_holdings",
            [
                Slot("min_score", "int", required=True, minimum=0, maximum=100, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "risk_logs.by_asset",
            "All risk entries for named assets",
            ["asset_risk_logs"],
            "SELECT risk_id, asset_name, risk_type, risk_score, risk_level, risk_description, assessment_date, escalation_flag "
            "FROM asset_risk_logs WHERE lower(asset_name) LIKE :asset_name AND {RBAC} ORDER BY assessment_date DESC LIMIT :limit",
            "asset_via_holdings",
            [
                Slot("asset_name", "str", required=True, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "risk_logs.by_level",
            "Entries with a given risk_level",
            ["asset_risk_logs"],
            "SELECT risk_id, asset_name, risk_type, risk_score, risk_level, risk_description, assessment_date, escalation_flag "
            "FROM asset_risk_logs WHERE risk_level = :risk_level AND {RBAC} ORDER BY risk_score DESC LIMIT :limit",
            "asset_via_holdings",
            [
                Slot("risk_level", "enum", required=True, choices=RISK_LEVELS, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "risk_logs.escalation_flagged",
            "Rows with escalation_flag = TRUE",
            ["asset_risk_logs"],
            "SELECT risk_id, asset_name, risk_type, risk_score, risk_level, risk_description, assessment_date, escalation_flag "
            "FROM asset_risk_logs WHERE escalation_flag IS TRUE AND {RBAC} ORDER BY risk_score DESC LIMIT :limit",
            "asset_via_holdings",
            [Slot("limit", "int", default=100, minimum=1, maximum=200)],
        ),
        _t(
            "risk_logs.latest_by_asset",
            "Most recent assessment per asset",
            ["asset_risk_logs"],
            "SELECT r.risk_id, r.asset_name, r.risk_type, r.risk_score, r.risk_level, r.risk_description, "
            "r.assessment_date, r.escalation_flag FROM asset_risk_logs r "
            "JOIN (SELECT asset_name, MAX(assessment_date) AS max_date FROM asset_risk_logs GROUP BY asset_name) latest "
            "ON r.asset_name = latest.asset_name AND r.assessment_date = latest.max_date "
            "WHERE {RBAC} ORDER BY r.risk_score DESC LIMIT :limit",
            "asset_via_holdings",
            [Slot("limit", "int", default=100, minimum=1, maximum=200)],
        ),
        _t(
            "market_indicators.latest_by_name_region",
            "Latest value for indicator+region",
            ["market_indicators"],
            "SELECT indicator_id, indicator_name, region, indicator_value, measurement_date, trend_direction "
            "FROM market_indicators WHERE indicator_name = :indicator_name AND region = :region "
            "ORDER BY measurement_date DESC LIMIT :limit",
            "none",
            [
                Slot("indicator_name", "str", required=True, nullable=False),
                Slot("region", "str", required=True, nullable=False),
                Slot("limit", "int", default=5, minimum=1, maximum=200),
            ],
        ),
        _t(
            "market_indicators.by_trend",
            "Indicators with a trend_direction",
            ["market_indicators"],
            "SELECT indicator_id, indicator_name, region, indicator_value, measurement_date, trend_direction "
            "FROM market_indicators WHERE trend_direction = :trend ORDER BY measurement_date DESC LIMIT :limit",
            "none",
            [
                Slot("trend", "str", required=True, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
        _t(
            "decisions.by_portfolio",
            "Decision history for portfolio ids",
            ["investment_decisions"],
            "SELECT decision_id, portfolio_id, asset_name, decision_type, decision_reason, "
            "risk_assessment_reference, decision_date, approval_status "
            "FROM investment_decisions WHERE {RBAC} ORDER BY decision_date DESC LIMIT :limit",
            "portfolio_id",
            [Slot("limit", "int", default=100, minimum=1, maximum=200)],
        ),
        _t(
            "equities.by_symbol",
            "Universe + latest fundamentals for one ticker",
            ["equity_universe", "equity_fundamentals"],
            "SELECT u.symbol, u.company_name, u.sector, u.industry, u.exchange, u.market_cap_cr, "
            "f.period_end, f.period_type, f.pe, f.pb, f.roe, f.roce, f.debt_to_equity, "
            "f.current_ratio, f.sales_growth_3y, f.profit_growth_3y, f.dividend_yield, f.promoter_holding "
            "FROM equity_universe u JOIN equity_fundamentals f ON u.symbol = f.symbol "
            "WHERE u.symbol = :symbol AND u.is_active IS TRUE "
            "ORDER BY f.period_end DESC LIMIT :limit",
            "none",
            [
                Slot("symbol", "str", required=True, nullable=False),
                Slot("limit", "int", default=1, minimum=1, maximum=8),
            ],
        ),
        _t(
            "decisions.by_approval_status",
            "Decisions by approval status",
            ["investment_decisions"],
            "SELECT decision_id, portfolio_id, asset_name, decision_type, decision_reason, "
            "risk_assessment_reference, decision_date, approval_status "
            "FROM investment_decisions WHERE approval_status = :status AND {RBAC} "
            "ORDER BY decision_date DESC LIMIT :limit",
            "portfolio_id",
            [
                Slot("status", "str", required=True, nullable=False),
                Slot("limit", "int", default=100, minimum=1, maximum=200),
            ],
        ),
    ]
}


def catalog() -> List[Dict[str, Any]]:
    return [
        {
            "query_id": t.query_id,
            "description": t.description,
            "tables": t.tables,
            "slots": list(t.slots.keys()),
        }
        for t in TEMPLATES.values()
    ]
