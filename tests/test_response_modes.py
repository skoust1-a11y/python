"""Tests for configurable AI response mode prompts."""

import pytest

from app.guardrails.constants import STRICT_INSUFFICIENT_INFO_RESPONSE
from app.prompts.manager import PromptManager
from app.prompts.types import DEFAULT_RESPONSE_MODE


@pytest.fixture
def prompt_manager() -> PromptManager:
    return PromptManager()


def test_normalize_response_mode_defaults_invalid(prompt_manager: PromptManager):
    assert prompt_manager.normalize_response_mode(None) == DEFAULT_RESPONSE_MODE
    assert prompt_manager.normalize_response_mode("unknown") == DEFAULT_RESPONSE_MODE


def test_normalize_response_mode_accepts_valid_modes(prompt_manager: PromptManager):
    for mode in ("strict", "explain", "analysis"):
        assert prompt_manager.normalize_response_mode(mode) == mode


def test_get_system_prompt_varies_by_mode(prompt_manager: PromptManager):
    strict = prompt_manager.get_system_prompt("strict")
    analysis = prompt_manager.get_system_prompt("analysis")
    assert "STRICT mode" in strict
    assert "ANALYSIS mode" in analysis
    assert strict != analysis


def test_strict_system_prompt_forbids_prior_knowledge(prompt_manager: PromptManager):
    strict = prompt_manager.get_system_prompt("strict")
    assert "prior knowledge" in strict.lower() or "outside information" in strict.lower()
    assert "general legal knowledge" in strict.lower()
    assert "No hallucination" in strict
    assert STRICT_INSUFFICIENT_INFO_RESPONSE in strict


def test_strict_user_prompt_requires_exact_insufficient_message(
    prompt_manager: PromptManager,
):
    prompt = prompt_manager.get_user_prompt(
        "strict",
        context="[Source 1] Sample clause text.",
        question="What are the payment terms?",
    )
    assert STRICT_INSUFFICIENT_INFO_RESPONSE in prompt
    assert "Sample clause text." in prompt
    assert "What are the payment terms?" in prompt
    assert "STRICT MODE" in prompt
    assert "[Source N]" in prompt
    assert "Do NOT use general knowledge" in prompt


def test_strict_user_prompt_formats_context_and_question(prompt_manager: PromptManager):
    prompt = prompt_manager.get_user_prompt(
        "strict",
        context="[Source 1] Payment is due within 30 days.",
        question="When is payment due?",
    )
    assert "[Source 1] Payment is due within 30 days." in prompt
    assert "When is payment due?" in prompt


def test_analysis_user_prompt_includes_structured_sections(prompt_manager: PromptManager):
    prompt = prompt_manager.get_user_prompt(
        "analysis",
        context="[Source 1] Sample clause text.",
        question="What are the payment terms?",
    )
    assert "Sample clause text." in prompt
    assert "What are the payment terms?" in prompt
    assert "ANALYSIS MODE" in prompt
    assert "## Legal Review" in prompt
    assert "## Suggested Follow-up Questions" in prompt


def test_get_user_prompt_hybrid_adds_structured_context_note(prompt_manager: PromptManager):
    rag_prompt = prompt_manager.get_user_prompt(
        "explain",
        context="ctx",
        question="q",
        retrieval_mode="rag",
    )
    hybrid_prompt = prompt_manager.get_user_prompt(
        "explain",
        context="ctx",
        question="q",
        retrieval_mode="hybrid",
    )
    assert "structured database records" in hybrid_prompt
    assert "structured database records" not in rag_prompt


def test_build_synthesis_messages_returns_system_and_user(prompt_manager: PromptManager):
    messages = prompt_manager.build_synthesis_messages(
        context="[Source 1] clause",
        question="What is the term?",
        response_mode="strict",
        retrieval_mode="rag",
    )
    assert len(messages) == 2
    assert "STRICT mode" in messages[0].content
    assert "What is the term?" in messages[1].content
    assert STRICT_INSUFFICIENT_INFO_RESPONSE in messages[1].content
