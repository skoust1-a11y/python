"""
API routes and models for vectorstore operations.
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field,ValidationError
from main.services.vectorstore_service import get_vectorstore_service
from uuid import uuid4

# TODO: Import your service here

logger = logging.getLogger(__name__)

# --------------------------
# Pydantic Models
# --------------------------

class UploadDataRequest(BaseModel):
    """Request model for uploading string data."""
    doc_id: str = Field(..., description="Unique identifier for the document")
    content: str = Field(..., description="The text content to add to the vectorstore")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata to attach to the document (e.g., document name, category, etc.)"
    )


class UploadDataResponse(BaseModel):
    """Response model for upload operation."""
    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Status message")
    document_id: Optional[str] = Field(default=None, description="ID of the inserted document")


class QueryRequest(BaseModel):
    """Request model for querying the vectorstore."""
    query: str = Field(..., description="The search query text")
    top_k: Optional[int] = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of results to return (1-10, default: 1)"
    )


class QueryResult(BaseModel):
    """Model for a single query result."""
    content: str = Field(..., description="The document content")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")


class QueryResponse(BaseModel):
    """Response model for query operation."""
    success: bool = Field(..., description="Whether the query was successful")
    query: str = Field(..., description="The original query")
    results: List[QueryResult] = Field(..., description="List of query results")
    count: int = Field(..., description="Number of results returned")

class QueryHit(BaseModel):
    """Model representing a single query result."""
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Document metadata",
        example={"document": "vehicle_policy", "id": "hr_manual_002"}
    )
    page_content: str = Field(
        ...,
        description="The document content",
        example="Our company's vacation policy allows for 20 paid days off per year."
    )



# --------------------------
# API Routes
# --------------------------

router = APIRouter(prefix="/api/v1", tags=["vectorstore"])


@router.post("/upload", response_model=UploadDataResponse, status_code=status.HTTP_201_CREATED)
async def upload_data(request: UploadDataRequest):
    """
    Upload/add string data to the vectorstore.
    
    - **doc_id**: Unique identifier for the document (required)
    - **content**: The text content to add
    - **metadata**: Optional metadata (e.g., document name, category, etc.)
    """
    try:
        # TODO: Get your service instance here
        service = get_vectorstore_service()
   
        # TODO: Prepare metadata (merge doc_id into metadata if needed)
        final_doc_id = request.doc_id or str(uuid4())
        md = dict(request.metadata or {})
        md["id"] = final_doc_id

        # TODO: Call your service method to add the document
        doc_id = service.add_document(request.content,md)
        
        # TODO: Replace the placeholder below with actual document_id from service call
        document_id = doc_id
        
        # Return success response
        return UploadDataResponse(
            success=True,
            message="Document added successfully",
            document_id=document_id
        )
    except ValidationError as e:
        logger.error(f"Validation Error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Validation Error: {str(e)}"
        )

    except ValueError as e:
        logger.error(f"Value Error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Input: {str(e)}"
        )

    except ConnectionError as e:
        logger.error(f"Connection Error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to the service."
        )

    except FileNotFoundError as e:
        logger.error(f"File Not Found: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception as e:
        logger.exception("Unexpected Error")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )


@router.post("/query", response_model=QueryResponse)
async def query_vectorstore(request: QueryRequest):
    """
    Query the vectorstore for similar documents.
    
    - **query**: The search query text
    - **top_k**: Number of results to return (1-10, default: 1)
    """
    try:
        # TODO: Get your service instance here
        service = get_vectorstore_service()
        
        # TODO: Call your service method to query the vectorstore    
        # TODO: Replace the placeholder below with actual results from service call
        
        # TODO: Transform service results into QueryResult objects
        
        query_result_ans = service.query(request.query,request.top_k)

        query_results = []

        for item in query_result_ans:
            query_results.append(
                QueryResult(
                content=item.get('content'),
                metadata=item.get('metadata')
            )
            )     
        # Return success response
        return QueryResponse(
            success=True,
            query=request.query,
            results=query_results,
            count=len(query_results)
        )
    except ValidationError as e:
        logger.error(f"Validation Error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Validation Error: {str(e)}"
        )

    except ValueError as e:
        logger.error(f"Value Error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Input: {str(e)}"
        )

    except ConnectionError as e:
        logger.error(f"Connection Error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to the service."
        )

    except FileNotFoundError as e:
        logger.error(f"File Not Found: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception as e:
        logger.exception("Unexpected Error")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )
