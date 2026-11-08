"""Backward-compatible re-exports for Langfuse tracing."""

from app.observability.tracing import (
    flush_traces,
    get_langfuse_client,
    init_langfuse_client,
    is_tracing_enabled,
    log_evaluation_scores,
    log_query_result,
    mask_sources_for_trace,
    observe,
    score_trace_metric,
    shutdown_tracing,
    trace_llm_messages,
    trace_query,
    traced,
    update_current_generation,
    update_current_span,
)

__all__ = [
    "flush_traces",
    "get_langfuse_client",
    "init_langfuse_client",
    "is_tracing_enabled",
    "log_evaluation_scores",
    "log_query_result",
    "mask_sources_for_trace",
    "observe",
    "score_trace_metric",
    "shutdown_tracing",
    "trace_llm_messages",
    "trace_query",
    "traced",
    "update_current_generation",
    "update_current_span",
]
