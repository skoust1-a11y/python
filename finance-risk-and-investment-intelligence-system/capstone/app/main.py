from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.responses import Response

from app import __version__
from app.api.routers import router
from app.core.config import get_settings
from app.core.db import CAPSTONE_ROOT
from app.core.ids import new_trace_id
from app.core.logging import bind_log, clear_log, configure_logging, get_logger
from app.rag import embed_missing_chunks
from app.sqlq.seed import bootstrap

STARTED = time.time()
REQUESTS = Counter("frii_requests_total", "API requests", ["path", "method"])

OPENAPI_TAGS = [
    {"name": "Health", "description": "Liveness, readiness, and Prometheus metrics."},
    {"name": "Auth", "description": "Signup, login, and the current principal."},
    {"name": "Profiles", "description": "Per-user analysis profiles and guidelines."},
    {"name": "Query", "description": "Grounded financial Q&A as JSON or SSE."},
    {"name": "Sessions", "description": "Chat session history."},
    {"name": "Screens", "description": "Equity screening, saved screens, and CSV export."},
    {"name": "Portfolios", "description": "In-scope books and CSV upload."},
    {"name": "Documents", "description": "Policy corpus and user-uploaded PDFs."},
    {"name": "Escalations", "description": "Human-review handoff records."},
    {"name": "Admin", "description": "Users, traces, reindex, SQL templates, and eval."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bootstrap(reset=False)
    threading.Thread(target=embed_missing_chunks, daemon=True).start()
    yield


def error_body(code: str, message: str, trace_id: str, status: int, extra: Dict[str, Any] = None) -> JSONResponse:
    payload = {"error": {"code": code, "message": message}, "trace_id": trace_id}
    if extra:
        payload["error"].update(extra)
    return JSONResponse(status_code=status, content=payload)


def create_app() -> FastAPI:
    configure_logging()
    log = get_logger("api")
    settings = get_settings()
    app = FastAPI(
        title="Finance Risk & Investment Intelligence API",
        description=(
            "Grounded Q&A over synthetic portfolio, risk, and policy data. "
            "Not investment advice — every answer includes citations and a disclaimer."
        ),
        version=__version__,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def extras(request: Request, call_next):
        trace_id = request.headers.get("X-Request-Id") or new_trace_id()
        request.state.trace_id = trace_id
        REQUESTS.labels(path=request.url.path, method=request.method).inc()
        started = time.perf_counter()
        bind_log(trace_id=trace_id)
        try:
            response = await call_next(request)
            status = response.status_code
            payload = dict(
                method=request.method,
                path=request.url.path,
                status=status,
                trace_id=trace_id,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            if status >= 500:
                log.error("http_request", **payload)
            elif status >= 400:
                log.warning("http_request", **payload)
            else:
                log.info("http_request", **payload)
            response.headers["X-Request-Id"] = trace_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            return response
        finally:
            clear_log()

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        field, message = None, "validation failed"
        if exc.errors():
            first = exc.errors()[0]
            loc = first.get("loc") or []
            field = str(loc[-1]) if loc else None
            if first.get("type") == "json_invalid":
                field, message = "body", f"malformed JSON at character {loc[-1]}: {first.get('ctx', {}).get('error', '')}"
        log.warning("invalid_request", field=field, path=str(request.url.path))
        return error_body(
            "invalid_request",
            message,
            getattr(request.state, "trace_id", new_trace_id()),
            400,
            {"field": field},
        )

    @app.get("/health", tags=["Health"])
    def health():
        """Liveness probe. Returns status, version, and uptime."""
        return {"status": "ok", "version": settings.version, "uptime_s": int(time.time() - STARTED)}

    @app.get("/metrics", tags=["Health"])
    def metrics():
        """Prometheus metrics scrape endpoint."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(router)
    dist = CAPSTONE_ROOT / "frontend" / "dist"
    if settings.app_env != "local" and (dist / "index.html").is_file():
        assets = dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="ui-assets")

        @app.get("/")
        def ui_root():
            return FileResponse(dist / "index.html")

        @app.get("/{full_path:path}")
        def ui_spa(full_path: str):
            candidate = dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
