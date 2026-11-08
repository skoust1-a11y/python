"""Tests for multi-mode synthesis orchestration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.mode_responses import ModeResponses
from app.prompts.shared import EVIDENCE_NONE_FOUND_RESPONSE
from app.rag.synthesizer import LegalResponseSynthesizer


@pytest.fixture
def synthesizer() -> LegalResponseSynthesizer:
    llm_service = MagicMock()
    llm_service.achat_with_fallback = AsyncMock(
        side_effect=[
            ("Explain answer.", "openai"),
            ("### Direct — [Source 1]\n- **Clause:** Payment due in 30 days.", "openai"),
        ]
    )
    prompt_manager = MagicMock()
    prompt_manager.build_synthesis_messages = MagicMock(return_value=[])
    return LegalResponseSynthesizer(llm_service, prompt_manager)


@pytest.mark.asyncio
async def test_insufficient_evidence_skips_strict_llm(synthesizer: LegalResponseSynthesizer):
    sources = [
        {
            "score": 0.22,
            "full_text": "Delaware law governs this Agreement.",
            "excerpt": "Delaware law governs this Agreement.",
            "citation_label": "[Source 1]",
        },
    ]
    result = await synthesizer.synthesize_all_modes_from_context(
        "Who won the FIFA World Cup?",
        "[Source 1] Delaware law governs this Agreement.",
        sources=sources,
        retrieved_count=1,
    )

    assert result.strict == EVIDENCE_NONE_FOUND_RESPONSE
    assert result.explain == "Explain answer."
    assert synthesizer._llm_service.achat_with_fallback.await_count == 1


@pytest.mark.asyncio
async def test_analysis_mode_skipped_when_disabled(synthesizer: LegalResponseSynthesizer):
    sources = [
        {
            "score": 0.90,
            "full_text": "Payment is due within thirty days of invoice.",
            "excerpt": "Payment is due within thirty days of invoice.",
            "citation_label": "[Source 1]",
        },
    ]
    with patch("app.rag.synthesizer.settings.ENABLE_ANALYSIS_MODE", False):
        result = await synthesizer.synthesize_all_modes_from_context(
            "What is the payment due period?",
            "[Source 1] Payment is due within thirty days of invoice.",
            sources=sources,
            retrieved_count=1,
        )

    assert isinstance(result, ModeResponses)
    assert result.analysis == ""
    assert result.analysis_evaluation is None
    assert synthesizer._llm_service.achat_with_fallback.await_count == 2
