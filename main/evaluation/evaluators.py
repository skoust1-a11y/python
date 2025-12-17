"""
LLM-as-a-Judge Evaluators and Evaluation Pipeline
Implements faithfulness and answer relevance evaluators, plus end-to-end evaluation pipeline.

TODO: Implement the evaluator functions and evaluation pipeline below.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langfuse import Langfuse
from llama_index.core.settings import Settings

from main.service.rag_service import initialize_services, get_query_engine, add_documents_to_index, get_embed_model
from main.service.indexing import load_documents
from main.evaluation.dataset import get_langfuse_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()

DATASET_NAME = "product_manual"


async def evaluate_faithfulness_score(
    langfuse,
    trace_id: str,
    query: str,
    context: str,
    answer: str,
) -> float:
    """
    Evaluate if answer is grounded in retrieved context (0.0 - 1.0).
    
    TODO: 
    1. Create judge prompt with question, context, answer, and scoring criteria (0.0-1.0 scale)
    2. Use Settings.llm.complete(judge_prompt) to get judgment
    3. Extract score from judgment text (look for "Score:" line)
    4. Clamp score to 0.0-1.0 range
    5. Attach to Langfuse using langfuse.create_score(trace_id, name="faithfulness", value=score, comment=judgment)
    6. Return score
    """
    # TODO: Implement this function
    return 0.0


async def evaluate_answer_relevance(
    langfuse,
    trace_id: str,
    query: str,
    answer: str,
) -> float:
    """
    Evaluate how well the answer addresses the question (0.0 - 1.0).
    
    TODO: Similar to evaluate_faithfulness_score but for answer relevance.
    Create prompt with question and answer, get LLM judgment, extract score, attach to Langfuse with name="answer_relevance"
    """
    # TODO: Implement this function
    return 0.0


async def query_with_evaluation(
    langfuse: Langfuse,
    question: str,
    expected_output: Optional[str] = None,
    similarity_top_k: int = 2,
) -> Dict[str, Any]:
    """
    Execute a RAG query and trigger automated evaluation.
    
    TODO:
    1. Create Langfuse span with langfuse.start_span()
    2. Get query engine and execute query
    3. Extract answer and build context from source_nodes
    4. Run evaluate_faithfulness_score and evaluate_answer_relevance asynchronously
    5. Update span with output and end it
    6. Return dict with question, answer, trace_id, faithfulness, answer_relevance
    """
    # TODO: Implement this function
    return {}


async def run_dataset_evaluation():
    """
    Evaluation Pipeline: Initialize RAG, load dataset, run evaluation on all items, calculate metrics.
    
    TODO:
    1. Initialize RAG services and load/index documents
    2. Get Langfuse client and load dataset
    3. Loop through dataset items, call query_with_evaluation() for each
    4. Calculate aggregate metrics (average scores, SLO compliance, lowest scoring questions)
    5. Log results and return
    """
    # TODO: Implement this function
    return []


if __name__ == "__main__":
    asyncio.run(run_dataset_evaluation())
