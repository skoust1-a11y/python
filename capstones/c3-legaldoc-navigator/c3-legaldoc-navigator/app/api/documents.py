"""Document listing and retrieval endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_document_service
from app.models.schemas import DocumentDetailResponse, DocumentListResponse
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List uploaded documents",
    description="Returns a paginated list of all documents ordered by upload date.",
)
async def list_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    return await document_service.list_documents(skip=skip, limit=limit)


@router.get(
    "/document/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document by ID",
    description="Returns full metadata for a single uploaded document.",
    responses={404: {"description": "Document not found"}},
)
async def get_document(
    document_id: UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDetailResponse:
    logger.debug("Fetching document: id=%s", document_id)
    return await document_service.get_document(document_id)
