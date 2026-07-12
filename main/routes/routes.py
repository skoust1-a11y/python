"""API routes for diet counselling assistant with metadata filtering."""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, field_validator
import os,re
from ..service.rag_service import RAGService
import tempfile

logger = logging.getLogger(__name__)

router = APIRouter()
rag_service = RAGService()


ALLOWED_EXTENSIONS = {'.pdf','.txt','.md'}
MAX_FILE_SIZE = 10 * 1024 * 1024 

class QueryRequest(BaseModel):
    """Request model for query endpoint with metadata filtering."""
    question: str = Field(
        ...,
        max_length=2000,
        description="Query question (max 2000 characters)",
        examples=["What are some healthy breakfast options for a vegetarian diet?"],
    )
    similarity_top_k: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Number of top similar results to retrieve (1-20)",
        examples=[3],
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters (e.g., {'meal_type': 'breakfast', 'dietary_restriction': 'vegetarian'})",
        examples=[
            {"meal_type": "breakfast"},
            {"meal_type": "breakfast", "dietary_restriction": "vegetarian"},
        ],
    )
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class NodeInfo(BaseModel):
    """Model for node information in query responses."""
    text: str
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str
    source_nodes: List[NodeInfo]


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    message: str
    documents_indexed: int


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
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove any remaining path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove dangerous characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename

@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "Personal Diet Counselling Assistant API",
        "initialized": rag_service.is_initialized()
    }


