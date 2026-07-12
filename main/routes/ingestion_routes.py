"""
FastAPI routes for document ingestion and query operations.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional,Dict,Any
from fastapi import APIRouter, File, UploadFile, HTTPException
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

    content = file.file.read()
    file_size = len(content)
    file.file.seek(0)

    # ✅ Guard moved BEFORE the comparison
    if file_size is None:
        raise HTTPException(status_code=400, detail="Could not determine file size.")

    if file_size == 0:
        error_msg = f"Empty file: {file.filename}"
        logger.warning(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    if file_size > max_size:
        error_msg = f"File too large: {file_size} bytes (max {max_size} bytes)"
        logger.warning(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    return file_extension, file_size

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

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class QueryResult(BaseModel):
    content: str
    metadata: dict
    distance: Optional[float] = None

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
    return {
       "name": "Smart Auto Advisor - RAG Ingestion API",
        "description": "AI-powered conversational assistant for car manufacturers",
        "version": "1.0.0",
        'endpoints':[
            "/documents",
            "/upload",
            "/query"
        ]
    }
    raise NotImplementedError("root() not implemented. Return API info dictionary.")


@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all uploaded documents."""
    # TODO: Implement list documents.
    # Expected:
    # - Read files in DOCUMENTS_DIR filtered by ALLOWED_EXT
    docs = list_documents_in_directory(DOCUMENTS_DIR,allowed_extensions=ALLOWED_EXT)
    # - Map to List[DocumentInfo]
    doc_info = [DocumentInfo(filename=doc["filename"], size=doc["size"], extension=doc["extension"], uploaded_at=doc["uploaded_at"]) for doc in docs]
    return doc_info
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
    try:
        file_extension,file_size = validate_and_prepare_upload(file=file,allowed_extensions=ALLOWED_EXT,max_size=MAX_FILE_SIZE)
        # - Save uploaded file to DOCUMENTS_DIR (timestamped)
        await file.seek(0)
        filename, file_path = await save_uploaded_file(file=file,directory=DOCUMENTS_DIR)
        # - Run InjectionPipelineService().process_file(file_path)
        file_process : dict = InjectionPipelineService().process_file(file_path=file_path)
        if file_process.get('status') == 'warning':
            raise HTTPException(
                status_code=404,
                detail=f"No documents loaded from {file_path}"
            )
        return UploadResponse(
            filename=file_process.get('filename'),
            chunks_created=file_process.get('chunks_created'),
            embeddings_stored=file_process.get('embeddings_stored'),
            message=file_process.get('message'),
            saved_path=file_path,
            size=file_size
        )
    except HTTPException as e:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f'File Not Found'
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unkonwn Error : {e}"
        )
    # - Build and return UploadResponse; handle HTTPException and general errors
    raise NotImplementedError("upload_document() not implemented. Validate, save, process, and return UploadResponse.")


@router.post("/query", response_model=QueryResponse)
async def query_vectorstore(request: QueryRequest):
    """
    Query the vector database for similar documents.
    
    - **query**: The search query text
    - **top_k**: Number of results to return (default: 5)
    """
    # TODO: Implement vector database query.
    # Expected:
    # - Initialize QueryService()
    try:
        queryService = QueryService()
        
        docs :  List[Dict[str, Any]] = queryService.similarity_search(query=request.query,top_k=request.top_k)

        query_results : List[QueryResult]= []

        for doc in docs:
            query_results.append(
                QueryResult(content=doc.get('content'),metadata=doc.get('metadata'),distance=doc.get('score')))
        
        return QueryResponse(success=True,count=request.top_k,query=request.query,results=query_results)
    except Exception as e:
        logger.error(f'Unknown Error : {e}')
        raise HTTPException(
            status_code=500,
            detail=f'Unknown Error : {e}'
        )

    # - Call similarity_search(request.query, top_k=request.top_k)
    # - Results are tuples: (Document, distance_score)
    # - Map results to List[QueryResult] with content, metadata, and distance
    # - Build and return QueryResponse(success, query, results, count)

    # - Handle exceptions: log errors and raise HTTPException(status_code=500)
    raise NotImplementedError("query_vectorstore() not implemented. Query vector database and return QueryResponse.")

