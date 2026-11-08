"""Tests for configurable AI response mode prompts."""

import pytest

from app.prompts.manager import PromptManager
from app.prompts.shared import EVIDENCE_NONE_FOUND_RESPONSE
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
    assert "EVIDENCE mode" in strict
    assert "ANALYSIS mode" in analysis
    assert strict != analysis


def test_strict_system_prompt_extracts_clauses_not_answers(prompt_manager: PromptManager):
    strict = prompt_manager.get_system_prompt("strict")
    assert "extract" in strict.lower() or "evidence" in strict.lower()
    assert "do not answer" in strict.lower() or "not an answer engine" in strict.lower()
    assert EVIDENCE_NONE_FOUND_RESPONSE in strict


def test_strict_user_prompt_requires_evidence_format(prompt_manager: PromptManager):
    prompt = prompt_manager.get_user_prompt(
        "strict",
        context="[Source 1] Sample clause text.",
        question="What are the payment terms?",
    )
    assert EVIDENCE_NONE_FOUND_RESPONSE in prompt
    assert "Sample clause text." in prompt
    assert "What are the payment terms?" in prompt
    assert "EVIDENCE MODE" in prompt
    assert "Do NOT answer" in prompt


def test_strict_user_prompt_formats_context_and_question(prompt_manager: PromptManager):
    prompt = prompt_manager.get_user_prompt(
        "strict",
        context="[Source 1] Payment is due within 30 days.",
        question="When is payment due?",
    )
    assert "[Source 1] Payment is due within 30 days." in prompt
    assert "When is payment due?" in prompt


def test_analysis_user_prompt_includes_explain_and_evidence_inputs(prompt_manager: PromptManager):
    prompt = prompt_manager.get_user_prompt(
        "analysis",
        context="[Source 1] Sample clause text.",
        question="What are the payment terms?",
        explain_answer="Payment is due in 30 days [Source 1].",
        evidence_output="### Direct — [Source 1]\n- **Clause:** Payment is due in 30 days.",
    )
    assert "Sample clause text." in prompt
    assert "What are the payment terms?" in prompt
    assert "ANALYSIS MODE" in prompt
    assert "Payment is due in 30 days [Source 1]." in prompt
    assert "EXPLAIN ANSWER" in prompt
    assert "EVIDENCE EXTRACTION" in prompt
    assert "```json" in prompt_manager.get_system_prompt("analysis")


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
    assert "EVIDENCE mode" in messages[0].content
    assert "What is the term?" in messages[1].content
