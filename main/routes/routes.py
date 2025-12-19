"""
Routes Module
FastAPI route handlers for document upload and querying.
"""

import os
import re
import logging
import tempfile
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from llama_index.core import SimpleDirectoryReader
from main.service.rag_service import get_query_engine, add_documents_to_index
from main.evaluation.dataset import get_langfuse_client
from main.evaluation.dataset_evaluation import (
    evaluate_faithfulness_score,
    evaluate_answer_relevance,
)
from main.handoff.handoff_service import (
    evaluate_score,
    send_handoff_email,
    generate_handoff_reference_id,
    evaluate_explicit_user_request,
    evaluate_confidence_score,
)
import secrets
import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_QUERY_LENGTH = 2000
MIN_SIMILARITY_TOP_K = 1
MAX_SIMILARITY_TOP_K = 20
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.md'}


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    question: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    user_email: str = Field(..., min_length=3, max_length=320, description="User email for human handoff follow-up")
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        """Validate and sanitize question input."""
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()

    @field_validator("user_email")
    @classmethod
    def validate_user_email(cls, v: str):
        v = (v or "").strip()
        if "@" not in v or v.startswith("@") or v.endswith("@"):
            raise ValueError("Invalid user_email")
        return v


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str
    source_nodes: List[dict] = []


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    message: str
    documents_indexed: int


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Sprint 9 Practice RAG API"}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other security issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem operations
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    filename = os.path.basename(filename)
    filename = filename.replace('/', '_').replace('\\', '_')
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document file for indexing.
    
    Accepts: .txt, .pdf, .md files (max 10MB)
    
    Returns:
        UploadResponse with message and number of documents indexed
    """
    file_path = None
    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        
        safe_filename = sanitize_filename(file.filename)
        file_ext = os.path.splitext(safe_filename)[1].lower()
        
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        content = await file.read()
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix=file_ext,
            delete=False
        ) as tmp_file:
            tmp_file.write(content)
            file_path = tmp_file.name
        
        logger.info(f"File uploaded: {safe_filename} ({len(content)} bytes)")
        
        reader = SimpleDirectoryReader(input_files=[file_path])
        documents = reader.load_data()
        
        logger.info(f"Loaded {len(documents)} document(s) from {safe_filename}")
        
        result = add_documents_to_index(documents)
        
        return UploadResponse(
            message=result["message"],
            documents_indexed=len(documents)
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid file or request"
        )
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process document"
        )
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {file_path}: {e}")


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest, background_tasks: BackgroundTasks):
    """
    Query the RAG system with a question.
    
    Returns answer and source nodes used for the response.
    Also performs automatic evaluation (faithfulness + answer relevance) in Langfuse.
    Implements human handoff when quality thresholds are not met.
    
    Args:
        request: QueryRequest with question and user_email
        background_tasks: FastAPI background tasks for async email sending
        
    Returns:
        QueryResponse with answer and source nodes (or handoff message if triggered)
    """
    # TODO: Implement query endpoint with human handoff logic
    raise NotImplementedError("Query endpoint with handoff logic needs to be implemented")


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Sprint 9 Practice RAG API",
        "version": "1.0.0",
        "endpoints": {
            "POST /upload": "Upload documents for indexing",
            "POST /query": "Query the RAG system",
            "GET /health": "Health check"
        }
    }

