from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

# Langfuse draws the agent graph only when some observation type is not span/event/generation;
# langgraph_node/langgraph_step metadata makes it draw real LangGraph edges instead of guessing from timing.
_TYPES = {
    "input_guard": "guardrail",
    "escalation_check": "guardrail",
    "retrieval": "retriever",
    "stock_cache": "retriever",
    "portfolio_eval": "tool",
    "market_data": "tool",
    "risk": "evaluator",
    "finalize": "span",
}


def available() -> bool:
    settings = get_settings()
    return bool(settings.langfuse_public_key.strip() and settings.langfuse_secret_key.strip())


def emit_query(
    *,
    user_id: str,
    session_id: str,
    trace_id: str,
    query: str,
    answer: str,
    category: str,
    outcome: str,
    synthesis: str,
    latency_ms: int,
    cost_usd: float,
    agents: List[str],
    spans: List[Dict[str, Any]],
    confidence: float = 0.0,
    citation_count: int = 0,
    evidence_mode: str = "corpus",
    current_quotes: int = 0,
    current_news: int = 0,
    stale_quotes: int = 0,
) -> None:
    if not available():
        return
    settings = get_settings()
    env = settings.app_env
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    spans = sorted(spans, key=lambda s: s.get("start") or now)
    tid, root = hashlib.md5(trace_id.encode()).hexdigest(), uuid.uuid4().hex[:16]
    shared = {
        "langfuse.trace.name": "query",
        "langfuse.user.id": user_id,
        "langfuse.session.id": session_id,
        "langfuse.trace.tags": ["frii", category, outcome],
        "langfuse.environment": env,
        "langfuse.trace.metadata.trace_id": trace_id,
        "langfuse.trace.metadata.category": category,
        "langfuse.trace.metadata.outcome": outcome,
        "langfuse.trace.metadata.retrieval_weights": "vector={} lexical={}".format(
            settings.retrieval_vector_weight, settings.retrieval_lexical_weight
        ),
    }
    otel = [
        _span(
            tid, root, None, "query",
            spans[0].get("start", now) if spans else now,
            max((s.get("end", now) for s in spans), default=now),
            dict(
                shared,
                **{
                    "langfuse.observation.type": "agent",
                    "langfuse.observation.input": query,
                    "langfuse.observation.output": answer,
                    "langfuse.observation.metadata.synthesis": synthesis,
                    "langfuse.observation.metadata.latency_ms": latency_ms,
                    "langfuse.observation.metadata.cost_usd": cost_usd,
                    "langfuse.observation.metadata.agents": json.dumps(agents),
                },
            ),
        )
    ]
    for s in spans:
        sid, name = uuid.uuid4().hex[:16], str(s.get("name") or "node")
        start, end = s.get("start", now), s.get("end", now)
        otel.append(
            _span(tid, sid, root, name, start, end, dict(
                shared,
                **{"langfuse.observation.type": _TYPES.get(name, "chain"),
                   "langfuse.observation.metadata.duration_ms": s.get("duration_ms"),
                   "langfuse.observation.metadata.langgraph_node": name if s.get("step") else None,
                   "langfuse.observation.metadata.langgraph_step": s.get("step")},
            ))
        )
        if name == "synthesis" and synthesis != "deterministic":
            failed = synthesis == "deterministic_fallback"
            otel.append(
                _span(tid, uuid.uuid4().hex[:16], sid, "llm", start, end, dict(
                    shared,
                    **{"langfuse.observation.type": "generation",
                       "langfuse.observation.model.name": synthesis,
                       "langfuse.observation.input": query,
                       "langfuse.observation.output": answer,
                       "langfuse.observation.level": "ERROR" if failed else None,
                       "langfuse.observation.status_message": "LLM call failed; grounded text used" if failed else None},
                ))
            )
    fresh = 1.0 if current_quotes and not stale_quotes else 0.0
    scores = [
        {
            "id": str(uuid.uuid4()),
            "type": "score-create",
            "timestamp": now,
            "body": {
                "id": "scr_" + uuid.uuid4().hex[:16],
                "traceId": tid,
                "name": name,
                "value": value,
                "dataType": "NUMERIC",
                "comment": comment,
                "environment": env,
            },
        }
        for name, value, comment in (
            ("answered", 1.0 if outcome == "answered" else 0.0, outcome),
            ("confidence", float(confidence), category),
            ("attributed", 1.0 if citation_count else 0.0, "{} citation(s)".format(citation_count)),
            ("current_quotes", float(current_quotes), evidence_mode),
            ("current_news", float(current_news), evidence_mode),
            ("current_fresh", fresh, "stale={}".format(stale_quotes)),
        )
    ]
    try:
        _post(
            "/api/public/otel/v1/traces",
            {"resourceSpans": [{
                "resource": {"attributes": [_attr("service.name", "frii")]},
                "scopeSpans": [{"scope": {"name": "frii"}, "spans": otel}],
            }]},
            {"x-langfuse-ingestion-version": "4"},
        )
        _post("/api/public/ingestion", {"batch": scores})
    except Exception as exc:
        get_logger("langfuse").error("langfuse_failed", error=str(exc))


def _ns(iso: str) -> str:
    return str(int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1e9))


def _attr(key: str, value: Any) -> Dict[str, Any]:
    if isinstance(value, list):
        return {"key": key, "value": {"arrayValue": {"values": [{"stringValue": str(v)} for v in value]}}}
    return {"key": key, "value": {"stringValue": str(value)}}


def _span(
    tid: str, sid: str, parent: Optional[str], name: str, start: str, end: str, attrs: Dict[str, Any]
) -> Dict[str, Any]:
    span = {
        "traceId": tid,
        "spanId": sid,
        "name": name,
        "kind": 1,
        "startTimeUnixNano": _ns(start),
        "endTimeUnixNano": _ns(end),
        "attributes": [_attr(k, v) for k, v in attrs.items() if v is not None],
    }
    if parent:
        span["parentSpanId"] = parent
    return span


def _post(path: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> None:
    settings = get_settings()
    with httpx.Client(timeout=8.0) as client:  # ponytail: sync POST; background if 8s starts blocking queries
        res = client.post(
            settings.langfuse_base_url.rstrip("/") + path,
            json=payload,
            headers=headers,
            auth=(settings.langfuse_public_key.strip(), settings.langfuse_secret_key.strip()),
        )
        res.raise_for_status()
        if res.status_code == 207 and res.json().get("errors"):
            raise RuntimeError("ingestion errors: {}".format(res.json()["errors"]))
