"""FastAPI dependency injection providers for the RAG stack."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.guardrails.validator import GuardrailValidator
from app.mcp.retry import MCPRetryPolicy
from app.mcp.search import ExternalLegalSearchService
from app.prompts.manager import PromptManager
from app.rag.hybrid_pipeline import HybridPipeline
from app.rag.pipeline import RAGPipeline
from app.routing.router import Router
from app.services.context_compression_service import ContextCompressionService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.feedback_service import FeedbackService
from app.services.handoff_service import HandoffService
from app.services.llm_service import LLMService
from app.services.query_dispatcher import QueryDispatcher
from app.services.query_service import QueryService
from app.services.sql_query_planner import SqlQueryPlanner
from app.services.sql_retrieval_service import SqlRetrievalService


@lru_cache
def get_prompt_manager() -> PromptManager:
    return PromptManager()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()


@lru_cache
def get_context_compression_service() -> ContextCompressionService:
    return ContextCompressionService()


@lru_cache
def get_guardrail_validator() -> GuardrailValidator:
    return GuardrailValidator()


@lru_cache
def get_query_router() -> Router:
    return Router(llm_service=get_llm_service())


@lru_cache
def get_sql_query_planner() -> SqlQueryPlanner:
    return SqlQueryPlanner(llm_service=get_llm_service())


@lru_cache
def get_external_legal_search_service() -> ExternalLegalSearchService:
    return ExternalLegalSearchService(
        servers=settings.MCP_SERVERS,
        enabled=settings.MCP_ENABLED,
        retry_policy=MCPRetryPolicy(
            max_attempts=settings.MCP_RETRY_MAX_ATTEMPTS,
            min_wait_seconds=settings.MCP_RETRY_MIN_WAIT_SECONDS,
            max_wait_seconds=settings.MCP_RETRY_MAX_WAIT_SECONDS,
        ),
    )


def get_rag_pipeline(
    session: AsyncSession = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
    context_compression_service: ContextCompressionService = Depends(
        get_context_compression_service
    ),
) -> RAGPipeline:
    return RAGPipeline(
        session=session,
        embedding_service=embedding_service,
        llm_service=llm_service,
        prompt_manager=prompt_manager,
        context_compression_service=context_compression_service,
    )


def get_hybrid_pipeline(
    session: AsyncSession = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
    sql_planner: SqlQueryPlanner = Depends(get_sql_query_planner),
    external_search_service: ExternalLegalSearchService = Depends(
        get_external_legal_search_service
    ),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
    context_compression_service: ContextCompressionService = Depends(
        get_context_compression_service
    ),
) -> HybridPipeline:
    return HybridPipeline(
        session=session,
        llm_service=llm_service,
        embedding_service=embedding_service,
        sql_planner=sql_planner,
        external_search_service=external_search_service,
        prompt_manager=prompt_manager,
        context_compression_service=context_compression_service,
    )


def get_query_dispatcher(
    session: AsyncSession = Depends(get_db),
    router: Router = Depends(get_query_router),
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
    hybrid_pipeline: HybridPipeline = Depends(get_hybrid_pipeline),
    sql_planner: SqlQueryPlanner = Depends(get_sql_query_planner),
    llm_service: LLMService = Depends(get_llm_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
) -> QueryDispatcher:
    return QueryDispatcher(
        session=session,
        router=router,
        rag_pipeline=rag_pipeline,
        hybrid_pipeline=hybrid_pipeline,
        sql_planner=sql_planner,
        llm_service=llm_service,
        embedding_service=embedding_service,
        prompt_manager=prompt_manager,
    )


def get_query_service(
    session: AsyncSession = Depends(get_db),
    dispatcher: QueryDispatcher = Depends(get_query_dispatcher),
    guardrails: GuardrailValidator = Depends(get_guardrail_validator),
) -> QueryService:
    return QueryService(session=session, dispatcher=dispatcher, guardrails=guardrails)


def get_sql_retrieval_service(
    session: AsyncSession = Depends(get_db),
) -> SqlRetrievalService:
    return SqlRetrievalService(session=session)


def get_document_service(
    session: AsyncSession = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> DocumentService:
    return DocumentService(session=session, embedding_service=embedding_service)


def get_feedback_service(
    session: AsyncSession = Depends(get_db),
) -> FeedbackService:
    return FeedbackService(session=session)


def get_handoff_service(
    session: AsyncSession = Depends(get_db),
) -> HandoffService:
    return HandoffService(session=session)
