"""LangGraph compilation entrypoint for the investment strategy board.

The compiled graph owns orchestration. Specialist agents run as nodes through
the execution wrapper. The manager plans and synthesizes; it does not start
its own graph. Reflection is a single optional critique with at most one
controlled re-analysis cycle.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.base import Agent, AgentContext
from app.workflow.nodes import (
    COLLECT,
    CRITIQUE,
    DETECT_CONFLICTS,
    FUNDAMENTAL,
    JOIN,
    MARKET,
    OPTIMIZE,
    PLAN,
    REANALYZE,
    RISK,
    SYNTHESIZE,
    collect_node,
    critique_node,
    detect_conflicts_node,
    join_node,
    plan_node,
    reanalyze_node,
    route_after_conflicts,
    route_after_critique,
    route_after_join,
    route_after_plan,
    route_after_reanalyze,
    route_after_risk,
    specialist_node,
    synthesize_node,
)
from app.workflow.runtime import WorkflowRuntime, resolve_specialists
from app.workflow.state import InvestmentState

logger = logging.getLogger("app.workflow")


def build_strategy_graph(
    context: AgentContext | None = None,
    *,
    specialists: Mapping[str, Agent] | None = None,
) -> Any:
    """Compile and return the strategy board graph.

    Pass `context` (and optional specialist doubles) for a single run. Calling
    with no arguments compiles against the process provider bundle.
    """
    runtime = _runtime_from(context, specialists)
    builder = StateGraph(InvestmentState)
    builder.add_node(PLAN, _bind(plan_node, runtime))
    builder.add_node(MARKET, _bind(_specialist(MARKET), runtime))
    builder.add_node(FUNDAMENTAL, _bind(_specialist(FUNDAMENTAL), runtime))
    builder.add_node(JOIN, _bind(join_node, runtime))
    builder.add_node(RISK, _bind(_specialist(RISK), runtime))
    builder.add_node(OPTIMIZE, _bind(_specialist(OPTIMIZE), runtime))
    builder.add_node(COLLECT, _bind(collect_node, runtime))
    builder.add_node(DETECT_CONFLICTS, _bind(detect_conflicts_node, runtime))
    builder.add_node(CRITIQUE, _bind(critique_node, runtime))
    builder.add_node(REANALYZE, _bind(reanalyze_node, runtime))
    builder.add_node(SYNTHESIZE, _bind(synthesize_node, runtime))

    builder.add_edge(START, PLAN)
    builder.add_conditional_edges(
        PLAN,
        _bind_route(route_after_plan, runtime),
        [MARKET, FUNDAMENTAL, JOIN, SYNTHESIZE],
    )
    builder.add_edge(MARKET, JOIN)
    builder.add_edge(FUNDAMENTAL, JOIN)
    builder.add_conditional_edges(
        JOIN,
        _bind_route(route_after_join, runtime),
        [RISK, OPTIMIZE, COLLECT],
    )
    builder.add_conditional_edges(
        RISK,
        _bind_route(route_after_risk, runtime),
        [OPTIMIZE, COLLECT],
    )
    builder.add_edge(OPTIMIZE, COLLECT)
    builder.add_edge(COLLECT, DETECT_CONFLICTS)
    builder.add_conditional_edges(
        DETECT_CONFLICTS,
        _bind_route(route_after_conflicts, runtime),
        [CRITIQUE, SYNTHESIZE],
    )
    builder.add_conditional_edges(
        CRITIQUE,
        _bind_route(route_after_critique, runtime),
        [REANALYZE, SYNTHESIZE],
    )
    builder.add_conditional_edges(
        REANALYZE,
        _bind_route(route_after_reanalyze, runtime),
        [MARKET, FUNDAMENTAL, JOIN, RISK, OPTIMIZE, COLLECT],
    )
    builder.add_edge(SYNTHESIZE, END)
    logger.info("workflow.compiled nodes=%s", ",".join(sorted(builder.nodes)))
    return builder.compile()


def invoke_strategy_board(
    state: InvestmentState,
    context: AgentContext,
    *,
    specialists: Mapping[str, Agent] | None = None,
) -> InvestmentState:
    """Run the compiled graph once and return the typed final state."""
    from app.workflow.observability import create_langfuse_handler, record_workflow_evaluations

    graph = build_strategy_graph(context, specialists=specialists)
    handler = create_langfuse_handler(state)
    config = {"callbacks": [handler]} if handler is not None else None
    result = graph.invoke(state, config=config)
    if handler is not None:
        record_workflow_evaluations(handler, state, result)
    return result  # type: ignore[return-value]


def _runtime_from(
    context: AgentContext | None,
    specialists: Mapping[str, Agent] | None,
) -> WorkflowRuntime:
    if context is None:
        from app.config.settings import get_settings
        from app.providers.registry import build_providers

        context = AgentContext(providers=build_providers(get_settings()))
    resolved = resolve_specialists(
        context, dict(specialists) if specialists is not None else None
    )
    return WorkflowRuntime(context=context, specialists=resolved)


def _specialist(name: str) -> Callable[[InvestmentState, WorkflowRuntime], dict[str, Any]]:
    def node(state: InvestmentState, runtime: WorkflowRuntime) -> dict[str, Any]:
        return specialist_node(state, runtime, name)

    node.__name__ = name.replace("-", "_")
    return node


def _bind(
    fn: Callable[[InvestmentState, WorkflowRuntime], dict[str, Any]],
    runtime: WorkflowRuntime,
) -> Callable[[InvestmentState], dict[str, Any]]:
    def node(state: InvestmentState) -> dict[str, Any]:
        return fn(state, runtime)

    node.__name__ = getattr(fn, "__name__", "node")
    return node


def _bind_route(
    fn: Callable[[InvestmentState, WorkflowRuntime], Any],
    runtime: WorkflowRuntime,
) -> Callable[[InvestmentState], Any]:
    def route(state: InvestmentState) -> Any:
        return fn(state, runtime)

    route.__name__ = getattr(fn, "__name__", "route")
    return route
