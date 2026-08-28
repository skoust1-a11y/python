import logging
import time
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from graph import build_graph
import uvicorn

# TODO: Implement FastAPI application
# - Create FastAPI app
# - Build graph at startup
# - Create DocumentationRequest and DocumentationResponse
# - POST /generate endpoint:
#   - Accept DocumentationRequest (task_description, quality_threshold, max_iterations)
#   - Initialize state
#   - Run graph
#   - Return DocumentationResponse
# - GET /health endpoint
# - Print results to console



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent.log')
    ]
)

logger = logging.getLogger(__name__)

# TODO: Create FastAPI app
# 
# INSTRUCTIONS:
# 1. Initialize FastAPI app:
#    - title="Technical Documentation Generator"
#    - description="..."
#    - version="0.1.0"

app = FastAPI(
    title="Technical Documentation Generator with Self-Correction",
    description="AI agent that generates technical documentation for Python code and iteratively improves it through self-reflection",
    version="0.1.0"
)


# TODO: Build graph at startup
# 
# INSTRUCTIONS:
# 1. Call build_graph() and assign to doc_graph
# 2. Add logging to indicate startup

logger.info("Building documentation generation graph...")
doc_graph = build_graph()
logger.info("Graph built successfully")


# TODO: Implement DocumentationRequest and DocumentationResponse
# 
# INSTRUCTIONS:
# 1. DocumentationRequest(BaseModel):
#    - task_description: str (required)
#    - quality_threshold: float (default 8.0)
#    - max_iterations: int (default 3)
# 
# 2. DocumentationResponse(BaseModel):
#    - status: str
#    - task_description: str
#    - generated_documentation: str
#    - reflection_history: List[str]
#    - iterations: int
#    - final_quality_score: float
#    - approved: bool
#    - execution_time: float

class DocumentationRequest(BaseModel):
    task_description: str
    quality_threshold: float = 8.0
    max_iterations: int = 3

class DocumentationResponse(BaseModel):
    status: str
    task_description: str
    generated_documentation: str
    reflection_history: list[str]
    iterations: int
    final_quality_score: float
    approved: bool
    execution_time: float


# TODO: Implement POST /generate endpoint
@app.post("/generate", response_model=DocumentationResponse)
async def generate_documentation(request: DocumentationRequest):
    """Generate technical documentation for Python code."""
    # TODO: Implement endpoint logic
    # 
    # INSTRUCTIONS:
    # 1. Initialize state dictionary with:
    #    - task_description from request
    #    - quality_threshold from request
    #    - max_iterations from request
    #    - default values for other fields
    # 
    # 2. Invoke the graph:
    #    - Use `await asyncio.to_thread(doc_graph.invoke, ...)` to avoid blocking
    #    - Handle timeouts (optional but recommended)
    # 
    # 3. Process result:
    #    - Extract final state values
    #    - Calculate execution time
    # 
    # 4. Return DocumentationResponse

    start_time = time.time()
  
    init_state = {
        'task_description' : request.task_description,
        'quality_threshold': request.quality_threshold,
        'max_iterations':request.max_iterations,
        'messages':[],
        'draft_output' : "",
        'reflection_feedback': [],
        'iteration_count': 0,
        'quality_score': 0.0,
        'output_approved': False
    }
    timeout_seconds = 300
    try:
        logger.info("Starting graph execution...")
        result = await asyncio.wait_for(
                asyncio.to_thread(
                    doc_graph.invoke,
                    init_state,
                    {"recursion_limit": 50}
                ),
                timeout=timeout_seconds
            )
        elapsed_time = time.time() - start_time
        logger.info(f"Graph execution completed in {elapsed_time:.2f} seconds")
        logger.info(f"Final quality score: {result.get('quality_score', 0.0)}/10, Iterations: {result.get('iteration_count', 0)}")
        response = DocumentationResponse(
            status="success",
            task_description=request.task_description,
            generated_documentation=result.get("draft_output", ""),
            reflection_history=result.get("reflection_feedback", []),
            iterations=result.get("iteration_count", 0),
            final_quality_score=result.get("quality_score", 0.0),
            approved=result.get("output_approved", False),
            execution_time=elapsed_time
        )
        print("\n" + "=" * 60)
        print("DOCUMENTATION GENERATION RESULT:")
        print("=" * 60)
        print(f"Task: {response.task_description}")
        print(f"\nStatus: {response.status}")
        print(f"Execution Time: {response.execution_time:.2f} seconds")
        print(f"Iterations: {response.iterations}")
        print(f"Final Quality Score: {response.final_quality_score}/10")
        print(f"Approved: {response.approved}")
        
        print("\n" + "=" * 60)
        print("GENERATED DOCUMENTATION:")
        print("=" * 60)
        print(response.generated_documentation)
        
        print("\n" + "=" * 60)
        print("REFLECTION HISTORY:")
        print("=" * 60)
        for feedback in response.reflection_history:
            print(f"- {feedback}")
        print("=" * 60 + "\n")
        
        return response
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        elapsed_time = time.time() - start_time
        logger.error(f"Request timed out after {elapsed_time:.2f} seconds")
        raise HTTPException(
            status_code=504,
            detail=f"Request exceeded {timeout_seconds}s timeout. The agent may need more time to complete."
        )
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Error during execution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during documentation generation: {str(e)}")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Technical Documentation Generator with Self-Correction"
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
