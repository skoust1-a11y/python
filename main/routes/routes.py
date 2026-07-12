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
    """Query RAG system with evaluation and human handoff logic."""
    import asyncio
    span = None
    try:
        # 1. Setup: Generate session_id, initialize conversation_flow
        session_id = secrets.token_hex(8)
        conversation_flow = f"Session {session_id} started."

        # 2. RAG Query: Get query engine, execute query, build full_chunks list
        query_engine = get_query_engine()
        response = query_engine.query(request.question)
        answer = str(response)

        full_chunks = []
        if hasattr(response, "source_nodes") and response.source_nodes:
            for node in response.source_nodes:
                try:
                    full_chunks.append(node.text)
                except Exception:
                    continue
        no_chunks = len(full_chunks) == 0

        # 3. Langfuse: Start span, get trace_id
        langfuse = None
        try:
            langfuse = get_langfuse_client()
            span = langfuse.start_span(
                name="rag_query_handoff",
                input={"question": request.question},
            )
            trace_id = span.trace_id
        except Exception as e:
            logger.warning(f"Could not initialize Langfuse or start span: {e}")
            trace_id = f"TR-{secrets.token_hex(8).upper()}"

        # 4. Evaluations: Run faithfulness, relevance, confidence, explicit request checks (all async)
        if langfuse is None:
            class DummyLangfuse:
                def create_score(self, *args, **kwargs):
                    pass
                def score(self, *args, **kwargs):
                    pass
            langfuse_to_pass = DummyLangfuse()
        else:
            langfuse_to_pass = langfuse

        context_str = "\n\n".join(full_chunks)

        faithfulness_task = evaluate_faithfulness_score(
            langfuse_to_pass, trace_id, request.question, context_str, answer
        )
        relevance_task = evaluate_answer_relevance(
            langfuse_to_pass, trace_id, request.question, answer
        )
        confidence_task = evaluate_confidence_score(answer)
        explicit_task = evaluate_explicit_user_request(request.question)

        faithfulness_val, relevance_val, confidence_res, explicit_res = await asyncio.gather(
            faithfulness_task,
            relevance_task,
            confidence_task,
            explicit_task
        )

        # 5. Handoff Decision (priority order):
        #    - Explicit request → high priority
        #    - Confidence + risk → high priority
        #    - Score-based → normal priority
        trigger_handoff = False
        priority = "normal"
        trigger_reason = ""

        if explicit_res.get("trigger"):
            trigger_handoff = True
            priority = "high"
            trigger_reason = explicit_res.get("reason", "explicit user request")
        elif confidence_res.get("trigger"):
            trigger_handoff = True
            priority = "high"
            trigger_reason = confidence_res.get("reason", "confidence below threshold")
        else:
            score_res = evaluate_score(faithfulness_val, relevance_val, request.question, no_chunks)
            if score_res.get("trigger"):
                trigger_handoff = True
                priority = "normal"
                trigger_reason = score_res.get("reason", "evaluation score below threshold")

        # 6. If handoff triggered:
        #    - Generate reference_id, build handoff_context with all fields
        #    - Send email via background_tasks
        #    - Return fallback message with reference_id
        if trigger_handoff:
            reference_id = generate_handoff_reference_id()
            
            user_metadata = {"email": request.user_email}
            query_history = f"User: {request.question}"
            evaluation_scores = {
                "faithfulness": faithfulness_val,
                "relevance": relevance_val,
                "confidence": confidence_res.get("confidence")
            }
            flow_summary = (
                f"1. Session started: {session_id}\n"
                f"2. User question: '{request.question}'\n"
                f"3. RAG Generated response (low quality or requested human)\n"
                f"4. Automated evaluation triggered handoff: {trigger_reason}"
            )

            handoff_context = {
                "reference_id": reference_id,
                "trace_id": trace_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "priority": priority,
                "trigger_reason": trigger_reason,
                "user_metadata": user_metadata,
                "query_history": query_history,
                "generated_answer": answer,
                "evaluation_scores": evaluation_scores,
                "retrieved_chunks": full_chunks,
                "conversation_flow": flow_summary
            }

            background_tasks.add_task(send_handoff_email, handoff_context)

            fallback_msg = (
                "I apologize, but I am unable to provide a reliable answer to your question. "
                f"I have escalated this issue to a human support agent. Reference ID: {reference_id}."
            )
            
            if span:
                span.update(output={"answer": fallback_msg})
                span.end()

            return QueryResponse(answer=fallback_msg, source_nodes=[])

        # 7. Normal response: Format source_nodes (truncate to 200 chars), return answer
        formatted_nodes = []
        if hasattr(response, "source_nodes") and response.source_nodes:
            for node in response.source_nodes:
                text = getattr(node, "text", "")
                truncated_text = text[:200] + "..." if len(text) > 200 else text
                formatted_nodes.append({
                    "node_id": getattr(node.node, "node_id", None),
                    "text": truncated_text,
                    "score": getattr(node, "score", None)
                })

        if span:
            span.update(output={"answer": answer})
            span.end()

        return QueryResponse(answer=answer, source_nodes=formatted_nodes)

    # 8. Error handling: Wrap in try/except, log errors, raise HTTPException
    except Exception as e:
        logger.error(f"Error in query_rag endpoint: {e}", exc_info=True)
        if span:
            try:
                span.end()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="Internal server error")



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

