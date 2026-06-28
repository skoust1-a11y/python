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
from app.rag.context_builder import LegalContextBuilder
from app.rag.merge import (
    MergeStats,
    external_results_to_nodes,
    merge_retrieval_results,
    sql_results_to_nodes,
)
from app.rag.retriever import LegalDocumentRetriever
from app.rag.synthesizer import LegalResponseSynthesizer
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.search_service import SearchService
from app.services.sql_query_executor import SqlQueryExecutor, SqlRetrievalResult
from app.services.sql_query_planner import SqlQueryPlan, SqlQueryPlanner


@dataclass
class HybridPipelineResult:
    """Output from hybrid or SQL-only retrieval paths."""

    answer: str
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
    sql_planner: SqlQueryPlanner | None = None
    external_search_service: ExternalLegalSearchService | None = None
    context_builder: LegalContextBuilder = field(default_factory=LegalContextBuilder)
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

    def _build_synthesizer(self, provider: str | None = None) -> LegalResponseSynthesizer:
        llm = self.llm_service.get_llm(provider)
        return LegalResponseSynthesizer(llm)

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
        """Run SQL + vector retrieval in parallel, merge, dedupe, and synthesize."""
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
            max_results=(top_k or self.top_k) * 2,
        )

        return await self._synthesize(
            question,
            merged_nodes,
            sql_result=sql_result,
            vector_count=len(vector_nodes),
            external_count=len(external_nodes),
            merge_stats=merge_stats,
            external_search=external_search,
            routing_explanation=plan.explanation,
            provider=provider,
            mode="hybrid",
        )

    async def run_sql(
        self,
        question: str,
        plan: SqlQueryPlan,
        *,
        document_id: UUID | None = None,
        provider: str | None = None,
    ) -> HybridPipelineResult:
        """Run structured SQL retrieval only and synthesize an answer."""
        executor = SqlQueryExecutor(self.session)
        sql_result = await executor.execute(plan, document_id=document_id)
        nodes = sql_results_to_nodes(sql_result)

        return await self._synthesize(
            question,
            nodes,
            sql_result=sql_result,
            vector_count=0,
            merge_stats=None,
            routing_explanation=plan.explanation,
            provider=provider,
            mode="sql",
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

    async def _synthesize(
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
    ) -> HybridPipelineResult:
        built_context = self.context_builder.build(nodes)
        synthesizer = self._build_synthesizer(provider)
        if mode in {"hybrid", "sql"} and built_context.context_text:
            answer = await synthesizer.synthesize_from_context(
                question,
                built_context.context_text,
            )
        else:
            answer = await synthesizer.synthesize(question, nodes)
        confidence = compute_confidence_score(nodes)
        active_provider = provider or settings.DEFAULT_LLM_PROVIDER

        sources = [
            {
                "document_id": source.document_id,
                "chunk_index": source.chunk_index,
                "excerpt": source.excerpt,
                "score": source.score,
                "citation_label": source.citation_label,
                "source_type": source.metadata.get("source_type", "vector"),
                "entity_id": source.metadata.get("entity_id"),
                "entity_type": source.metadata.get("entity_type"),
                "metadata": source.metadata,
            }
            for source in built_context.sources
        ]

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

        return HybridPipelineResult(
            answer=answer,
            sources=sources,
            structured_metadata=_serialize_sql_result(sql_result),
            explanation=explanation,
            confidence_score=confidence,
            provider=active_provider,
            retrieved_count=len(nodes),
            vector_count=vector_count,
            sql_count=sql_result.total_count,
            external_count=external_count,
            merge_stats=merge_stats,
            external_search=external_search,
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
                f"After reciprocal-rank fusion and deduplication, "
                f"{merge_stats.merged_count} unique source(s) were used "
                f"({merge_stats.duplicates_removed} duplicate(s) removed)."
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
