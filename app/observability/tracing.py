"""Langfuse tracing integration for RAG queries, pipelines, and evaluation runs."""

from __future__ import annotations

import base64
import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Generator, TypeVar

import httpx
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from app.core.config import settings
from app.utils.google_http import build_requests_session, build_ssl_context

logger = logging.getLogger(__name__)

_langfuse_initialized = False
F = TypeVar("F", bound=Callable[..., Any])
LANGFUSE_EXPORT_TIMEOUT_SECONDS = 30.0


def is_tracing_enabled() -> bool:
    """Return True when Langfuse tracing is configured and enabled."""
    if not settings.ENABLE_LANGFUSE:
        return False
    return bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)


def _langfuse_base_url() -> str:
    base = (settings.LANGFUSE_BASE_URL or settings.LANGFUSE_HOST or "").strip()
    return base or "https://cloud.langfuse.com"


def _build_langfuse_otlp_exporter(
    *,
    base_url: str,
    public_key: str,
    secret_key: str,
    timeout: float = LANGFUSE_EXPORT_TIMEOUT_SECONDS,
) -> OTLPSpanExporter:
    """Create an OTLP exporter that uses the app's Windows-safe SSL configuration."""
    from langfuse._version import __version__ as langfuse_version

    basic_auth_header = "Basic " + base64.b64encode(
        f"{public_key}:{secret_key}".encode("utf-8")
    ).decode("ascii")
    headers = {
        "Authorization": basic_auth_header,
        "x-langfuse-sdk-name": "python",
        "x-langfuse-sdk-version": langfuse_version,
        "x-langfuse-public-key": public_key,
        "x-langfuse-ingestion-version": "4",
    }
    endpoint = f"{base_url.rstrip('/')}/api/public/otel/v1/traces"
    return OTLPSpanExporter(
        endpoint=endpoint,
        headers=headers,
        timeout=timeout,
        session=build_requests_session(),
    )


def init_langfuse_client():
    """Initialize the Langfuse SDK singleton when tracing is enabled."""
    global _langfuse_initialized
    if _langfuse_initialized:
        from langfuse import get_client

        return get_client()

    if not is_tracing_enabled():
        os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
        _langfuse_initialized = True
        logger.info("Langfuse tracing disabled")
        return None

    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
    os.environ.setdefault("LANGFUSE_BASE_URL", _langfuse_base_url())
    os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "true")
    os.environ.setdefault("LANGFUSE_TRACING_ENVIRONMENT", settings.APP_ENV)

    from langfuse import Langfuse

    base_url = _langfuse_base_url()
    Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        base_url=base_url,
        environment=settings.APP_ENV,
        tracing_enabled=True,
        timeout=int(LANGFUSE_EXPORT_TIMEOUT_SECONDS),
        httpx_client=httpx.Client(
            verify=build_ssl_context(),
            timeout=LANGFUSE_EXPORT_TIMEOUT_SECONDS,
        ),
        span_exporter=_build_langfuse_otlp_exporter(
            base_url=base_url,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
        ),
    )
    _langfuse_initialized = True
    logger.info("Langfuse tracing initialized (environment=%s)", settings.APP_ENV)

    from langfuse import get_client

    return get_client()


def get_langfuse_client():
    """Return the Langfuse client when tracing is enabled, else None."""
    if not is_tracing_enabled():
        return None
    client = init_langfuse_client()
    if client is None:
        return None
    if getattr(client, "disabled", False):
        return None
    return client


def flush_traces() -> None:
    """Flush queued Langfuse events."""
    client = get_langfuse_client()
    if client is not None:
        client.flush()


def shutdown_tracing() -> None:
    """Flush and shut down the Langfuse client."""
    client = get_langfuse_client()
    if client is not None:
        client.shutdown()


def observe(*args: Any, **kwargs: Any):
    """Langfuse @observe decorator, or a no-op when tracing is disabled."""
    if not is_tracing_enabled():
        if args and callable(args[0]):
            return args[0]

        def passthrough(func: F) -> F:
            return func

        return passthrough

    from langfuse import observe as langfuse_observe

    return langfuse_observe(*args, **kwargs)


def traced(name: str | None = None, *, as_type: str | None = None, **kwargs: Any):
    """Decorator alias for observe with explicit span naming."""
    observe_kwargs = dict(kwargs)
    if name is not None:
        observe_kwargs["name"] = name
    if as_type is not None:
        observe_kwargs["as_type"] = as_type
    return observe(**observe_kwargs)


def mask_sources_for_trace(sources: list[dict]) -> list[dict]:
    """Strip full chunk text from sources before sending to Langfuse."""
    masked: list[dict] = []
    for source in sources:
        entry = {key: value for key, value in source.items() if key != "full_text"}
        excerpt = entry.get("excerpt")
        if isinstance(excerpt, str) and len(excerpt) > 300:
            entry["excerpt"] = excerpt[:300] + "..."
        masked.append(entry)
    return masked


def update_current_span(
    *,
    input: Any | None = None,
    output: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Update the active Langfuse span when tracing is enabled."""
    if not is_tracing_enabled():
        return
    from langfuse import get_client

    client = get_client()
    if getattr(client, "disabled", False):
        return
    if input is not None or output is not None or metadata:
        client.update_current_span(
            input=input,
            output=output,
            metadata=metadata or {},
        )


def update_current_generation(
    *,
    input: Any | None = None,
    output: Any | None = None,
    model: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Update the active Langfuse generation span when tracing is enabled."""
    if not is_tracing_enabled():
        return
    from langfuse import get_client

    client = get_client()
    if getattr(client, "disabled", False):
        return
    client.update_current_generation(
        input=input,
        output=output,
        model=model,
        metadata=metadata or {},
    )


def _score_trace(observation: Any, *, name: str, value: float) -> None:
    """Attach a score to the Langfuse trace backing an observation."""
    score_trace = getattr(observation, "score_trace", None)
    if callable(score_trace):
        score_trace(name=name, value=value)
        return
    observation.score(name=name, value=value)


def score_trace_metric(observation: Any, *, name: str, value: float) -> None:
    """Public helper for attaching trace-level scores from call sites."""
    _score_trace(observation, name=name, value=value)


@contextmanager
def trace_query(
    *,
    name: str,
    question: str,
    metadata: dict[str, Any] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    tags: list[str] | None = None,
) -> Generator[Any, None, None]:
    """Create a Langfuse trace span for a query or evaluation item."""
    client = get_langfuse_client()
    if client is None:
        yield None
        return

    trace_metadata = {
        "feature": "legal-query",
        **(metadata or {}),
    }
    trace_tags = ["legaldoc-navigator", *(tags or [])]

    from langfuse import propagate_attributes

    with propagate_attributes(
        session_id=session_id,
        user_id=user_id,
        metadata=trace_metadata,
        tags=trace_tags,
        environment=settings.APP_ENV,
    ):
        with client.start_as_current_observation(
            name=name,
            as_type="chain",
            input={"question": question},
            metadata=trace_metadata,
        ) as observation:
            try:
                yield observation
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
        output={
            "answer": answer,
            "sources": mask_sources_for_trace(sources),
        },
        metadata={
            "route": route,
            "confidence_score": confidence_score,
            **(metadata or {}),
        },
    )
    _score_trace(trace, name="latency_ms", value=latency_ms)
    _score_trace(trace, name="cost_usd", value=cost_usd)
    _score_trace(trace, name="confidence_score", value=confidence_score)


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

    def _apply_scores(observation: Any) -> None:
        for metric_name, value in scores.items():
            if value is not None:
                _score_trace(observation, name=metric_name, value=float(value))

    if trace is not None:
        _apply_scores(trace)
    else:
        with client.start_as_current_observation(
            name=f"eval-{run_name}",
            metadata={"type": "benchmark_evaluation"},
        ) as eval_trace:
            _apply_scores(eval_trace)
    flush_traces()


def trace_llm_messages(messages: Any) -> list[dict[str, str]]:
    """Serialize chat messages for trace input without leaking full RAG context."""
    serialized: list[dict[str, str]] = []
    for message in messages:
        role = getattr(message, "role", None)
        content = getattr(message, "content", None)
        if role is None and hasattr(message, "role"):
            role = message.role
        if content is None and hasattr(message, "content"):
            content = message.content
        role_value = str(getattr(role, "value", role) or "unknown")
        text = str(content or "")
        if len(text) > 500:
            text = text[:500] + "..."
        serialized.append({"role": role_value, "content": text})
    return serialized
