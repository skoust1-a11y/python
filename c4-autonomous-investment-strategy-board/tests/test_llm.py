"""LLM provider selection, validation, fallback, and structured output."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from app.exceptions import ConfigurationError, ProviderError, ProviderNotImplementedError
from app.providers.contracts import LLMProvider, TModel
from app.providers.llm.errors import redact_secrets
from app.providers.llm.factory import build_llm_provider, normalize_llm_provider
from app.providers.llm.fallback import FallbackLLMProvider
from app.providers.llm.openai_compatible import OpenAICompatibleLLMProvider
from app.providers.llm.parsing import parse_structured_output
from app.providers.registry import build_providers
from tests.helpers import make_settings


class _Thesis(BaseModel):
    stance: str
    confidence: float


class _FakeCompletions:
    def __init__(self, content: str | None = "ok", *, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class _FakeClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


class _FakeLLM(LLMProvider):
    def __init__(self, name: str, *, text: str = "ok", error: Exception | None = None) -> None:
        self._name = name
        self._text = text
        self._error = error
        self.complete_calls = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return f"{self._name}-model"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        self.complete_calls += 1
        if self._error is not None:
            raise self._error
        return self._text

    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        self.complete_calls += 1
        if self._error is not None:
            raise self._error
        return response_model.model_validate({"stance": "bullish", "confidence": 0.8})


def _openai_settings(**overrides):
    values = {
        "llm_provider": "openai",
        "openai_llm_api_key": "sk-test-openai",
        "openai_llm_model": "gpt-4o-mini",
    }
    values.update(overrides)
    return make_settings(**values)


def _groq_settings(**overrides):
    values = {
        "llm_provider": "groq",
        "groq_llm_api_key": "gsk_test_groq",
        "groq_llm_model": "llama-3.3-70b-versatile",
    }
    values.update(overrides)
    return make_settings(**values)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("OpenAI", "openai"),
        ("GROQ", "groq"),
        ("gemini", "google"),
        ("google-genai", "google"),
        ("azure", "azure"),
        ("azure-openai", "azure"),
        ("azureopenai", "azure"),
    ],
)
def test_normalize_llm_provider_aliases(raw: str, expected: str) -> None:
    assert normalize_llm_provider(raw) == expected


def test_stub_is_the_default_llm() -> None:
    provider = build_llm_provider(make_settings())
    assert provider.name == "stub"
    assert provider.fallback_name is None


def test_changing_llm_provider_changes_implementation() -> None:
    openai = build_llm_provider(_openai_settings())
    groq = build_llm_provider(_groq_settings())
    google = build_llm_provider(
        make_settings(
            llm_provider="google",
            google_llm_api_key="AIzaSyTestKey00000000000000000000000",
            google_llm_model="gemini-2.0-flash",
        )
    )
    azure = build_llm_provider(
        make_settings(
            llm_provider="azure",
            azure_llm_api_key="azure-test-key",
            azure_llm_model="gpt-4o",
            azure_llm_endpoint="https://example.openai.azure.com",
        )
    )

    assert openai.name == "openai"
    assert openai.model == "gpt-4o-mini"
    assert groq.name == "groq"
    assert groq.model == "llama-3.3-70b-versatile"
    assert google.name == "google"
    assert azure.name == "azure"
    assert len({type(openai), type(groq), type(google), type(azure)}) == 4


def test_gemini_alias_selects_google_adapter() -> None:
    provider = build_llm_provider(
        make_settings(
            llm_provider="gemini",
            google_llm_api_key="AIzaSyTestKey00000000000000000000000",
        )
    )
    assert provider.name == "google"


def test_unknown_llm_provider_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="LLM_PROVIDER"):
        build_llm_provider(make_settings(llm_provider="anthropic"))


def test_openai_requires_api_key() -> None:
    with pytest.raises(ConfigurationError, match="OPENAI_LLM_API_KEY"):
        build_llm_provider(make_settings(llm_provider="openai", openai_llm_api_key=""))


def test_openai_requires_model() -> None:
    with pytest.raises(ConfigurationError, match="OPENAI_LLM_MODEL"):
        build_llm_provider(_openai_settings(openai_llm_model=""))


def test_groq_requires_api_key() -> None:
    with pytest.raises(ConfigurationError, match="GROQ_LLM_API_KEY"):
        build_llm_provider(make_settings(llm_provider="groq", groq_llm_api_key=""))


def test_google_requires_api_key() -> None:
    with pytest.raises(ConfigurationError, match="GOOGLE_LLM_API_KEY"):
        build_llm_provider(make_settings(llm_provider="google", google_llm_api_key=""))


def test_azure_requires_endpoint_and_key() -> None:
    with pytest.raises(ConfigurationError, match="AZURE_LLM_API_KEY"):
        build_llm_provider(
            make_settings(
                llm_provider="azure",
                azure_llm_model="gpt-4o",
                azure_llm_endpoint="https://example.openai.azure.com",
            )
        )
    with pytest.raises(ConfigurationError, match="AZURE_LLM_ENDPOINT"):
        build_llm_provider(
            make_settings(
                llm_provider="azure",
                azure_llm_api_key="azure-test-key",
                azure_llm_model="gpt-4o",
            )
        )


def test_unknown_fallback_provider_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="FALLBACK_LLM_PROVIDER"):
        build_llm_provider(_groq_settings(fallback_llm_provider="not-a-vendor"))


def test_fallback_requires_its_own_credentials() -> None:
    with pytest.raises(ConfigurationError, match="OPENAI_LLM_API_KEY"):
        build_llm_provider(_groq_settings(fallback_llm_provider="openai", openai_llm_api_key=""))


def test_fallback_wrapper_is_wired_from_configuration() -> None:
    provider = build_llm_provider(
        _groq_settings(
            fallback_llm_provider="openai",
            openai_llm_api_key="sk-test-openai",
            openai_llm_model="gpt-4o-mini",
        )
    )
    assert isinstance(provider, FallbackLLMProvider)
    assert provider.name == "groq"
    assert provider.fallback_name == "openai"


def test_identical_fallback_is_ignored() -> None:
    provider = build_llm_provider(_groq_settings(fallback_llm_provider="GROQ"))
    assert not isinstance(provider, FallbackLLMProvider)
    assert provider.name == "groq"


def test_build_providers_uses_configured_llm() -> None:
    providers = build_providers(_openai_settings())
    assert providers.llm.name == "openai"
    assert providers.market_data.name == "stub"


def test_runtime_fallback_uses_secondary_provider() -> None:
    primary = _FakeLLM("groq", error=ProviderError("primary down"))
    fallback = _FakeLLM("openai", text="from-fallback")
    provider = FallbackLLMProvider(primary, fallback)

    assert provider.complete("hello") == "from-fallback"
    assert primary.complete_calls == 1
    assert fallback.complete_calls == 1


def test_runtime_fallback_for_structured_output() -> None:
    primary = _FakeLLM("groq", error=ProviderError("primary down"))
    fallback = _FakeLLM("openai")
    provider = FallbackLLMProvider(primary, fallback)

    result = provider.complete_structured("hello", _Thesis)
    assert result.stance == "bullish"
    assert result.confidence == 0.8


def test_fallback_is_not_used_when_primary_succeeds() -> None:
    primary = _FakeLLM("groq", text="from-primary")
    fallback = _FakeLLM("openai", text="from-fallback")
    provider = FallbackLLMProvider(primary, fallback)

    assert provider.complete("hello") == "from-primary"
    assert fallback.complete_calls == 0


def test_openai_compatible_complete_and_structured_output() -> None:
    completions = _FakeCompletions('{"stance": "bearish", "confidence": 0.4}')
    provider = OpenAICompatibleLLMProvider(
        name="openai",
        model="gpt-4o-mini",
        client=_FakeClient(completions),
        timeout_seconds=15,
        api_key="sk-secret-value",
    )

    assert provider.complete("summarize") == '{"stance": "bearish", "confidence": 0.4}'
    result = provider.complete_structured("view", _Thesis)
    assert result == _Thesis(stance="bearish", confidence=0.4)
    assert completions.calls[1]["response_format"] == {"type": "json_object"}
    assert completions.calls[1]["timeout"] == 15
    assert completions.calls[1]["model"] == "gpt-4o-mini"


def test_timeout_is_wrapped_and_secrets_are_redacted() -> None:
    completions = _FakeCompletions(
        error=TimeoutError("request to api with sk-secret-value timed out")
    )
    provider = OpenAICompatibleLLMProvider(
        name="groq",
        model="llama-3.3-70b-versatile",
        client=_FakeClient(completions),
        timeout_seconds=5,
        api_key="sk-secret-value",
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.complete("hello")
    assert "timed out" in exc_info.value.message.lower()
    assert "sk-secret-value" not in exc_info.value.message
    assert "[REDACTED]" in exc_info.value.message


def test_redact_secrets_strips_common_key_shapes() -> None:
    leaked = "Authorization: Bearer sk-proj-abc123 gsk_live_abc AIzaSySecret"
    redacted = redact_secrets(leaked, extra_secrets=["AIzaSySecret"])
    assert "sk-proj-abc123" not in redacted
    assert "gsk_live_abc" not in redacted
    assert "AIzaSySecret" not in redacted


def test_parse_structured_output_accepts_fenced_json() -> None:
    text = """```json
    {"stance": "hold", "confidence": 0.5}
    ```"""
    parsed = parse_structured_output(text, _Thesis)
    assert parsed.stance == "hold"


def test_stub_complete_is_not_implemented() -> None:
    provider = build_llm_provider(make_settings())
    with pytest.raises(ProviderNotImplementedError):
        provider.complete("hello")
    with pytest.raises(ProviderNotImplementedError):
        provider.complete_structured("hello", _Thesis)


def test_instantiation_logs_do_not_include_api_keys(caplog) -> None:
    import logging

    caplog.set_level(logging.INFO)
    build_llm_provider(
        _groq_settings(
            fallback_llm_provider="openai",
            openai_llm_api_key="sk-test-openai",
        )
    )
    combined = caplog.text
    assert "gsk_test_groq" not in combined
    assert "sk-test-openai" not in combined


def test_create_app_instantiates_configured_llm() -> None:
    from app.main import create_app

    application = create_app(_openai_settings(app_env="test"))
    assert application.state.providers.llm.name == "openai"
    assert application.state.providers.llm.model == "gpt-4o-mini"


def test_health_does_not_expose_llm_api_keys() -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings = _groq_settings(
        fallback_llm_provider="openai",
        openai_llm_api_key="sk-test-openai",
        app_env="test",
    )
    client = TestClient(create_app(settings))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["providers"]["llm"] == "groq"
    body = response.text
    assert "gsk_test_groq" not in body
    assert "sk-test-openai" not in body
    assert "api_key" not in body.lower()


def test_agents_depend_on_llm_contract_not_vendor_sdks() -> None:
    from pathlib import Path

    agents_root = Path("app/agents")
    for path in agents_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "openai" not in source
        assert "google.genai" not in source
        assert "app.providers.llm.openai" not in source
        assert "app.providers.llm.groq" not in source
        assert "app.providers.llm.google" not in source
        assert "app.providers.llm.azure" not in source
    assert "from app.providers.registry import ProviderBundle" in (
        agents_root / "base.py"
    ).read_text(encoding="utf-8")
