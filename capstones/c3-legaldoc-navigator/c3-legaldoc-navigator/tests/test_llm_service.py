"""Unit tests for multi-provider LLM service."""

import pytest

from app.core.exceptions import LLMProviderError
from app.services.llm_service import LLMService, normalize_llm_provider


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("google", "google"),
        ("gemini", "google"),
        ("GROQ", "groq"),
        ("azureopenai", "azureopenai"),
        ("azure_openai", "azureopenai"),
        ("azure", "azureopenai"),
    ],
)
def test_normalize_llm_provider_aliases(raw: str, expected: str) -> None:
    assert normalize_llm_provider(raw) == expected


def test_unknown_provider_raises() -> None:
    service = LLMService()
    with pytest.raises(LLMProviderError, match="Unknown provider"):
        service._create_llm("unsupported-provider")
