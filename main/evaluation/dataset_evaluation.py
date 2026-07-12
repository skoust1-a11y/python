"""
LLM-as-a-Judge Evaluators and Evaluation Pipeline
Implements faithfulness and answer relevance evaluators, plus end-to-end evaluation pipeline.

TODO: Implement the evaluator functions and evaluation pipeline below.
"""

import os
import re
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
    judge_prompt = f"""You are an expert evaluator assessing the FAITHFULNESS of an AI-generated answer.
Faithfulness measures whether the answer is fully grounded in and supported by the retrieved context.

Question:
{query}

Retrieved Context:
{context}

Answer:
{answer}

Evaluate whether every claim in the answer can be verified from the retrieved context, with no
hallucinated or unsupported information.

Scoring criteria (0.0 to 1.0):
- 1.0: All claims are fully supported by the context.
- 0.7-0.9: Most claims supported, minor unsupported details.
- 0.4-0.6: Some claims supported, some unsupported.
- 0.1-0.3: Most claims unsupported by the context.
- 0.0: The answer is not supported by the context at all.

Respond in exactly this format:
Reasoning: <brief explanation>
Score: <a single number between 0.0 and 1.0>
"""

    judgment = str(Settings.llm.complete(judge_prompt))

    score = 0.0
    for line in judgment.splitlines():
        if "score:" in line.lower():
            match = re.search(r"[-+]?\d*\.?\d+", line)
            if match:
                score = float(match.group())
                break

    score = max(0.0, min(1.0, score))

    langfuse.create_score(
        trace_id=trace_id,
        name="faithfulness",
        value=score,
        comment=judgment,
    )

    return score


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
    judge_prompt = f"""You are an expert evaluator assessing the ANSWER RELEVANCE of an AI-generated answer.
Answer relevance measures how well the answer addresses and directly responds to the user's question.

Question:
{query}

Answer:
{answer}

Evaluate whether the answer is on-topic, complete, and directly addresses the question asked.

Scoring criteria (0.0 to 1.0):
- 1.0: The answer fully and directly addresses the question.
- 0.7-0.9: The answer mostly addresses the question with minor gaps.
- 0.4-0.6: The answer partially addresses the question.
- 0.1-0.3: The answer is mostly off-topic or incomplete.
- 0.0: The answer does not address the question at all.

Respond in exactly this format:
Reasoning: <brief explanation>
Score: <a single number between 0.0 and 1.0>
"""

    judgment = str(Settings.llm.complete(judge_prompt))

    score = 0.0
    for line in judgment.splitlines():
        if "score:" in line.lower():
            match = re.search(r"[-+]?\d*\.?\d+", line)
            if match:
                score = float(match.group())
                break

    score = max(0.0, min(1.0, score))

    langfuse.create_score(
        trace_id=trace_id,
        name="answer_relevance",
        value=score,
        comment=judgment,
    )

    return score


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
    span = langfuse.start_span(
        name="rag_query_evaluation",
        input={"question": question},
        metadata={
            "expected_output": expected_output,
            "similarity_top_k": similarity_top_k,
        },
    )
    trace_id = span.trace_id

    query_engine = get_query_engine(similarity_top_k=similarity_top_k)
    response = query_engine.query(question)
    answer = str(response)

    context_chunks = []
    if hasattr(response, "source_nodes") and response.source_nodes:
        for node in response.source_nodes:
            text = getattr(node, "text", "") or ""
            context_chunks.append(text)
    context = "\n\n".join(context_chunks)

    faithfulness, answer_relevance = await asyncio.gather(
        evaluate_faithfulness_score(langfuse, trace_id, question, context, answer),
        evaluate_answer_relevance(langfuse, trace_id, question, answer),
    )

    span.update(
        output={
            "answer": answer,
            "faithfulness": faithfulness,
            "answer_relevance": answer_relevance,
        }
    )
    span.end()

    return {
        "question": question,
        "answer": answer,
        "trace_id": trace_id,
        "faithfulness": faithfulness,
        "answer_relevance": answer_relevance,
    }


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
    SLO_THRESHOLD = 0.7

    # 1. Initialize RAG services and load/index documents
    initialize_services()
    documents = load_documents()
    add_documents_to_index(documents)

    # 2. Get Langfuse client and load dataset
    langfuse = get_langfuse_client()
    dataset = langfuse.get_dataset(DATASET_NAME)

    # 3. Loop through dataset items and evaluate each
    results = []
    for item in dataset.items:
        logger.info(f"Evaluating: {item.input}")
        result = await query_with_evaluation(
            langfuse,
            question=item.input,
            expected_output=item.expected_output,
        )
        results.append(result)

    langfuse.flush()

    # 4. Calculate aggregate metrics
    if not results:
        logger.warning("No results to evaluate.")
        return results

    total = len(results)
    avg_faithfulness = sum(r["faithfulness"] for r in results) / total
    avg_relevance = sum(r["answer_relevance"] for r in results) / total

    faithfulness_pass = sum(1 for r in results if r["faithfulness"] >= SLO_THRESHOLD)
    relevance_pass = sum(1 for r in results if r["answer_relevance"] >= SLO_THRESHOLD)
    faithfulness_compliance = faithfulness_pass / total * 100
    relevance_compliance = relevance_pass / total * 100

    lowest_scoring = sorted(
        results,
        key=lambda r: (r["faithfulness"] + r["answer_relevance"]) / 2,
    )[:3]

    # 5. Log results
    logger.info("=" * 60)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total questions evaluated : {total}")
    logger.info(f"Average faithfulness      : {avg_faithfulness:.2f}")
    logger.info(f"Average answer relevance  : {avg_relevance:.2f}")
    logger.info(
        f"SLO threshold             : {SLO_THRESHOLD}"
    )
    logger.info(
        f"Faithfulness SLO compliance: {faithfulness_compliance:.1f}% "
        f"({faithfulness_pass}/{total})"
    )
    logger.info(
        f"Relevance SLO compliance   : {relevance_compliance:.1f}% "
        f"({relevance_pass}/{total})"
    )
    logger.info("-" * 60)
    logger.info("Lowest scoring questions:")
    for r in lowest_scoring:
        avg = (r["faithfulness"] + r["answer_relevance"]) / 2
        logger.info(
            f"  [{avg:.2f}] {r['question']} "
            f"(faithfulness={r['faithfulness']:.2f}, relevance={r['answer_relevance']:.2f})"
        )
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    asyncio.run(run_dataset_evaluation())
