"""LLM response synthesizer with source-aware, citation-grounded generation."""

import asyncio

from llama_index.core.schema import NodeWithScore

from app.core.config import settings
from app.utils.analysis_parser import format_analysis_markdown, parse_analysis_response
from app.utils.answer_metrics import apply_scores_to_evaluation
from app.models.analysis_evaluation import AnalysisEvaluation
from app.models.mode_responses import ModeResponses, empty_mode_responses
from app.prompts.shared import EVIDENCE_NONE_FOUND_RESPONSE
from app.prompts.manager import PromptManager
from app.rag.context_builder import LegalContextBuilder
from app.services.llm_service import LLMService


def _has_sufficient_evidence(question: str, sources: list[dict]) -> bool:
    """Lazy import avoids a circular dependency through ``app.rag`` package init."""
    from app.utils.evidence_validator import has_sufficient_evidence

    return has_sufficient_evidence(question, sources)


class LegalResponseSynthesizer:
    """Generate grounded legal Q&A answers with mandatory source citations."""

    def __init__(
        self,
        llm_service: LLMService,
        prompt_manager: PromptManager,
        *,
        provider: str | None = None,
        top_k: int = 5,
    ) -> None:
        self._llm_service = llm_service
        self._prompt_manager = prompt_manager
        self._provider = provider
        self._top_k = top_k

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
                return EVIDENCE_NONE_FOUND_RESPONSE
            return (
                "I could not find relevant information in the indexed documents to "
                "answer this question. Please ensure documents are uploaded and indexed."
            )

        built_context = LegalContextBuilder().build(nodes)
        sources = [
            {
                "score": source.score,
                "full_text": source.full_text,
                "excerpt": source.excerpt,
            }
            for source in built_context.sources
        ]
        if active_mode == "strict" and not _has_sufficient_evidence(question, sources):
            return EVIDENCE_NONE_FOUND_RESPONSE

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
        explain_answer: str = "",
        evidence_output: str = "",
    ) -> str:
        """Generate an answer from pre-built context (RAG, hybrid, or SQL paths)."""
        active_mode = self._prompt_manager.normalize_response_mode(response_mode)
        if not context_text.strip():
            if active_mode == "strict":
                return EVIDENCE_NONE_FOUND_RESPONSE
            return (
                "I could not find relevant structured or document information to "
                "answer this question."
            )

        messages = self._prompt_manager.build_synthesis_messages(
            context=context_text,
            question=question,
            response_mode=response_mode,
            retrieval_mode=mode,
            explain_answer=explain_answer,
            evidence_output=evidence_output,
        )
        answer, _provider_used = await self._llm_service.achat_with_fallback(
            messages,
            provider=self._provider,
        )
        return answer

    async def synthesize_analysis(
        self,
        question: str,
        context_text: str,
        *,
        explain_answer: str,
        evidence_output: str,
        mode: str = "rag",
        sources: list[dict] | None = None,
        retrieved_count: int = 0,
    ) -> tuple[str, AnalysisEvaluation | None]:
        """
        Run Analysis mode after Explain and Evidence are available.

        Returns formatted markdown for display and the structured evaluation object.
        """
        raw = await self.synthesize_from_context(
            question,
            context_text,
            mode=mode,
            response_mode="analysis",
            explain_answer=explain_answer,
            evidence_output=evidence_output,
        )
        evaluation = parse_analysis_response(raw)
        if evaluation is None:
            return raw, None

        scored = apply_scores_to_evaluation(
            evaluation,
            sources=sources or [],
            explain_answer=explain_answer,
            retrieved_count=retrieved_count,
            top_k=self._top_k,
        )
        return format_analysis_markdown(scored), scored

    async def synthesize_all_modes_from_context(
        self,
        question: str,
        context_text: str,
        *,
        mode: str = "rag",
        sources: list[dict] | None = None,
        retrieved_count: int = 0,
        evidence_sufficient: bool | None = None,
    ) -> ModeResponses:
        """
        Generate all response modes from the same retrieved context.

        Explain and Evidence run in parallel when evidence quality is sufficient.
        Analysis is optional (controlled by ``ENABLE_ANALYSIS_MODE``) and, when
        enabled, runs afterward so it can evaluate the Explain answer against
        the Evidence extraction.
        """
        if not context_text.strip():
            return empty_mode_responses(
                strict_message=EVIDENCE_NONE_FOUND_RESPONSE,
                default_message=(
                    "I could not find relevant structured or document information to "
                    "answer this question."
                ),
            )

        source_dicts = sources or []
        if evidence_sufficient is None:
            evidence_is_sufficient = _has_sufficient_evidence(question, source_dicts)
        else:
            evidence_is_sufficient = evidence_sufficient

        explain_task = self.synthesize_from_context(
            question,
            context_text,
            mode=mode,
            response_mode="explain",
        )
        if evidence_is_sufficient:
            strict_task = self.synthesize_from_context(
                question,
                context_text,
                mode=mode,
                response_mode="strict",
            )
            explain, strict = await asyncio.gather(explain_task, strict_task)
        else:
            # Off-topic or weak retrieval: skip strict LLM to avoid extracting
            # irrelevant clauses. Explain still synthesizes from context.
            explain = await explain_task
            strict = EVIDENCE_NONE_FOUND_RESPONSE

        if settings.ENABLE_ANALYSIS_MODE:
            analysis_text, evaluation = await self.synthesize_analysis(
                question,
                context_text,
                explain_answer=explain,
                evidence_output=strict,
                mode=mode,
                sources=source_dicts,
                retrieved_count=retrieved_count,
            )
        else:
            analysis_text, evaluation = "", None

        return ModeResponses(
            strict=strict,
            explain=explain,
            analysis=analysis_text,
            analysis_evaluation=evaluation,
        )
