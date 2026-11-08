import pytest

from app.core.config import get_settings
from app.core.langfuse import available, emit_query


def test_langfuse_off_without_keys(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    get_settings.cache_clear()
    assert available() is False


def test_emit_is_noop_without_keys(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    get_settings.cache_clear()
    called = []
    monkeypatch.setattr("app.core.langfuse._post", lambda *a, **k: called.append(a))
    emit_query(
        user_id="u_analyst",
        session_id="sess_test01",
        trace_id="trc_test01",
        query="List portfolios categorized as High risk.",
        answer="ok",
        category="C2_SQL",
        outcome="answered",
        synthesis="deterministic",
        latency_ms=10,
        cost_usd=0.0,
        agents=["router"],
        spans=[],
    )
    assert called == []


def test_emit_posts_when_keys_set(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    get_settings.cache_clear()
    posted = {}
    monkeypatch.setattr("app.core.langfuse._post", lambda path, payload, headers=None: posted.update({path: (payload, headers)}))
    try:
        emit_query(
            user_id="u_analyst",
            session_id="sess_test01",
            trace_id="trc_test01",
            query="q",
            answer="a",
            category="C1_RAG",
            outcome="answered",
            synthesis="llama-3.3-70b-versatile",
            latency_ms=8,
            cost_usd=0.0,
            agents=["synthesis"],
            spans=[
                {"name": "synthesis", "step": 2, "start": "2026-01-01T00:00:01Z", "end": "2026-01-01T00:00:02Z"},
                {"name": "router", "step": 1, "start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:00:01Z"},
            ],
        )
        otlp, headers = posted["/api/public/otel/v1/traces"]
        assert headers == {"x-langfuse-ingestion-version": "4"}
        spans = {s["name"]: s for s in otlp["resourceSpans"][0]["scopeSpans"][0]["spans"]}
        kind = {n: next(a["value"]["stringValue"] for a in s["attributes"] if a["key"] == "langfuse.observation.type") for n, s in spans.items()}
        assert kind == {"query": "agent", "router": "chain", "synthesis": "chain", "llm": "generation"}
        meta = {a["key"]: a["value"].get("stringValue") for a in spans["router"]["attributes"]}
        assert meta["langfuse.observation.metadata.langgraph_node"] == "router"
        assert meta["langfuse.observation.metadata.langgraph_step"] == "1"
        assert meta["langfuse.trace.metadata.retrieval_weights"] == "vector=0.4 lexical=0.6"
        assert not any(a["key"].endswith("langgraph_node") for a in spans["query"]["attributes"])
        assert "parentSpanId" not in spans["query"]
        assert spans["router"]["parentSpanId"] == spans["query"]["spanId"]
        assert spans["llm"]["parentSpanId"] == spans["synthesis"]["spanId"]
        assert spans["query"]["startTimeUnixNano"] == spans["router"]["startTimeUnixNano"] == str(1767225600 * 10**9)
        assert spans["query"]["endTimeUnixNano"] == spans["synthesis"]["endTimeUnixNano"]
        assert len({s["traceId"] for s in spans.values()}) == 1
        batch = posted["/api/public/ingestion"][0]["batch"]
        assert {item["body"]["traceId"] for item in batch} == {spans["query"]["traceId"]}
        names = {item["body"]["name"] for item in batch if item["type"] == "score-create"}
        assert names == {
            "answered",
            "confidence",
            "attributed",
            "current_quotes",
            "current_news",
            "current_fresh",
        }
    finally:
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        get_settings.cache_clear()


@pytest.mark.parametrize("synthesis,level", [("deterministic", None), ("deterministic_fallback", "ERROR"), ("groq", "")])
def test_llm_generation_only_when_llm_called(monkeypatch, synthesis, level):
    get_settings.cache_clear()
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    get_settings.cache_clear()
    posted = {}
    monkeypatch.setattr("app.core.langfuse._post", lambda path, payload, headers=None: posted.update({path: payload}))
    try:
        emit_query(
            user_id="u", session_id="s", trace_id="t", query="q", answer="a", category="C1_RAG",
            outcome="answered", synthesis=synthesis, latency_ms=1, cost_usd=0.0, agents=[],
            spans=[{"name": "synthesis", "start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:00:01Z"}],
        )
        spans = {s["name"]: s for s in posted["/api/public/otel/v1/traces"]["resourceSpans"][0]["scopeSpans"][0]["spans"]}
        if level is None:
            assert "llm" not in spans
        else:
            attrs = {a["key"]: a["value"].get("stringValue") for a in spans["llm"]["attributes"]}
            assert attrs.get("langfuse.observation.level", "") == level
    finally:
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        get_settings.cache_clear()


def test_emit_swallows_post_errors(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    get_settings.cache_clear()

    def boom(*_args, **_kwargs):
        raise RuntimeError("langfuse down")

    monkeypatch.setattr("app.core.langfuse._post", boom)
    try:
        emit_query(
            user_id="u_analyst",
            session_id="sess_test01",
            trace_id="trc_test01",
            query="q",
            answer="a",
            category="C1_RAG",
            outcome="answered",
            synthesis="deterministic_fallback",
            latency_ms=8,
            cost_usd=0.0,
            agents=[],
            spans=[],
        )
    finally:
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        get_settings.cache_clear()
