"""Route-aware query dispatcher — RAG, SQL, and Hybrid retrieval paths."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.engine import RAGEngine
from app.rag.hybrid_pipeline import HybridPipeline, HybridPipelineResult
from app.rag.pipeline import RAGPipeline
from app.routing.models import RoutingResult
from app.routing.router import Router
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.sql_query_planner import SqlQueryPlanner


@dataclass
class QueryResult:
    """Unified query response across all retrieval routes."""

    answer: str
    sources: list[dict]
    confidence_score: float
    provider: str
    retrieved_count: int
    routing: RoutingResult
    explanation: str
    structured_metadata: dict | None = None
    vector_count: int = 0
    sql_count: int = 0


class QueryDispatcher:
    """Classify queries and execute the appropriate retrieval pipeline."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        router: Router | None = None,
        rag_pipeline: RAGPipeline | None = None,
        hybrid_pipeline: HybridPipeline | None = None,
        sql_planner: SqlQueryPlanner | None = None,
        llm_service: LLMService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._session = session
        self._llm_service = llm_service or LLMService()
        self._embedding_service = embedding_service or EmbeddingService()
        self._router = router or Router(llm_service=self._llm_service)
        self._sql_planner = sql_planner or SqlQueryPlanner(llm_service=self._llm_service)
        self._rag_pipeline = rag_pipeline or RAGPipeline(
            session=session,
            llm_service=self._llm_service,
            embedding_service=self._embedding_service,
        )
        self._hybrid_pipeline = hybrid_pipeline or HybridPipeline(
            session=session,
            llm_service=self._llm_service,
            embedding_service=self._embedding_service,
            sql_planner=self._sql_planner,
        )
        self._rag_engine = RAGEngine(self._rag_pipeline)

    async def dispatch(
        self,
        question: str,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        provider: str | None = None,
    ) -> QueryResult:
        routing = await self._router.route(question, provider=provider)
        route = routing.route

        if route == "hybrid":
            return await self._run_hybrid(
                question,
                routing,
                document_id=document_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                provider=provider,
            )

        if route == "sql":
            return await self._run_sql(
                question,
                routing,
                document_id=document_id,
                provider=provider,
            )

        return await self._run_rag(
            question,
            routing,
            document_id=document_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            provider=provider,
        )

    async def _run_rag(
        self,
        question: str,
        routing: RoutingResult,
        *,
        document_id: UUID | None,
        top_k: int | None,
        similarity_threshold: float | None,
        provider: str | None,
    ) -> QueryResult:
        result = await self._rag_engine.query(
            question,
            document_id=document_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            provider=provider,
        )
        explanation = (
            f"{routing.reason} "
            f"Retrieved {result.retrieved_count} vector chunk(s) via semantic search."
        )
        return QueryResult(
            answer=result.answer,
            sources=result.sources,
            confidence_score=result.confidence_score,
            provider=result.provider,
            retrieved_count=result.retrieved_count,
            routing=routing,
            explanation=explanation.strip(),
            structured_metadata=None,
            vector_count=result.retrieved_count,
            sql_count=0,
        )

    async def _run_sql(
        self,
        question: str,
        routing: RoutingResult,
        *,
        document_id: UUID | None,
        provider: str | None,
    ) -> QueryResult:
        plan = await self._sql_planner.plan(question, provider=provider)
        result = await self._hybrid_pipeline.run_sql(
            question,
            plan,
            document_id=document_id,
            provider=provider,
        )
        return _from_hybrid_result(result, routing)

    async def _run_hybrid(
        self,
        question: str,
        routing: RoutingResult,
        *,
        document_id: UUID | None,
        top_k: int | None,
        similarity_threshold: float | None,
        provider: str | None,
    ) -> QueryResult:
        plan = await self._sql_planner.plan(question, provider=provider)
        result = await self._hybrid_pipeline.run_hybrid(
            question,
            plan,
            document_id=document_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            provider=provider,
        )
        hybrid_result = _from_hybrid_result(result, routing)
        hybrid_result.explanation = (
            f"{routing.reason} {result.explanation}"
        ).strip()
        return hybrid_result


def _from_hybrid_result(
    result: HybridPipelineResult,
    routing: RoutingResult,
) -> QueryResult:
    return QueryResult(
        answer=result.answer,
        sources=result.sources,
        confidence_score=result.confidence_score,
        provider=result.provider or settings.DEFAULT_LLM_PROVIDER,
        retrieved_count=result.retrieved_count,
        routing=routing,
        explanation=result.explanation,
        structured_metadata=result.structured_metadata,
        vector_count=result.vector_count,
        sql_count=result.sql_count,
    )
