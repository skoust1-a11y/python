"""Document upload endpoint."""

import logging

from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_document_service
from app.models.schemas import DocumentUploadResponse
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload a legal document",
    description=(
        "Accepts PDF, DOCX, or TXT files. The document is parsed, chunked, "
        "embedded, and indexed for retrieval."
    ),
    responses={
        400: {"description": "Invalid file type or missing filename"},
        413: {"description": "File exceeds maximum upload size"},
        422: {"description": "Ingestion or indexing failed"},
    },
)
async def upload_document(
    file: UploadFile = File(..., description="Legal document file (PDF, DOCX, or TXT)"),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    logger.info("Upload request received: filename=%s", file.filename)
    return await document_service.upload_document(file)
