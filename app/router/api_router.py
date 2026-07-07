"""Central API router — mounts all endpoint modules."""

from fastapi import APIRouter

from app.api import documents, feedback, handoff, health, keyword_search, query, upload

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(upload.router)
api_router.include_router(query.router)
api_router.include_router(keyword_search.router)
api_router.include_router(documents.router)
api_router.include_router(feedback.router)
api_router.include_router(handoff.router)
