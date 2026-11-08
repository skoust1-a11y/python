"""JSON exception handlers for expected and unexpected errors."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import AppError

logger = logging.getLogger("app")


def _error_body(
    code: str,
    message: str,
    *,
    detail: str | None = None,
    issues: list[dict] | None = None,
) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if detail:
        body["error"]["detail"] = detail
    if issues:
        body["error"]["issues"] = issues
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("%s: %s", exc.error_code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                exc.error_code,
                exc.message,
                issues=exc.issues or None,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("validation_error path=%s errors=%s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Request validation failed."),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.warning("http_exception path=%s status=%d detail=%s", request.url.path, exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("http_error", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        settings = getattr(request.app.state, "settings", None)
        detail = str(exc) if settings is not None and settings.is_development else None
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "internal_error",
                "An unexpected error occurred.",
                detail=detail,
            ),
        )
