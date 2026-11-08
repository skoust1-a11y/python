"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.models.schemas import ErrorResponse
from app.router.api_router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    from app.services.llm_service import log_llm_configuration

    log_llm_configuration()
    from app.observability.tracing import init_langfuse_client

    init_langfuse_client()
    from app.database.session import verify_database_connection

    await verify_database_connection()
    if settings.VECTOR_BACKEND == "qdrant":
        from app.services.qdrant_service import QdrantVectorService

        await QdrantVectorService().ensure_collection()
    logger.info("Starting %s", settings.APP_NAME)
    yield
    if settings.MCP_ENABLED:
        from app.dependencies import get_external_legal_search_service

        await get_external_legal_search_service().shutdown()
    from app.observability.tracing import shutdown_tracing

    shutdown_tracing()
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description=(
            "AI-powered legal document analysis API. Upload contracts and case files, "
            "query them with natural language, and receive grounded answers with citations."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        logger.warning("AppException: %s (status=%d)", exc.message, exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(detail=exc.message).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(detail=detail).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        message = "; ".join(
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in errors
        )
        logger.warning("Validation error: %s", message)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(detail=message).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(detail="An unexpected internal error occurred.").model_dump(),
        )

    return app


app = create_app()
