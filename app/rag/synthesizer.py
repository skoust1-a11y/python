"""LLM response synthesizer with source-aware, citation-grounded generation."""

import asyncio

from llama_index.core.schema import NodeWithScore

from app.guardrails.constants import STRICT_INSUFFICIENT_INFO_RESPONSE
from app.prompts.manager import PromptManager
from app.prompts.types import RESPONSE_MODES
from app.rag.context_builder import LegalContextBuilder
from app.services.llm_service import LLMService
from app.models.mode_responses import ModeResponses, empty_mode_responses


class LegalResponseSynthesizer:
    """Generate grounded legal Q&A answers with mandatory source citations."""

    def __init__(
        self,
        llm_service: LLMService,
        prompt_manager: PromptManager,
        *,
        provider: str | None = None,
    ) -> None:
        self._llm_service = llm_service
        self._prompt_manager = prompt_manager
        self._provider = provider

    @property
    def llm(self):
        return self._llm_service.get_llm(self._provider)

    async def synthesize(
        self,
        question: str,
        nodes: list[NodeWithScore],
        *,
        response_mode: str | None = None,
    ) -> str:
        """Generate a grounded answer from retrieved nodes."""
        active_mode = self._prompt_manager.normalize_response_mode(response_mode)
        if not nodes:
            if active_mode == "strict":
                return STRICT_INSUFFICIENT_INFO_RESPONSE
            return (
                "I could not find relevant information in the indexed documents to "
                "answer this question. Please ensure documents are uploaded and indexed."
            )

        built_context = LegalContextBuilder().build(nodes)
        return await self.synthesize_from_context(
            question,
            built_context.context_text,
            mode="rag",
            response_mode=response_mode,
        )

    async def synthesize_from_context(
        self,
        question: str,
        context_text: str,
        *,
        mode: str = "hybrid",
        response_mode: str | None = None,
    ) -> str:
        """Generate an answer from pre-built context (RAG, hybrid, or SQL paths)."""
        active_mode = self._prompt_manager.normalize_response_mode(response_mode)
        if not context_text.strip():
            if active_mode == "strict":
                return STRICT_INSUFFICIENT_INFO_RESPONSE
            return (
                "I could not find relevant structured or document information to "
                "answer this question."
            )

        messages = self._prompt_manager.build_synthesis_messages(
            context=context_text,
            question=question,
            response_mode=response_mode,
            retrieval_mode=mode,
        )
        answer, _provider_used = await self._llm_service.achat_with_fallback(
            messages,
            provider=self._provider,
        )
        return answer

    async def synthesize_all_modes_from_context(
        self,
        question: str,
        context_text: str,
        *,
        mode: str = "rag",
    ) -> ModeResponses:
        """Generate one answer per response mode from the same retrieved context."""
        if not context_text.strip():
            return empty_mode_responses(
                strict_message=STRICT_INSUFFICIENT_INFO_RESPONSE,
                default_message=(
                    "I could not find relevant structured or document information to "
                    "answer this question."
                ),
            )

        tasks = [
            self.synthesize_from_context(
                question,
                context_text,
                mode=mode,
                response_mode=response_mode,
            )
            for response_mode in RESPONSE_MODES
        ]
        strict, explain, analysis = await asyncio.gather(*tasks)
        return ModeResponses(
            strict=strict,
            explain=explain,
            analysis=analysis,
        )
