"""Hybrid retrieval pipeline — vector + SQL with merge, context, and synthesis."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from llama_index.core.schema import QueryBundle
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.mcp.models import ExternalSearchResult
from app.mcp.search import ExternalLegalSearchService
from app.rag.confidence import compute_confidence_score
from app.rag.context_builder import LegalContextBuilder, internal_source_to_dict
from app.rag.merge import (
    MergeStats,
    external_results_to_nodes,
    merge_retrieval_results,
    sql_results_to_nodes,
)
from app.rag.ranking import rank_retrieval_results
from app.rag.retriever import LegalDocumentRetriever
from app.prompts.manager import PromptManager
from app.rag.retrieval_result import PipelineRetrievalResult
from app.rag.synthesizer import LegalResponseSynthesizer
from app.models.mode_responses import ModeResponses
from app.services.context_compression_service import ContextCompressionService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.search_service import SearchService
from app.services.sql_query_executor import SqlQueryExecutor, SqlRetrievalResult
from app.services.sql_query_planner import SqlQueryPlan, SqlQueryPlanner
from app.utils.evidence_validator import filter_public_sources, validate_retrieved_evidence


@dataclass
class HybridPipelineResult:
    """Output from hybrid or SQL-only retrieval paths."""

    answer: str
    responses: ModeResponses
    sources: list[dict]
    structured_metadata: dict
    explanation: str
    confidence_score: float
    provider: str
    retrieved_count: int
    vector_count: int = 0
    sql_count: int = 0
    external_count: int = 0
    merge_stats: MergeStats | None = None
    external_search: ExternalSearchResult | None = None


@dataclass
class HybridPipeline:
    """Orchestrate parallel SQL + vector retrieval, merge, and LLM synthesis."""

    session: AsyncSession
    llm_service: LLMService
    embedding_service: EmbeddingService
    prompt_manager: PromptManager
    sql_planner: SqlQueryPlanner | None = None
    external_search_service: ExternalLegalSearchService | None = None
    context_builder: LegalContextBuilder = field(default_factory=LegalContextBuilder)
    context_compression_service: ContextCompressionService = field(
        default_factory=ContextCompressionService
    )
    top_k: int = field(default_factory=lambda: settings.TOP_K_RETRIEVAL)
    similarity_threshold: float = field(
        default_factory=lambda: settings.SIMILARITY_THRESHOLD
    )

    def _build_retriever(
        self,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> LegalDocumentRetriever:
        search_service = SearchService(self.session, self.embedding_service)
        return LegalDocumentRetriever(
            search_service,
            top_k=top_k or self.top_k,
            similarity_threshold=(
                similarity_threshold
                if similarity_threshold is not None
                else self.similarity_threshold
            ),
            document_id=document_id,
        )

    def _build_synthesizer(
        self,
        provider: str | None = None,
        top_k: int | None = None,
    ) -> LegalResponseSynthesizer:
        return LegalResponseSynthesizer(
            self.llm_service,
            self.prompt_manager,
            provider=provider,
            top_k=top_k or self.top_k,
        )

    async def retrieve_hybrid(
        self,
        question: str,
        plan: SqlQueryPlan,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        provider: str | None = None,
    ) -> PipelineRetrievalResult:
        """Run SQL + vector retrieval once; build shared context for all modes."""
        executor = SqlQueryExecutor(self.session)
        retriever = self._build_retriever(
            document_id=document_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        sql_task = asyncio.create_task(
            executor.execute(plan, document_id=document_id)
        )
        vector_task = asyncio.create_task(
            retriever.aretrieve(QueryBundle(query_str=question))
        )
        external_task = asyncio.create_task(
            self._search_external(question)
        )

        sql_result, vector_nodes, external_search = await asyncio.gather(
            sql_task,
            vector_task,
            external_task,
        )
        external_nodes = external_results_to_nodes(external_search.hits)

        merged_nodes, merge_stats = merge_retrieval_results(
            vector_nodes,
            sql_result,
            external_nodes=external_nodes,
        )
        ranked_nodes, _ranking_stats = rank_retrieval_results(
            merged_nodes,
            question,
            top_k=top_k,
        )

        return self._build_retrieval_result(
            question,
            ranked_nodes,
            sql_result=sql_result,
            vector_count=len(vector_nodes),
            external_count=len(external_nodes),
            merge_stats=merge_stats,
            external_search=external_search,
            routing_explanation=plan.explanation,
            provider=provider,
            mode="hybrid",
        )

    async def retrieve_sql(
        self,
        question: str,
        plan: SqlQueryPlan,
        *,
        document_id: UUID | None = None,
        provider: str | None = None,
    ) -> PipelineRetrievalResult:
        """Run structured SQL retrieval once; build shared context for all modes."""
        executor = SqlQueryExecutor(self.session)
        sql_result = await executor.execute(plan, document_id=document_id)
        sql_nodes = sql_results_to_nodes(sql_result)
        nodes, _ranking_stats = rank_retrieval_results(
            sql_nodes,
            question,
            top_k=self.top_k,
        )

        return self._build_retrieval_result(
            question,
            nodes,
            sql_result=sql_result,
            vector_count=0,
            merge_stats=None,
            routing_explanation=plan.explanation,
            provider=provider,
            mode="sql",
        )

    async def synthesize_all_modes(
        self,
        question: str,
        retrieval: PipelineRetrievalResult,
        *,
        provider: str | None = None,
    ) -> ModeResponses:
        synthesizer = self._build_synthesizer(provider or retrieval.provider, top_k=self.top_k)
        return await synthesizer.synthesize_all_modes_from_context(
            question,
            retrieval.context_text,
            mode=retrieval.retrieval_mode,
            sources=retrieval.sources,
            retrieved_count=retrieval.retrieved_count,
            evidence_sufficient=retrieval.evidence_sufficient,
        )

    @staticmethod
    def _public_sources(retrieval: PipelineRetrievalResult) -> list[dict]:
        """Return retrieval sources — see ``RAGPipeline._public_sources``."""
        return filter_public_sources(
            retrieval.sources,
            evidence_sufficient=retrieval.evidence_sufficient,
        )

    async def run_hybrid(
        self,
        question: str,
        plan: SqlQueryPlan,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        provider: str | None = None,
    ) -> HybridPipelineResult:
        """Retrieve once, then synthesize all response modes."""
        retrieval = await self.retrieve_hybrid(
            question,
            plan,
            document_id=document_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            provider=provider,
        )
        responses = await self.synthesize_all_modes(
            question,
            retrieval,
            provider=provider,
        )
        return self._to_pipeline_result(retrieval, responses)

    async def run_sql(
        self,
        question: str,
        plan: SqlQueryPlan,
        *,
        document_id: UUID | None = None,
        provider: str | None = None,
    ) -> HybridPipelineResult:
        """Retrieve once, then synthesize all response modes."""
        retrieval = await self.retrieve_sql(
            question,
            plan,
            document_id=document_id,
            provider=provider,
        )
        responses = await self.synthesize_all_modes(
            question,
            retrieval,
            provider=provider,
        )
        return self._to_pipeline_result(retrieval, responses)

    def _build_retrieval_result(
        self,
        question: str,
        nodes: list,
        *,
        sql_result: SqlRetrievalResult,
        vector_count: int,
        external_count: int = 0,
        merge_stats: MergeStats | None,
        external_search: ExternalSearchResult | None = None,
        routing_explanation: str,
        provider: str | None,
        mode: str,
    ) -> PipelineRetrievalResult:
        built_context = self.context_builder.build(nodes)
        compressed = self.context_compression_service.compress(
            built_context,
            question,
        )
        confidence = compute_confidence_score(nodes)
        active_provider = provider or settings.DEFAULT_LLM_PROVIDER
        sources = [internal_source_to_dict(source) for source in built_context.sources]
        explanation = _build_explanation(
            mode=mode,
            routing_explanation=routing_explanation,
            vector_count=vector_count,
            sql_count=sql_result.total_count,
            external_count=external_count,
            merge_stats=merge_stats,
            external_search=external_search,
            final_count=len(nodes),
        )

        return PipelineRetrievalResult(
            context_text=compressed.context_text,
            sources=sources,
            nodes=nodes,
            confidence_score=confidence,
            provider=active_provider,
            retrieved_count=len(nodes),
            retrieval_mode=mode,
            explanation=explanation,
            structured_metadata=_serialize_metadata(sql_result),
            vector_count=vector_count,
            sql_count=sql_result.total_count,
            **self._evidence_validation_fields(question, sources),
        )

    @staticmethod
    def _evidence_validation_fields(
        question: str,
        sources: list[dict],
    ) -> dict[str, bool | float]:
        validation = validate_retrieved_evidence(question, sources)
        return {
            "evidence_sufficient": validation.sufficient,
            "evidence_relevance": validation.relevance,
        }

    def _to_pipeline_result(
        self,
        retrieval: PipelineRetrievalResult,
        responses: ModeResponses,
    ) -> HybridPipelineResult:
        public_sources = self._public_sources(retrieval)
        confidence_score = (
            retrieval.confidence_score
            if retrieval.evidence_sufficient
            else retrieval.evidence_relevance
        )
        return HybridPipelineResult(
            answer=responses.explain,
            responses=responses,
            sources=public_sources,
            structured_metadata=retrieval.structured_metadata or _empty_metadata(),
            explanation=retrieval.explanation,
            confidence_score=confidence_score,
            provider=retrieval.provider,
            retrieved_count=retrieval.retrieved_count,
            vector_count=retrieval.vector_count,
            sql_count=retrieval.sql_count,
        )

    async def _search_external(self, question: str) -> ExternalSearchResult:
        """Query external legal MCP databases; failures return empty results."""
        if self.external_search_service is None or not self.external_search_service.is_available:
            return ExternalSearchResult()
        try:
            return await self.external_search_service.search(question)
        except Exception:
            return ExternalSearchResult(
                errors=["External MCP search unavailable due to an unexpected error."],
            )


def _build_explanation(
    *,
    mode: str,
    routing_explanation: str,
    vector_count: int,
    sql_count: int,
    external_count: int = 0,
    merge_stats: MergeStats | None,
    external_search: ExternalSearchResult | None = None,
    final_count: int,
) -> str:
    parts = [routing_explanation]

    if mode == "hybrid":
        retrieval_parts = [
            f"{vector_count} vector chunk(s)",
            f"{sql_count} structured record(s)",
        ]
        if external_count:
            retrieval_parts.append(f"{external_count} external legal source(s)")
        parts.append(f"Retrieved {' and '.join(retrieval_parts)}.")
        if merge_stats is not None:
            parts.append(
                f"After reciprocal-rank fusion, deduplication, overlap merging, "
                f"and relevance ranking, the top {final_count} chunk(s) were sent "
                f"to the LLM ({merge_stats.duplicates_removed} duplicate(s) removed "
                f"during fusion)."
            )
        if external_search and external_search.had_failures:
            parts.append(
                "Some external legal databases were unavailable; "
                "results may be incomplete."
            )
    elif mode == "sql":
        parts.append(f"Retrieved {sql_count} structured record(s) from the database.")
    else:
        parts.append(f"Used {final_count} retrieved source(s).")

    return " ".join(part for part in parts if part)


def _empty_metadata() -> dict:
    return {
        "contracts": [],
        "clauses": [],
        "cases": [],
        "metadata_records": [],
        "plan_explanation": None,
        "total_count": 0,
    }


def _serialize_metadata(sql_result: SqlRetrievalResult) -> dict:
    return _serialize_sql_result(sql_result)


def _serialize_sql_result(sql_result: SqlRetrievalResult) -> dict:
    from dataclasses import asdict

    return {
        "contracts": [asdict(item) for item in sql_result.contracts],
        "clauses": [asdict(item) for item in sql_result.clauses],
        "cases": [asdict(item) for item in sql_result.cases],
        "metadata_records": [
            {
                "entity_type": record.entity_type,
                "entity_id": str(record.entity_id),
                "fields": _json_safe(record.fields),
                "custom_metadata": record.custom_metadata,
            }
            for record in sql_result.metadata_records
        ],
        "plan_explanation": sql_result.plan_explanation,
        "total_count": sql_result.total_count,
    }


def _json_safe(value):
    from datetime import date, datetime
    from uuid import UUID

    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value
