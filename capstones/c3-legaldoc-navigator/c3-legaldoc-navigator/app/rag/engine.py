"""RAG query engine orchestration."""

from dataclasses import dataclass
from uuid import UUID

from app.models.mode_responses import ModeResponses
from app.rag.pipeline import RAGPipeline, RAGPipelineResult


@dataclass
class RAGResponse:
    answer: str
    responses: ModeResponses
    sources: list[dict]
    confidence_score: float
    provider: str
    retrieved_count: int = 0


class RAGEngine:
    """Thin facade over the LlamaIndex RAG pipeline."""

    def __init__(self, pipeline: RAGPipeline) -> None:
        self._pipeline = pipeline

    async def query(
        self,
        question: str,
        *,
        document_id: UUID | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        provider: str | None = None,
    ) -> RAGResponse:
        result: RAGPipelineResult = await self._pipeline.run(
            question,
            document_id=document_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            provider=provider,
        )
        return RAGResponse(
            answer=result.answer,
            responses=result.responses,
            sources=result.sources,
            confidence_score=result.confidence_score,
            provider=result.provider,
            retrieved_count=result.retrieved_count,
        )