@router.get("/")
async def root():
    """
    Root endpoint with API information and available metadata filters.
    
    Returns:
        API information and metadata filter options
    """
    return {
        "service": "Personal Diet Counselling Assistant API",
        "version": "1.0.0",
        "description": "RAG-based diet counselling system with multi-modal content processing",
        "docs": "/docs",
        "metadata_filters": {
            "meal_types": ["breakfast", "lunch", "dinner", "snack"],
            "dietary_restrictions": ["vegetarian", "vegan", "gluten-free", "keto", "diabetic", "low-sodium"],
            "nutrition_categories": ["protein", "carbohydrates", "vitamins", "minerals", "healthy-fats"],
            "topics": ["recipes", "meal-planning", "nutrition-facts", "dietary-guidelines"]
        },
        "example_queries": {
            "without_filter": {
                "question": "What are some healthy breakfast options?",
                "similarity_top_k": 3
            },
            "with_meal_type": {
                "question": "What are some healthy breakfast options?",
                "similarity_top_k": 3,
                "filters": {"meal_type": "breakfast"}
            },
            "with_multiple_filters": {
                "question": "What are some healthy breakfast options?",
                "similarity_top_k": 3,
                "filters": {
                    "meal_type": "breakfast",
                    "dietary_restriction": "vegetarian"
                }
            }
        }
    }


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a PDF document.
    
    Metadata is automatically assigned based on filename patterns:
    - Meal types: breakfast, lunch, dinner, snack
    - Dietary restrictions: vegetarian, vegan, gluten-free, keto, diabetic, low-sodium
    - Nutrition categories: protein, carbohydrates, vitamins, minerals, healthy-fats
    - Topics: recipes, meal-planning, nutrition-facts, dietary-guidelines
    
    Example filenames:
    - breakfast_vegetarian_recipes.pdf → meal_type: breakfast, dietary_restriction: vegetarian, topic: recipes
    - diabetic_meal_planning.pdf → dietary_restriction: diabetic, topic: meal-planning
    
    Args:
        file: PDF file to upload and process (max 10MB)
        
    Returns:
        Processing result with document count
    """
    logger.info("Upload document (boilerplate)")

    # TODO: Validate the uploaded file and process it for indexing.
    # HINT: Validate filename and file extension (e.g., allow .pdf/.txt/.md).
    filename = sanitize_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
                status_code=400,
                detail=f"File type not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

    # HINT: Enforce a max upload size (e.g., 10MB) and return HTTP 400 when exceeded.
    content = await file.read()
    file_size = len(content)

    if file_size >= MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size not supported. Allowed size :{MAX_FILE_SIZE}"
            )
    try:
        with tempfile.NamedTemporaryFile(
            suffix=ext,
            delete=False,
            mode='wb'
        ) as tmpFile:
            tmpFile.write(content)
            filepath = tmpFile.name
        logger.info(f"File uploaded: {filename} ({len(content)} bytes)")

    # HINT: Persist the uploaded bytes somewhere accessible to your processing logic
    #       (temporary file, object storage, etc.).
    # HINT: Call your document processing/indexing service and return:
    #   - message: str
    #   - documents_indexed: int
    # HINT: Ensure cleanup of any temporary artifacts you create.
    # Your code here:
        try:
            # Process document (pass original filename for metadata)
            logger.info(f"Processing document: {file.filename}")
            result = rag_service.process_document(pdf_path=filepath, original_filename=file.filename)
            
            logger.info(f"Document processed successfully: {result}")
            
            return UploadResponse(
                documents_indexed=result['documents_indexed'],
                message=result['message'],
            )
        finally:
            # Clean up temporary file
            if os.path.exists(filepath):
                os.unlink(filepath)
                logger.debug(f"Cleaned up temporary file: {filepath}")
        
    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )


@router.post(
    "/query",
    response_model=QueryResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "no_filters": {
                            "summary": "No filters",
                            "value": {
                                "question": "What are some healthy breakfast options?",
                                "similarity_top_k": 3,
                            },
                        },
                        "meal_type_filter": {
                            "summary": "Filter by meal type",
                            "value": {
                                "question": "Give me healthy breakfast options.",
                                "similarity_top_k": 3,
                                "filters": {"meal_type": "breakfast"},
                            },
                        },
                        "multiple_filters": {
                            "summary": "Filter by meal type + dietary restriction",
                            "value": {
                                "question": "Give me healthy breakfast options.",
                                "similarity_top_k": 3,
                                "filters": {
                                    "meal_type": "breakfast",
                                    "dietary_restriction": "vegetarian",
                                },
                            },
                        },
                        "diabetic_meal_planning": {
                            "summary": "Filter by dietary restriction + topic",
                            "value": {
                                "question": "Suggest a 1-day meal plan.",
                                "similarity_top_k": 3,
                                "filters": {
                                    "dietary_restriction": "diabetic",
                                    "topic": "meal-planning",
                                },
                            },
                        },
                    }
                }
            }
        }
    },
)
async def query_documents(request: QueryRequest):
    """
    Query the diet counselling system with optional metadata filtering.
    
    Supports filtering by:
    - meal_type: breakfast, lunch, dinner, snack
    - dietary_restriction: vegetarian, vegan, gluten-free, keto, diabetic, low-sodium
    - nutrition_category: protein, carbohydrates, vitamins, minerals, healthy-fats
    - topic: recipes, meal-planning, nutrition-facts, dietary-guidelines
    
    Args:
        request: Query request with question, similarity_top_k, and optional filters
        
    Returns:
        Answer to the query along with retrieved source nodes
    """
    logger.info(
        f"Received query request: question='{request.question[:50]}...', "
        f"similarity_top_k={request.similarity_top_k}, filters={request.filters}"
    )
    
    try:
        answer, nodes = rag_service.query(
            question=request.question,
            similarity_top_k=request.similarity_top_k,
            filters=request.filters
        )
        
        # Convert nodes to NodeInfo format
        node_infos = []
        for node in nodes:
            # Handle both NodeWithScore and direct Node objects
            if hasattr(node, 'node'):
                node_obj = node.node
                score = getattr(node, 'score', None)
            else:
                node_obj = node
                score = None
            
            # Extract text and metadata
            text = getattr(node_obj, 'text', str(node_obj))
            metadata = getattr(node_obj, 'metadata', None)
            
            node_infos.append(NodeInfo(
                text=text,
                score=score,
                metadata=metadata
            ))
        
        logger.info(
            f"Query completed successfully, answer length: {len(answer)} characters, "
            f"{len(node_infos)} nodes returned"
        )
        
        return QueryResponse(answer=answer, source_nodes=node_infos)
        
    except ValueError as e:
        # ValueError is raised when index is not initialized
        if "Index not initialized" in str(e) or "not initialized" in str(e).lower():
            logger.warning("Query attempted but no document has been processed yet")
            raise HTTPException(
                status_code=400,
                detail="No document has been processed yet. Please upload a document first."
            )
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
