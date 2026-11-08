"""Deterministic tools used by agents (calculations, parsing, I/O helpers).

Tools must not embed provider-specific clients. Data retrieval belongs in
provider adapters; numeric work belongs in Python tools, not the LLM.
"""

from app.tools.base import Tool
from app.tools.fundamentals import (
    classify_financial_health,
    classify_profitability,
    growth_rate,
    latest_statement,
    safe_ratio,
)
from app.tools.market import (
    classify_trend,
    price_momentum,
    realized_volatility,
    relative_performance,
    simple_moving_average,
    total_return,
)
from app.tools.optimization import optimize_portfolio
from app.tools.portfolio import parse_portfolio_file, validate_upload_file
from app.tools.risk import (
    classify_concentration,
    classify_diversification,
    herfindahl_hirschman_index,
    max_drawdown,
    mean_pairwise_correlation,
)

__all__ = [
    "Tool",
    "classify_concentration",
    "classify_diversification",
    "classify_financial_health",
    "classify_profitability",
    "classify_trend",
    "growth_rate",
    "herfindahl_hirschman_index",
    "latest_statement",
    "max_drawdown",
    "mean_pairwise_correlation",
    "optimize_portfolio",
    "parse_portfolio_file",
    "price_momentum",
    "realized_volatility",
    "relative_performance",
    "safe_ratio",
    "simple_moving_average",
    "total_return",
    "validate_upload_file",
]
