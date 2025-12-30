from __future__ import annotations

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI

# Load env as early as possible
load_dotenv()

# Simple logging setup (can be controlled via LOG_LEVEL env var)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Configure LlamaIndex globally for this app
from llama_index.core import Settings
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding

_llm_deployment = os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT")
_embed_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
_api_key = os.getenv("AZURE_OPENAI_API_KEY")
_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
_api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# Configure models only when env vars are present (so the app can import without secrets)
if _llm_deployment and _api_key and _endpoint and _api_version:
    Settings.llm = AzureOpenAI(
        model="gpt-4o-mini",
        deployment_name=_llm_deployment,
        api_key=_api_key,
        azure_endpoint=_endpoint,
        api_version=_api_version,
    )
else:
    print("⚠ Azure OpenAI LLM not configured (missing AZURE_OPENAI_* env vars)")

if _embed_deployment and _api_key and _endpoint and _api_version:
    Settings.embed_model = AzureOpenAIEmbedding(
        model="text-embedding-3-small",
        deployment_name=_embed_deployment,
        api_key=_api_key,
        azure_endpoint=_endpoint,
        api_version=_api_version,
    )
else:
    print("⚠ Azure OpenAI embedding not configured (missing AZURE_OPENAI_* env vars)")

# Global guardrails validator (reused across requests)
from main.service.guardrails import GuardrailsValidator

_global_validator = GuardrailsValidator()
print("✓ Guardrails validator initialized")

# Import routers after globals are configured
from main.routes import ingestion_router, query_router

app = FastAPI(
    title="Investment Advisor RAG",
    description="Fusion Retrieval (BM25+Vector+RRF) + Guardrails (PII redaction, input blocking, non-toxic/professional responses)",
    version="0.1.0",
)

app.include_router(ingestion_router)
app.include_router(query_router)


def get_validator() -> GuardrailsValidator:
    return _global_validator


@app.get("/")
async def root():
    return {
        "message": "Investment Advisor RAG",
        "endpoints": {
            "ingest_upload": "/api/ingestion/upload",
            "query": "/api/query",
            "docs": "/docs",
        },
    }
