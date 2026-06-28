"""Langfuse tracing integration for RAG query and evaluation runs."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

from app.core.config import settings

logger = logging.getLogger(__name__)

_langfuse_client = None


def get_langfuse_client():
    """Return a singleton Langfuse client when tracing is enabled."""
    global _langfuse_client
    if not settings.ENABLE_LANGFUSE:
        return None
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.warning("Langfuse enabled but keys are missing; tracing disabled")
        return None
    if _langfuse_client is None:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    return _langfuse_client


def flush_traces() -> None:
    client = get_langfuse_client()
    if client is not None:
        client.flush()


@contextmanager
def trace_query(
    *,
    name: str,
    question: str,
    metadata: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """Create a Langfuse trace span for a query or evaluation item."""
    client = get_langfuse_client()
    if client is None:
        yield None
        return

    trace = client.trace(
        name=name,
        input={"question": question},
        metadata=metadata or {},
    )
    try:
        yield trace
    finally:
        flush_traces()


def log_query_result(
    trace: Any,
    *,
    answer: str,
    sources: list[dict],
    confidence_score: float,
    route: str,
    latency_ms: float,
    cost_usd: float,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Attach generation output and scores to an active Langfuse trace."""
    if trace is None:
        return

    trace.update(
        output={"answer": answer, "sources": sources},
        metadata={
            "route": route,
            "confidence_score": confidence_score,
            **(metadata or {}),
        },
    )
    trace.score(name="latency_ms", value=latency_ms)
    trace.score(name="cost_usd", value=cost_usd)


def log_evaluation_scores(
    trace: Any,
    *,
    scores: dict[str, float],
    run_name: str,
) -> None:
    """Log RAGAS metric scores to Langfuse."""
    client = get_langfuse_client()
    if client is None:
        return

    eval_trace = trace or client.trace(
        name=f"eval-{run_name}",
        metadata={"type": "benchmark_evaluation"},
    )
    for metric_name, value in scores.items():
        if value is not None:
            eval_trace.score(name=metric_name, value=float(value))
    flush_traces()
