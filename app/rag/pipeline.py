"""Production LlamaIndex RAG pipeline with injectable components."""

from dataclasses import dataclass, field
from uuid import UUID

from llama_index.core.schema import QueryBundle
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.confidence import compute_confidence_score
from app.rag.context_builder import LegalContextBuilder
from app.rag.retriever import LegalDocumentRetriever
from app.rag.synthesizer import LegalResponseSynthesizer
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.search_service import SearchService


@dataclass
class RAGPipelineResult:
    """Structured output from a full retrieve → synthesize cycle."""

    answer: str
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

    async def run(
        self,
        question: str,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        provider: str | None = None,
    ) -> RAGPipelineResult:
        """Execute the full RAG pipeline: retrieve → build context → synthesize."""
        retriever = self._build_retriever(
            document_id=document_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        nodes = await retriever.aretrieve(QueryBundle(query_str=question))

        built_context = self.context_builder.build(nodes)
        synthesizer = self._build_synthesizer(provider)
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
                "metadata": source.metadata,
            }
            for source in built_context.sources
        ]

        contexts = [
            (node_with_score.node.get_content() or "")
            for node_with_score in nodes
        ]

        return RAGPipelineResult(
            answer=answer,
            sources=sources,
            confidence_score=confidence,
            provider=active_provider,
            retrieved_count=len(nodes),
            contexts=contexts,
        )
