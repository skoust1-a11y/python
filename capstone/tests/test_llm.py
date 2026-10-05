from app.core.config import get_settings
from app.core.llm import LLMError, available, complete, embed_texts, resolve
from app.graph import _llm_or_fallback


def _no_keys(monkeypatch):
    for key in ("LLM_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    get_settings.cache_clear()


def test_unavailable_without_key(monkeypatch):
    _no_keys(monkeypatch)
    assert available() is False


def test_complete_without_key_raises(monkeypatch):
    _no_keys(monkeypatch)
    try:
        complete("sys", "user")
        assert False, "expected LLMError"
    except LLMError as exc:
        assert "no_api_key" in str(exc)


def test_embed_without_key_is_empty(monkeypatch):
    _no_keys(monkeypatch)
    assert embed_texts(["hello"]) == []


def test_fallback_when_no_key(monkeypatch):
    _no_keys(monkeypatch)
    text, mode = _llm_or_fallback("q", "grounded evidence", "C1_RAG")
    assert text == "grounded evidence"
    assert mode == "deterministic"


def test_fallback_when_llm_errors(monkeypatch):
    monkeypatch.setattr("app.graph.llm_available", lambda: True)

    def boom(*_a, **_k):
        raise LLMError("http_503")

    monkeypatch.setattr("app.graph.llm_complete", boom)
    text, mode = _llm_or_fallback("q", "grounded evidence", "C1_RAG")
    assert text == "grounded evidence"
    assert mode == "deterministic_fallback"


def test_uses_llm_text_when_present(monkeypatch):
    monkeypatch.setattr("app.graph.llm_available", lambda: True)
    monkeypatch.setattr("app.graph.llm_complete", lambda *_a, **_k: ("LLM rewrite", {"total": 3}))
    text, mode = _llm_or_fallback("q", "grounded evidence", "C1_RAG")
    assert text == "LLM rewrite"
    assert mode == resolve().agent


def test_quota_skips_retries_and_falls_back(monkeypatch):
    from app.core import llm as llmod

    _no_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "google")
    monkeypatch.setenv("GEMINI_MODEL_AGENT", "gemini-3.8-flash")
    get_settings.cache_clear()
    calls = []

    class Res:
        def __init__(self, status, body, text=""):
            self.status_code, self._body, self.text = status, body, text

        def json(self):
            return self._body

    class Cli:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, **k):
            calls.append(url)
            if "openai.com" in url:
                return Res(429, {}, '{"error": {"type": "insufficient_quota"}}')
            return Res(200, {"choices": [{"message": {"content": "from gemini"}}], "usage": {"total_tokens": 5}})

    monkeypatch.setattr(llmod.httpx, "Client", Cli)
    assert available() is True
    text, usage = complete("sys", "user")
    assert (text, usage["model"]) == ("from gemini", "gemini-3.8-flash")
    assert sum("openai.com" in u for u in calls) == 1
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "")
    get_settings.cache_clear()
    try:
        complete("sys", "user")
        assert False, "expected LLMError"
    except LLMError as exc:
        assert str(exc) == "insufficient_quota"
    monkeypatch.delenv("LLM_FALLBACK_PROVIDER")
    get_settings.cache_clear()


def test_resolve_openai_grok_gemini_groq_ollama(monkeypatch):
    cases = (
        ("openai", "https://api.openai.com/v1", "gpt-4o"),
        ("grok", "https://api.x.ai/v1", "grok-4"),
        ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.8-flash"),
        ("groq", "https://api.groq.com/openai/v1", "openai/gpt-oss-20b"),
        ("ollama", "http://127.0.0.1:11434/v1", "llama3.2"),
    )
    monkeypatch.setenv("GEMINI_MODEL_AGENT", "gemini-3.8-flash")
    monkeypatch.setenv("GROQ_MODEL_AGENT", "openai/gpt-oss-20b")
    for provider, base, agent in cases:
        get_settings.cache_clear()
        monkeypatch.setenv("LLM_PROVIDER", provider)
        get_settings.cache_clear()
        endpoint = resolve()
        assert endpoint.provider == provider
        assert endpoint.base_url == base
        assert endpoint.agent == agent
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    get_settings.cache_clear()
