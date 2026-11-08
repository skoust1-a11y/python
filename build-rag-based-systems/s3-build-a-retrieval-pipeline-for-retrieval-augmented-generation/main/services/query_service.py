"""
Query service for executing RAG queries with error handling.

TODO: Complete the implementation of query_with_error_handling() and evaluate_response() functions.
These functions handle query execution, error handling, and response evaluation in the RAG pipeline.
"""

# TODO: Import necessary modules
# Verify these imports are correct for your implementation:
from typing import Dict, Any
from datetime import datetime
from langchain_core.runnables import Runnable
from ..config import logger


def query_with_error_handling(
    rag_chain: Runnable, 
    retriever: Any, 
    query: str
) -> Dict[str, Any]:
    """
    Execute query with comprehensive error handling and validation.
    
    This function orchestrates the RAG query pipeline: validates input, retrieves documents,
    executes the RAG chain, validates the response, and analyzes quality metrics.
    
    Args:
        rag_chain: The LCEL chain that combines retriever, prompt, and LLM
        retriever: The retriever for fetching source documents from vectorstore
        query: User question string
        
    Returns:
        Dictionary containing:
        - query: Original query string
        - timestamp: ISO format timestamp
        - status: "success", "failed", or "unknown"
        - answer: Generated answer (if successful)
        - retrieved_chunks: Number of chunks retrieved
        - sources: List of source documents with metadata
        - quality_metrics: Dictionary with quality indicators
        - error: Error message (if failed)
        
    Hints:
        1. Initialize result dictionary with query, timestamp, and status
        2. Wrap the entire logic in try-except for error handling
        3. Validate input query (minimum 3 characters, not empty)
        4. If validation fails, set status to "failed" and return early
        5. Invoke retriever to get relevant documents
        6. Extract source information from retrieved documents (source, chunk_id, content preview)
        7. Invoke the RAG chain to get the answer
        8. Validate the response is not empty
        9. If response is empty, set status to "failed" and return
        10. Set answer and status to "success"
        11. Calculate quality metrics (has_answer, cited_sources, graceful_failure, contact_provided)
        12. In except block, set error details
    """
    # TODO: Step 1 - Initialize result dictionary
    # Include: query, timestamp (ISO format using datetime.now().isoformat()), status ("unknown")
    # This dictionary will be used throughout the function and returned at the end
    result: Dict[str, Any] = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "status": "unknown",
        "answer": "",
        "retrieved_chunks": 0,
        "sources": [],
        "quality_metrics": {},
        "error": None,
    }
    try:
        # TODO: Step 2 - Validate input query
        # Check if query is empty or less than 3 characters after stripping
        # If invalid, set status to "failed", add error message, and return result
        if not isinstance(query, str) or len(query.strip()) < 3:
            result["status"] = "failed"
            result["error"] = "Query must be a non-empty string with at least 3 characters"
            result["error_type"] = "ValidationError"
            logger.warning(f"Invalid query input: '{query}'")
            return result

        # TODO: Step 3 - Retrieve relevant documents
        # Invoke the retriever with the query
        # Store the number of retrieved chunks in result
        docs = []
        # Support both retriever.get_relevant_documents(query) and callable retriever(query)
        try:
            docs = retriever.invoke(query)
        except Exception:
            raise

        if docs is None:
            docs = []

        # TODO: Step 4 - Extract source information
        # Create a list of dictionaries with source metadata:
        #   - source: from doc.metadata.get('source', 'Unknown')
        #   - chunk_id: from doc.metadata.get('chunk_id', 'N/A')
        #   - content_preview: first 200 characters of doc.page_content + "..."
        # Store this list in result["sources"]
        sources = []
        for d in docs:
            try:
                meta = getattr(d, "metadata", {}) or {}
                page_content = getattr(d, "page_content", "") or str(d)
            except Exception:
                meta = {}
                page_content = str(d)

            content_preview = (page_content[:200] + "...") if len(page_content) > 200 else (page_content + "...")
            sources.append({
                "source": meta.get("source", "Unknown"),
                "chunk_id": str(meta.get("chunk_id", "N/A")),
                "content_preview": content_preview,
            })

        result["retrieved_chunks"] = len(sources)
        result["sources"] = sources

        # TODO: Step 5 - Execute RAG chain
        # Invoke the rag_chain with the query
        rag_response = None
        # Support Runnable.run, callables, and dict/string outputs
        if hasattr(rag_chain, "invoke"):
            try:
                rag_response = rag_chain.invoke(query)
            except TypeError:
                # some runnables expect different input shape
                rag_response = rag_chain.invoke({"input": query})
        elif callable(rag_chain):
            rag_response = rag_chain(query)
        else:
            # Fallback: try to convert to string
            rag_response = str(rag_chain)

        # TODO: Step 6 - Validate response
        # Check if response is empty or only whitespace
        # If empty, set status to "failed", add error message, and return result
        answer = ""
        if isinstance(rag_response, dict):
            # try common keys
            answer = (
                rag_response.get("answer")
                or rag_response.get("text")
                or rag_response.get("output")
                or rag_response.get("response")
                or "".join(str(v) for v in rag_response.values())
            )
        elif isinstance(rag_response, str):
            answer = rag_response
        else:
            answer = str(rag_response)

        if not answer or not answer.strip():
            result["status"] = "failed"
            result["error"] = "RAG chain returned an empty response"
            result["error_type"] = "EmptyResponseError"
            logger.warning("RAG chain produced empty response for query")
            return result

        # TODO: Step 7 - Set success status and answer
        # Store the response in result["answer"]
        # Set result["status"] to "success"
        result["answer"] = answer
        result["status"] = "success"

        # TODO: Step 8 - Calculate quality metrics
        # Create a dictionary with:
        #   - has_answer: boolean (response length > 0)
        #   - cited_sources: boolean (check if "Source" appears in response)
        #   - graceful_failure: boolean (check if "don't have enough information" in lowercase response)
        #   - contact_provided: boolean (check if support email or phone number in response)
        # Store in result["quality_metrics"]
        lower_ans = answer.lower()
        has_answer = bool(len(answer.strip()) > 0)
        cited_sources = "source" in lower_ans or "references" in lower_ans or "references:" in lower_ans
        graceful_failure = any(phrase in lower_ans for phrase in ["don't have enough information", "do not have enough information", "insufficient information", "cannot find", "cannot provide", "no information"])
        # basic email and phone detection
        import re
        contact_provided = bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", answer) or re.search(r"\+?\d[\d\-\s]{6,}\d", answer))

        result["quality_metrics"] = {
            "has_answer": has_answer,
            "cited_sources": cited_sources,
            "graceful_failure": graceful_failure,
            "contact_provided": contact_provided,
        }

        # TODO: Step 9 - Return the result dictionary
        return result

    except Exception as e:
        # TODO: Step 10 - Handle errors
        # Set result["status"] to "failed"
        # Set result["error"] with error message (str(e))
        # Set result["error_type"] with exception type name (type(e).__name__)
        # Return the result dictionary (do not raise - return the error result)
        result["status"] = "failed"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        logger.error(f"Error while processing query: {str(e)}", exc_info=True)
        return result


