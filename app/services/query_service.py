"""RAG query business logic with routing and guardrail enforcement."""

import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.evaluation.cost import estimate_cost
from app.evaluation.tracing import log_query_result, trace_query
from app.guardrails.validator import GuardrailValidator
from app.prompts.types import RESPONSE_MODES
from app.rag.confidence import VERIFICATION_NOTICE, classify_confidence_level
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.models.mode_responses import ModeResponses
from app.services.query_dispatcher import QueryDispatcher, QueryResult
from app.routing.router import Router
from app.services.sql_query_planner import SqlQueryPlanner


class QueryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        dispatcher: QueryDispatcher | None = None,
        guardrails: GuardrailValidator | None = None,
        llm_service: LLMService | None = None,
        embedding_service: EmbeddingService | None = None,
        router: Router | None = None,
        sql_planner: SqlQueryPlanner | None = None,
    ) -> None:
        llm = llm_service or LLMService()
        self._dispatcher = dispatcher or QueryDispatcher(
            session,
            router=router,
            sql_planner=sql_planner,
            llm_service=llm,
            embedding_service=embedding_service or EmbeddingService(),
        )
        self.guardrails = guardrails or GuardrailValidator()

    async def ask(
        self,
        question: str,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        provider: str | None = None,
    ) -> QueryResult:
        self.guardrails.validate_query(question)

        with trace_query(
            name="legal-query",
            question=question,
            metadata={
                "document_id": str(document_id) if document_id else None,
            },
        ) as trace:
            start = time.perf_counter()
            response = await self._dispatcher.dispatch(
                question,
                document_id=document_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                provider=provider,
            )

            validated_responses = self._apply_guardrails_to_all_modes(
                response.responses,
                sources=response.sources,
                question=question,
            )
            response.responses = validated_responses
            response.answer = validated_responses.explain

            level = classify_confidence_level(response.confidence_score)
            response.confidence_level = level.value
            response.verification_notice = (
                VERIFICATION_NOTICE if level.value == "Low" else None
            )

            latency_ms = (time.perf_counter() - start) * 1000
            response.latency_ms = latency_ms

            if settings.ENABLE_LANGFUSE:
                contexts = [
                    source.get("full_text") or source.get("excerpt", "")
                    for source in response.sources
                    if source.get("full_text") or source.get("excerpt")
                ]
                cost = estimate_cost(
                    question=question,
                    answer=response.answer,
                    contexts=contexts,
                )
                log_query_result(
                    trace,
                    answer=response.answer,
                    sources=response.sources,
                    confidence_score=response.confidence_score,
                    route=response.routing.route,
                    latency_ms=latency_ms,
                    cost_usd=cost.total_cost_usd,
                    metadata={"explanation": response.explanation},
                )

            return response

    def _apply_guardrails_to_all_modes(
        self,
        responses: ModeResponses,
        *,
        sources: list[dict],
        question: str,
    ) -> ModeResponses:
        validated: dict[str, str] = {}
        for mode in RESPONSE_MODES:
            guardrail_result = self.guardrails.validate_response_detailed(
                responses.get(mode),
                sources=sources,
                question=question,
                response_mode=mode,
            )
            validated[mode] = guardrail_result.answer
        return ModeResponses.from_dict(validated)
