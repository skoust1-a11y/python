# /// script
# dependencies = [
#   "ragas>=0.2.14",
#   "datasets>=3.0.0",
#   "httpx>=0.28.0",
#   "python-dotenv>=1.0.1",
#   "langchain-openai>=0.3.0",
#   "langchain-google-genai>=2.0.1",
#   "langfuse>=4.7.0",
# ]
# ///

import sys
from unittest.mock import MagicMock
# Mock VertexAI to prevent import errors in ragas (optional dependency issue)
sys.modules['langchain_community.chat_models.vertexai'] = MagicMock()

import os
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
import httpx
from langfuse import Langfuse, get_client

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("eval_navigator_langfuse")

# CONFIG
API_URL = os.getenv("API_URL", "http://localhost:8000/query")
BENCHMARK_PATH = Path("./data/evaluation/benchmark.json")
DATASET_NAME = "c3-legaldoc-navigator-eval"
RAGAS_MODEL = os.getenv("EVAL_RAGAS_MODEL", "gpt-4o-mini")

# Initialize Langfuse
Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)
langfuse = get_client()

async def setup_langfuse_dataset():
    """Create and populate the Langfuse Dataset from our local benchmark file."""
    if not BENCHMARK_PATH.exists():
        logger.error(f"Benchmark file not found at {BENCHMARK_PATH}")
        return False

    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    items = benchmark_data.get("items", [])
    if not items:
        logger.warning("No items found in benchmark dataset.")
        return False

    # Create the dataset
    try:
        langfuse.create_dataset(
            name=DATASET_NAME,
            description="Golden-set benchmark for C3 LegalDoc Navigator evaluation",
        )
        logger.info(f"Created Langfuse Dataset: {DATASET_NAME}")
    except Exception:
        # Dataset already exists
        logger.info(f"Langfuse Dataset '{DATASET_NAME}' already exists, continuing...")

    # Upload items (prevent duplicates)
    for item in items:
        try:
            langfuse.create_dataset_item(
                dataset_name=DATASET_NAME,
                input={"question": item["question"]},
                expected_output={"ground_truth": item["ground_truth"]},
            )
        except Exception:
            pass
            
    logger.info("Dataset populated on Langfuse.")
    return True

async def query_endpoint(client: httpx.AsyncClient, question: str) -> dict:
    """Send asynchronous request to local FastAPI query endpoint requesting contexts."""
    payload = {
        "question": question,
        "include_contexts": True
    }
    try:
        response = await client.post(API_URL, json=payload, timeout=60.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error querying endpoint for question '{question[:40]}...': {e}")
        return {}

async def run_evaluation():
    # Step 1: Ensure dataset is created and populated on Langfuse
    dataset_ready = await setup_langfuse_dataset()
    if not dataset_ready:
        return

    # Step 2: Get dataset items from Langfuse
    logger.info(f"Fetching dataset '{DATASET_NAME}' from Langfuse...")
    dataset = langfuse.get_dataset(DATASET_NAME)

    logger.info(f"Starting evaluation of {len(dataset.items)} items...")
    
    # Query API concurrently
    async with httpx.AsyncClient() as client:
        tasks = [query_endpoint(client, item.input["question"]) for item in dataset.items]
        api_responses = await asyncio.gather(*tasks)

    # Compile samples for Ragas and trace them to Langfuse
    samples = []
    eval_traces = []

    # Setup Ragas LLM & Embeddings (prefer Gemini to match default pipeline and avoid OpenAI quota limits)
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    use_gemini = bool(gemini_api_key)

    for idx, (item, api_resp) in enumerate(zip(dataset.items, api_responses)):
        question = item.input["question"]
        expected = item.expected_output["ground_truth"]

        if not api_resp:
            logger.warning(f"Skipping failed response for query: {question[:40]}")
            continue

        answer = api_resp.get("explain") or ""
        contexts = api_resp.get("contexts") or [""]

        # Track trace and link it to the Langfuse dataset item
        with langfuse.start_as_current_observation(
            name="legaldoc-navigator-eval-run",
            as_type="span",
            input=question,
            output={"answer": answer, "contexts": contexts},
        ) as span:
            # We save the trace ID and metadata to bind computed Ragas scores to it later
            trace_id = span.trace_id
            eval_traces.append({
                "trace_id": trace_id,
                "dataset_item": item,
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": expected,
            })

            samples.append({
                "user_input": question,
                "response": answer,
                "retrieved_contexts": contexts,
                "reference": expected,
            })

    if not samples:
        logger.error("No valid responses collected for evaluation.")
        return

    # Check if we can compute Ragas scores (requires active API key)
    if not gemini_api_key and not openai_api_key:
        logger.warning("No Gemini or OpenAI API keys found. Traces uploaded to Langfuse, but Ragas scores skipped.")
        return

    logger.info("Computing faithfulness and answer_relevance scores via Ragas...")
    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import Faithfulness, AnswerRelevancy
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper

    if use_gemini:
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_api_key,
            temperature=0,
        )
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-2",
            google_api_key=gemini_api_key,
        )
    else:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        llm = ChatOpenAI(
            model=RAGAS_MODEL,
            api_key=openai_api_key,
            temperature=0,
        )
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=openai_api_key,
        )

    ragas_llm = LangchainLLMWrapper(llm)
    ragas_embeddings = LangchainEmbeddingsWrapper(embeddings)

    metrics = [
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
    ]

    dataset_eval = EvaluationDataset.from_list(samples)
    
    try:
        results = evaluate(dataset=dataset_eval, metrics=metrics)
        print("\n" + "=" * 50)
        print(" RAGAS EVALUATION RESULTS")
        print("=" * 50)
        print(results)
        print("=" * 50 + "\n")

        # Map scores and upload them to Langfuse
        df = results.to_pandas()
        for idx, trace_info in enumerate(eval_traces):
            row = df.iloc[idx]
            faithfulness_val = float(row["faithfulness"]) if "faithfulness" in row and not pd_isna(row["faithfulness"]) else None
            relevance_val = float(row["answer_relevancy"]) if "answer_relevancy" in row and not pd_isna(row["answer_relevancy"]) else None

            # Link the trace run to the Langfuse dataset item for comparison
            trace_info["dataset_item"].link(
                trace_id=trace_info["trace_id"],
                run_name="legaldoc-navigator-ragas-eval",
            )

            # Log scores to Langfuse under the specific trace run
            if faithfulness_val is not None:
                langfuse.score(
                    trace_id=trace_info["trace_id"],
                    name="faithfulness",
                    value=faithfulness_val,
                )
            if relevance_val is not None:
                langfuse.score(
                    trace_id=trace_info["trace_id"],
                    name="answer_relevance",
                    value=relevance_val,
                )

        logger.info("Evaluation metrics successfully sent to Langfuse.")

    except Exception as e:
        logger.error(f"Failed to compute or upload Ragas scores: {e}")
        # Even if Ragas scoring fails (e.g. due to quota limit), we still link the trace runs to the dataset item
        for trace_info in eval_traces:
            trace_info["dataset_item"].link(
                trace_id=trace_info["trace_id"],
                run_name="legaldoc-navigator-eval-run-only",
            )
        logger.info("Uploaded traces and linked them to Langfuse dataset items.")

    finally:
        langfuse.flush()

def pd_isna(val):
    import pandas as pd
    return pd.isna(val)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
