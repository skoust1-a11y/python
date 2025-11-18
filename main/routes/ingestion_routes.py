"""
FastAPI routes for document ingestion and query operations.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from main.config import logger
from main.services.injection_pipeline_service import InjectionPipelineService
from main.services.query_service import QueryService

ALLOWED_EXT = {".pdf", ".txt", ".html", ".htm", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

async def save_uploaded_file(
    file: UploadFile, 
    directory: str, 
    add_timestamp: bool = True
):
    os.makedirs(directory, exist_ok=True)
    if add_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
    else:
        filename = file.filename
    file_path = os.path.join(directory, filename)
    logger.info(f"Saving file to {file_path}")
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    logger.info(f"File saved successfully: {file_path}")
    return filename, file_path

def validate_and_prepare_upload(
    file: UploadFile,
    allowed_extensions: set = ALLOWED_EXT,
    max_size: int = MAX_FILE_SIZE
):
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        error_msg = f"Invalid file type: {file_extension}. Allowed types: {', '.join(allowed_extensions)}"
        logger.warning(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    is_valid_size = file_size <= max_size and file_size > 0
    if not is_valid_size:
        if file_size == 0:
            error_msg = f"Empty file: {file.filename}"
        else:
            error_msg = f"File too large: {file_size} bytes (max {max_size} bytes)"
        logger.warning(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    return file_extension, file_size

def count_documents_in_directory(directory: str, allowed_extensions: Optional[set] = None) -> int:
    if not os.path.exists(directory):
        return 0
    count = 0
    for file_path in Path(directory).glob("*"):
        if file_path.is_file():
            if allowed_extensions is None or file_path.suffix.lower() in allowed_extensions:
                count += 1
    return count

def list_documents_in_directory(directory: str, allowed_extensions: Optional[set] = None):
    documents = []
    if not os.path.exists(directory):
        return documents
    for file_path in Path(directory).glob("*"):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if allowed_extensions is not None and ext not in allowed_extensions:
                continue
            stat = file_path.stat()
            documents.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "extension": ext,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    return documents

def delete_file(directory: str, filename: str) -> bool:
    file_path = os.path.join(directory, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document not found: {filename}")
    try:
        os.remove(file_path)
        logger.info(f"Deleted file: {file_path}")
        return True
    except Exception as e:
        error_msg = f"Failed to delete {filename}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

def delete_all_files(directory: str) -> int:
    try:
        deleted_count = 0
        for file_path in Path(directory).glob("*"):
            if file_path.is_file():
                file_path.unlink()
                deleted_count += 1
                logger.debug(f"Deleted: {file_path}")
        logger.info(f"Deleted {deleted_count} file(s) from {directory}")
        return deleted_count
    except Exception as e:
        error_msg = f"Failed to delete documents: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

# Configuration
DOCUMENTS_DIR = "Documents"

# Ensure documents directory exists
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["ingestion"])

# Response models
class UploadResponse(BaseModel):
    filename: str
    size: int
    saved_path: str
    message: str
    chunks_created: int
    embeddings_stored: int

class DocumentInfo(BaseModel):
    filename: str
    size: int
    extension: str
    uploaded_at: str

class HealthResponse(BaseModel):
    status: str
    documents_dir: str
    total_documents: int

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class QueryResult(BaseModel):
    content: str
    metadata: dict
    score: Optional[float] = None

class QueryResponse(BaseModel):
    success: bool
    query: str
    results: List[QueryResult]
    count: int


@router.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    # TODO: Implement API info response.
    # Expected:
    # - Return a dict with name, version, description, and list of endpoints
    raise NotImplementedError("root() not implemented. Return API info dictionary.")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # TODO: Implement health check.
    # Expected:
    # - Compute total documents in DOCUMENTS_DIR
    # - Return HealthResponse(status, documents_dir, total_documents)
    # - Handle and raise HTTPException on failure
    raise NotImplementedError("health_check() not implemented. Build and return HealthResponse.")


@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all uploaded documents."""
    # TODO: Implement list documents.
    # Expected:
    # - Read files in DOCUMENTS_DIR filtered by ALLOWED_EXT
    # - Map to List[DocumentInfo]
    raise NotImplementedError("list_documents() not implemented. Return list of DocumentInfo.")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a single document (PDF, TXT, or HTML) and automatically generate embeddings.
    The document is processed immediately and stored in the vector database.
    
    - **file**: Document file to upload
    """
    # TODO: Implement single file upload and processing.
    # Expected:
    # - Validate file (extension and size)
    # - Save uploaded file to DOCUMENTS_DIR (timestamped)
    # - Run InjectionPipelineService().process_file(file_path)
    # - Build and return UploadResponse; handle HTTPException and general errors
    raise NotImplementedError("upload_document() not implemented. Validate, save, process, and return UploadResponse.")


@router.post("/upload-multiple", response_model=List[UploadResponse])
async def upload_multiple_documents(files: List[UploadFile] = File(...)):
    """
    Upload multiple documents at once and automatically generate embeddings.
    Each document is processed immediately and stored in the vector database.
    
    - **files**: List of document files to upload (use same field name 'files' for all files)
    """
    # TODO: Implement multi-file upload and processing.
    # Expected:
    # - Validate inputs
    # - Loop files: validate, save, process with InjectionPipelineService
    # - Aggregate UploadResponse items; collect errors
    # - Return 207 with partial results if needed, or list of responses
    raise NotImplementedError("upload_multiple_documents() not implemented. Validate, save, process, aggregate responses.")


@router.post("/query", response_model=QueryResponse)
async def query_vectorstore(request: QueryRequest):
    """
    Query the vector database for similar documents.
    
    - **query**: The search query text
    - **top_k**: Number of results to return (default: 5)
    """
    # TODO: Implement query endpoint.
    # Expected:
    # - Use QueryService().similarity_search(request.query, top_k=request.top_k)
    # - Map results to List[QueryResult]
    # - Return QueryResponse; handle HTTPException on failure
    raise NotImplementedError("query_vectorstore() not implemented. Execute search and return QueryResponse.")




@router.delete("/documents")
async def delete_all_documents():
    """Delete all documents from the Documents directory."""
    # TODO: Implement delete all endpoint.
    # Expected:
    # - Call delete_all_files(DOCUMENTS_DIR)
    # - Return dict with status, message, and deleted_count
    raise NotImplementedError("delete_all_documents() not implemented. Delete files and return summary.")

