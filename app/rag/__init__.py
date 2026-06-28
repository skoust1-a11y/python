"""Retrieval-Augmented Generation pipeline."""

from app.rag.confidence import compute_confidence_score
from app.rag.context_builder import BuiltContext, LegalContextBuilder, SourceReference
from app.rag.embeddings import EmbeddingService
from app.rag.engine import RAGEngine, RAGResponse
from app.rag.pipeline import RAGPipeline, RAGPipelineResult
from app.rag.retriever import LegalDocumentRetriever
from app.rag.search import SearchResult, SearchService
from app.rag.synthesizer import LegalResponseSynthesizer
from app.rag.vector_store import ChunkToStore, VectorStoreService

__all__ = [
    "BuiltContext",
    "ChunkToStore",
    "EmbeddingService",
    "LegalContextBuilder",
    "LegalDocumentRetriever",
    "LegalResponseSynthesizer",
    "RAGEngine",
    "RAGPipeline",
    "RAGPipelineResult",
    "RAGResponse",
    "SearchResult",
    "SearchService",
    "SourceReference",
    "VectorStoreService",
    "compute_confidence_score",
]
