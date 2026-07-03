"""Prompt assembly for configurable AI response modes."""

from dataclasses import dataclass

from llama_index.core.llms import ChatMessage, MessageRole

from app.prompts import (
    analysis_prompt,
    explain_prompt,
    strict_prompt,
)
from app.prompts.types import DEFAULT_RESPONSE_MODE, RESPONSE_MODES, ResponseMode

_HYBRID_CONTEXT_NOTE = (
    "Note: context includes both document excerpts and structured database records. "
    "Cite using the labels shown (e.g. [Source N]). "
    "Clearly separate facts from document text vs database metadata.\n\n"
)

_PROMPT_MODULES = {
    "strict": strict_prompt,
    "explain": explain_prompt,
    "analysis": analysis_prompt,
}


@dataclass(frozen=True)
class PromptManager:
    """Select and assemble prompts based on the active response mode."""

    def normalize_response_mode(self, mode: str | None) -> ResponseMode:
        """Return a valid response mode, falling back to the default."""
        if mode and mode in RESPONSE_MODES:
            return mode  # type: ignore[return-value]
        return DEFAULT_RESPONSE_MODE

    def get_system_prompt(self, response_mode: str | None) -> str:
        """Return the system prompt for the given response mode."""
        mode = self.normalize_response_mode(response_mode)
        return _PROMPT_MODULES[mode].SYSTEM_PROMPT

    def get_user_prompt(
        self,
        response_mode: str | None,
        *,
        context: str,
        question: str,
        retrieval_mode: str = "rag",
    ) -> str:
        """Build the user prompt for synthesis using the selected response mode."""
        mode = self.normalize_response_mode(response_mode)
        template = _PROMPT_MODULES[mode].USER_PROMPT_TEMPLATE
        user_content = template.format(context=context, question=question)
        if retrieval_mode in {"hybrid", "sql"}:
            user_content = user_content.replace(
                "Context from legal documents:",
                "Context from legal documents and structured database records:",
                1,
            )
            user_content = _HYBRID_CONTEXT_NOTE + user_content
        return user_content

    def build_synthesis_messages(
        self,
        *,
        context: str,
        question: str,
        response_mode: str | None = None,
        retrieval_mode: str = "rag",
    ) -> list[ChatMessage]:
        """Build chat messages for legal answer synthesis."""
        return [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=self.get_system_prompt(response_mode),
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=self.get_user_prompt(
                    response_mode,
                    context=context,
                    question=question,
                    retrieval_mode=retrieval_mode,
                ),
            ),
        ]
