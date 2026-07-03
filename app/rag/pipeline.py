"""Production LlamaIndex RAG pipeline with injectable components."""

from dataclasses import dataclass, field
from uuid import UUID

from llama_index.core.schema import QueryBundle
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.confidence import compute_confidence_score
from app.rag.context_builder import LegalContextBuilder, internal_source_to_dict
from app.rag.ranking import rank_retrieval_results
from app.rag.retriever import LegalDocumentRetriever
from app.prompts.manager import PromptManager
from app.services.search_service import SearchService
from app.models.mode_responses import ModeResponses
from app.rag.synthesizer import LegalResponseSynthesizer
from app.services.context_compression_service import ContextCompressionService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.rag.retrieval_result import PipelineRetrievalResult


@dataclass
class RAGPipelineResult:
    """Structured output from a full retrieve → synthesize cycle."""

    answer: str
    responses: ModeResponses
    sources: list[dict]
    confidence_score: float
    provider: str
    retrieved_count: int = 0
    contexts: list[str] = field(default_factory=list)


@dataclass
class RAGPipeline:
    """
    Orchestrates retrieval, context building, and LLM synthesis.

    Components are constructor-injected for testability and FastAPI DI.
    """

    session: AsyncSession
    llm_service: LLMService
    embedding_service: EmbeddingService
    prompt_manager: PromptManager
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
    ) -> LegalResponseSynthesizer:
        return LegalResponseSynthesizer(
            self.llm_service,
            self.prompt_manager,
            provider=provider,
        )

    async def retrieve(
        self,
        question: str,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        provider: str | None = None,
    ) -> PipelineRetrievalResult:
        """Execute retrieval once: vector search → context → compression."""
        retriever = self._build_retriever(
            document_id=document_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        raw_nodes = await retriever.aretrieve(QueryBundle(query_str=question))
        nodes, _ranking_stats = rank_retrieval_results(
            raw_nodes,
            question,
            top_k=top_k,
        )
        active_provider = provider or settings.DEFAULT_LLM_PROVIDER

        if not nodes:
            return PipelineRetrievalResult(
                context_text="",
                sources=[],
                nodes=[],
                confidence_score=0.0,
                provider=active_provider,
                retrieved_count=0,
                retrieval_mode="rag",
                contexts=[],
            )

        built_context = self.context_builder.build(nodes)
        compressed = self.context_compression_service.compress(
            built_context,
            question,
        )
        confidence = compute_confidence_score(nodes)
        sources = [internal_source_to_dict(source) for source in built_context.sources]
        contexts = [
            (node_with_score.node.get_content() or "")
            for node_with_score in nodes
        ]

        return PipelineRetrievalResult(
            context_text=compressed.context_text,
            sources=sources,
            nodes=nodes,
            confidence_score=confidence,
            provider=active_provider,
            retrieved_count=len(nodes),
            retrieval_mode="rag",
            contexts=contexts,
        )

    async def synthesize_all_modes(
        self,
        question: str,
        retrieval: PipelineRetrievalResult,
        *,
        provider: str | None = None,
    ) -> ModeResponses:
        """Generate all response modes from a pre-built retrieval context."""
        synthesizer = self._build_synthesizer(provider or retrieval.provider)
        return await synthesizer.synthesize_all_modes_from_context(
            question,
            retrieval.context_text,
            mode=retrieval.retrieval_mode,
        )

    async def run(
        self,
        question: str,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        provider: str | None = None,
    ) -> RAGPipelineResult:
        """Execute retrieve once, then synthesize all response modes."""
        retrieval = await self.retrieve(
            question,
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

        return RAGPipelineResult(
            answer=responses.explain,
            responses=responses,
            sources=retrieval.sources,
            confidence_score=retrieval.confidence_score,
            provider=retrieval.provider,
            retrieved_count=retrieval.retrieved_count,
            contexts=retrieval.contexts,
        )
