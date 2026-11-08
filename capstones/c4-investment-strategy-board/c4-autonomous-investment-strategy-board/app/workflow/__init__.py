"""LangGraph workflow package.

The compiled graph coordinates manager planning, specialist nodes, conflict
detection, a single optional critique with at most one re-analysis cycle, and
structured synthesis. Agents must not instantiate independent graphs.
"""

from typing import Any

from app.workflow.state import (
    AgentResultSnapshot,
    BoardState,
    ConflictRecord,
    CritiqueRecord,
    ExecutionMetadata,
    FinalRecommendation,
    FundamentalDataSnapshot,
    InvestmentProfile,
    InvestmentState,
    MarketDataSnapshot,
    NewsSnapshot,
    OptimizationResultSnapshot,
    RiskAnalysisSnapshot,
    SelectedStock,
    UserRequest,
    create_investment_state,
    merge_investment_state,
)

__all__ = [
    "AgentResultSnapshot",
    "BoardState",
    "ConflictRecord",
    "CritiqueRecord",
    "ExecutionMetadata",
    "FinalRecommendation",
    "FundamentalDataSnapshot",
    "InvestmentProfile",
    "InvestmentState",
    "MarketDataSnapshot",
    "NewsSnapshot",
    "OptimizationResultSnapshot",
    "RiskAnalysisSnapshot",
    "SelectedStock",
    "UserRequest",
    "build_strategy_graph",
    "create_investment_state",
    "invoke_strategy_board",
    "merge_investment_state",
]


def __getattr__(name: str) -> Any:
    if name in {"build_strategy_graph", "invoke_strategy_board"}:
        from app.workflow.graph import build_strategy_graph, invoke_strategy_board

        exports = {
            "build_strategy_graph": build_strategy_graph,
            "invoke_strategy_board": invoke_strategy_board,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
