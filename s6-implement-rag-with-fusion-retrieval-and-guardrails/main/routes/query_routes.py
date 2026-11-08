from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from main.routes.ingestion_routes import get_active_service
import time


router = APIRouter(prefix="/api", tags=["query"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    query: str


class NodeResponse(BaseModel):
    text: str
    score: Optional[float] = None
    source: Optional[str] = None


class ValidationResults(BaseModel):
    input_allowed: bool
    input_block_reason: Optional[str] = None
    pii_detected: bool
    pii_summaries: List[str]
    output_sanitized: bool
    output_blocked: bool
    output_block_reason: Optional[str] = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    retrieved_nodes: List[NodeResponse]
    validation_results: ValidationResults


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    TODO: Implement the query endpoint
    
    Steps to implement:
    1. Start a performance timer
    2. Get the active RAG service using get_active_service()
    3. Call the service's query method with the user's query
    4. Transform the result into a QueryResponse object
    5. Handle exceptions appropriately
    
    Expected result structure from service.query():
    {
        "query": str,
        "answer": str,
        "retrieved_nodes": List[Dict[str, Any]],
        "validation_results": Dict[str, Any]
    }
    """
    try:
        # TODO: Start a performance timer
        # Hint: Record the current time using a high-resolution timer to measure processing duration
        t0 = time.perf_counter()

        # TODO: Get the active RAG service
        # Hint: Retrieve the currently active RAG service instance using the helper function
        service = get_active_service()

        # TODO: Call the service's query method with the user's query
        # Hint: Invoke the query method on the service with the query text from the request
        result = service.query(request.query)

        # TODO: Transform the result into a QueryResponse object
        # Hint: Map the service result to a QueryResponse by extracting the query text, answer, transforming the retrieved nodes list into NodeResponse objects with their text, optional score, and optional source, and converting the validation results into a ValidationResults object
        retrieved_nodes_data = result.get("retrieved_nodes", []) or []
        retrieved_nodes: List[NodeResponse] = []
        for n in retrieved_nodes_data:
            # n is expected to be a dict with keys 'text', 'score', 'source'
            retrieved_nodes.append(
                NodeResponse(
                    text=n.get("text", ""),
                    score=n.get("score"),
                    source=n.get("source"),
                )
            )

        vr = result.get("validation_results", {}) or {}
        validation_results = ValidationResults(
            input_allowed=vr.get("input_allowed", True),
            input_block_reason=vr.get("input_block_reason"),
            pii_detected=vr.get("pii_detected", False),
            pii_summaries=vr.get("pii_summaries", []),
            output_sanitized=vr.get("output_sanitized", False),
            output_blocked=vr.get("output_blocked", False),
            output_block_reason=vr.get("output_block_reason"),
        )

        response = QueryResponse(
            query=result.get("query", request.query),
            answer=result.get("answer", ""),
            retrieved_nodes=retrieved_nodes,
            validation_results=validation_results,
        )

        logger.info("query.done ms=%.1f", (time.perf_counter() - t0) * 1000)
        # TODO: Return the QueryResponse object
        return response
        
    except Exception as e:
        # TODO: Raise an HTTPException with status 500 and appropriate error message
        # Hint: Raise an HTTP exception with a 500 status code and include the error details in the response message
        logger.exception("query.error %s", e)
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