def evaluate_response(result: Dict[str, Any]) -> None:
    """
    Evaluate and display response quality metrics.
    
    This function logs comprehensive evaluation metrics for the query result,
    including status, retrieved chunks, quality indicators, and source information.
    
    Args:
        result: Query result dictionary from query_with_error_handling()
    """
    # TODO: Log the result dictionary
    # Placeholder - remove this line once you implement the function
    if not isinstance(result, dict):
        logger.warning("evaluate_response called with non-dict result")
        return

    try:
        status = result.get("status", "unknown")
        logger.info(f"Query evaluation - status: {status}")

        logger.debug(f"Timestamp: {result.get('timestamp')}")
        logger.debug(f"Retrieved chunks: {result.get('retrieved_chunks', 0)}")

        qm = result.get("quality_metrics", {})
        logger.info(
            f"Quality metrics: has_answer={qm.get('has_answer')}, cited_sources={qm.get('cited_sources')}, "
            f"graceful_failure={qm.get('graceful_failure')}, contact_provided={qm.get('contact_provided')}"
        )

        # Log error if present
        if status != "success":
            logger.warning(f"Query failed: {result.get('error')} (type: {result.get('error_type')})")

        # Log top sources (up to 5)
        sources = result.get("sources", [])
        if sources:
            for i, s in enumerate(sources[:5], start=1):
                logger.debug(
                    f"Source {i}: {s.get('source')} (chunk_id={s.get('chunk_id')}) preview={s.get('content_preview')}"
                )
        else:
            logger.debug("No sources returned for this query")

    except Exception as e:
        logger.error(f"Failed to evaluate response: {str(e)}", exc_info=True)
        return

