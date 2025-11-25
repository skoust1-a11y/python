# Sprint 3: RAG Query Pipeline — Semantic Retrieval & Answer Generation

## Project Context

You're building **Smart Auto Advisor**, an AI-powered conversational assistant for car manufacturers that helps customers get instant answers about vehicle models, features, pricing, and availability.

This sprint (S3) builds on **Sprint 1's infrastructure** and **Sprint 2's ingestion pipeline** to create a complete query system that retrieves relevant context and generates accurate, sourced answers using LLMs.

---

## How This Fits the RAG Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  S1: Infrastructure (Completed)                             │
│  • PostgreSQL + PgVector setup                              │
│  • Embedding generation                                     │
│  • CRUD operations                                          │
│  • Similarity search                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  S2: Ingestion Pipeline (Completed)                         │
│  • Load documents (PDF, TXT, HTML, Web)                     │
│  • Chunk text intelligently                                 │
│  • Generate embeddings at scale                             │
│  • Store in vector database                                 │
│  • REST API for document upload                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  S3: Query Pipeline (You are here)                           │
│  • Accept user questions                                    │
│  • Retrieve relevant context                                │
│  • Generate answers with LLM                               │
│  • Provide REST API                                         │
│  • Source citations                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Problem Statement

A RAG system needs to answer user questions by retrieving relevant context from the vector database and generating accurate, sourced responses. The system must handle queries efficiently, provide citations, and scale to serve multiple users simultaneously. Without a proper query pipeline, you can't transform stored embeddings into actionable answers.

**Solution:** A complete RAG query system with:

1. **Semantic Retrieval:** Find relevant document chunks using vector similarity
2. **Context Assembly:** Combine retrieved chunks into LLM prompts
3. **LLM Generation:** Generate accurate, sourced answers using Azure OpenAI
4. **REST API:** Expose query endpoints for web and mobile applications
5. **Error Handling:** Robust error handling and logging for production use

---

## Prerequisites

Before starting S3, ensure you have completed **Sprint 1** and **Sprint 2**:

- ✅ PostgreSQL 14+ with PgVector extension installed and configured (S1)
- ✅ Azure OpenAI API access with `text-embedding-3-small` and LLM deployment (S1)
- ✅ Vector database populated with document embeddings (S2)
- ✅ S1 and S2 infrastructure tested and working
- ✅ Database connection verified

---

## Project Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ with PgVector extension (from S1)
- Azure OpenAI API access with both embedding and LLM deployments (from S1)
- UV package manager
- Vector database populated with documents (from S2)

### Project Structure

```
.
├── main/                                    # Main application package
│   ├── __init__.py                         # Package initialization
│   ├── app.py                              # FastAPI application setup & lifecycle
│   ├── config.py                           # Configuration and logging setup
│   ├── prompts/                            # Prompt templates
│   │   ├── __init__.py
│   │   └── prompt_templates.py            # Production RAG prompt templates
│   ├── routes/                             # API routes
│   │   ├── __init__.py
│   │   └── query_routes.py                # FastAPI routes for query endpoints
│   └── services/                           # Business logic services
│       ├── __init__.py
│       ├── vectorstore_service.py         # Embedding generation & vectorstore setup
│       ├── llm_service.py                 # LLM initialization
│       ├── rag_chain_service.py           # RAG chain building with LCEL
│       └── query_service.py               # Query execution with error handling
├── tests/                                  # Test directory
│   ├── __init__.py
│   └── test_api_client.py                 # API client tests
├── main.py                                 # Application entry point (runs FastAPI server)
├── pyproject.toml                          # Project dependencies and configuration
├── uv.lock                                 # Lock file for reproducible builds
├── .env                                    # Environment variables (create this - not in git)
├── .env.example                            # Environment variables template
├── .gitignore                             # Git ignore patterns
└── README.md                              # This file
```

**Service Organization:**

- **Vectorstore**: `vectorstore_service.py` - Embeddings and PGVector connection
- **LLM**: `llm_service.py` - Azure OpenAI LLM initialization
- **RAG Chain**: `rag_chain_service.py` - LCEL chain orchestration
- **Query Execution**: `query_service.py` - Query handling with error management
- **Prompts**: `prompts/prompt_templates.py` - Production-ready prompt templates

---

## Run the Application

### Step 1: Install Dependencies

1. Navigate to the project directory:

   ```bash
   cd s3-build-rag-query-pipeline-with-langchain
   ```

2. Install dependencies using UV:

   ```bash
   uv sync
   ```

   This will automatically:

   - Create a virtual environment
   - Install all dependencies from `pyproject.toml`
   - Set up the project environment

### Step 2: Configure Your Environment

1. **Create `.env` file** in the project root (or copy from `.env.example`):

   **For Linux:**

   ```bash
   touch .env
   ```

   **For Windows (PowerShell):**

   ```powershell
   New-Item -Path .env -ItemType File
   ```

2. **Add Configuration**:

   ```env
   # Database Configuration (Same as S1 & S2)
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=automind_db
   COLLECTION_NAME=smart_auto_advisor

   # Azure OpenAI Configuration (Same as S1 & S2)
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your_azure_api_key
   AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
   AZURE_OPENAI_LLM_DEPLOYMENT=gpt-4o-mini
   AZURE_OPENAI_API_VERSION=2024-02-01

   # Retrieval Configuration (S3 specific)
   TOP_K=5

   # Optional: CORS Configuration
   CORS_ORIGINS=*
   ```

   **Note**: Make sure there are no spaces around the `=` sign in the `.env` file.

   **Important**:

   - Use the same database and collection name as S1 and S2 to maintain continuity
   - Default collection name is `smart_auto_advisor` (can be overridden with `COLLECTION_NAME`)
   - Ensure `AZURE_OPENAI_LLM_DEPLOYMENT` is set (required for S3)
   - The vector database should already be populated with embeddings from S2

### Step 3: Run the Query API Server

Start the FastAPI server:

```bash
uv run python main.py
```

Or using uvicorn directly:

```bash
uv run uvicorn main.app:app --reload --host 0.0.0.0 --port 8000
```

**Server Startup Output:**

```
INFO:     Starting AutoMind RAG API...
INFO:     ================================================================================
INFO:     Starting RAG API component initialization
INFO:     ================================================================================
INFO:     Step 1: Loading configuration
INFO:     Step 2: Initializing embedding model
INFO:     Step 3: Initializing LLM
INFO:     Step 4: Setting up vectorstore
INFO:     Step 5: Building RAG chain
INFO:     ================================================================================
INFO:     All components initialized successfully
INFO:     ================================================================================
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The API will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
- Root Endpoint: `http://localhost:8000/`

---

## API Endpoints

The application provides REST API endpoints for querying the RAG system.

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Root Endpoint

**Endpoint**: `GET /`

**Description**: API information and available endpoints.

**Response**:

```json
{
  "service": "AutoMind RAG Query API",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "query": "/query",
    "retrieve": "/retrieve",
    "health": "/health",
    "metrics": "/metrics",
    "docs": "/docs"
  }
}
```

#### 2. Health Check

**Endpoint**: `GET /health`

**Description**: Check API health status and component initialization.

**Response**:

```json
{
  "status": "healthy",
  "database_connected": true,
  "embedding_model_loaded": true,
  "llm_loaded": true,
  "timestamp": "2024-01-15T10:30:00"
}
```

#### 3. Metrics

**Endpoint**: `GET /metrics`

**Description**: Get pipeline metrics and statistics.

**Response**:

```json
{
  "total_queries": 42,
  "successful_queries": 40,
  "failed_queries": 2,
  "average_chunks_retrieved": 4.5,
  "uptime_seconds": 3600.5
}
```

#### 4. RAG Query (Full Pipeline)

**Endpoint**: `POST /query`

**Description**: Execute full RAG query with retrieval and LLM generation.

**Request Body**:

```json
{
  "question": "What are the benefits of EV Model?",
  "top_k": 5,
  "include_sources": true
}
```

**Response**:

```json
{
  "question": "What are the benefits of EV Model?",
  "answer": "The EV Model offers several key benefits including zero emissions, lower operating costs, instant torque, and reduced maintenance requirements. The battery warranty covers 8 years or 100,000 miles, providing peace of mind for owners.",
  "sources": [
    {
      "source": "ev_model_specs.pdf",
      "chunk_id": "12",
      "content": "The EV Model features zero emissions...",
      "relevance_score": null
    }
  ],
  "metadata": {
    "chunks_retrieved": 5,
    "top_k": 5,
    "model": "gpt-4o-mini",
    "has_sources": true,
    "graceful_failure": false
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

#### 5. Retrieval Only (Semantic Search)

**Endpoint**: `POST /retrieve`

**Description**: Retrieve relevant chunks without LLM generation (semantic search only).

**Request Body**:

```json
{
  "query": "battery warranty",
  "top_k": 3
}
```

**Response**:

```json
{
  "query": "battery warranty",
  "chunks": [
    {
      "source": "car_engine_manual.pdf",
      "chunk_id": "5",
      "content": "Battery warranty covers 8 years or 100,000 miles, whichever comes first...",
      "relevance_score": null
    }
  ],
  "count": 3,
  "timestamp": "2024-01-15T10:30:00"
}
```

### API Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Example API Usage

**Using curl:**

```bash
# Full RAG query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the benefits of EV Model?",
    "top_k": 5,
    "include_sources": true
  }'

# Retrieval only
curl -X POST "http://localhost:8000/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "battery warranty",
    "top_k": 3
  }'

# Health check
curl -X GET "http://localhost:8000/health"

# Metrics
curl -X GET "http://localhost:8000/metrics"
```

**Using Python:**

```python
from tests.test_api_client import AutoMindRAGClient

client = AutoMindRAGClient(base_url="http://localhost:8000")

# Full RAG query
result = client.query(
    question="What are the benefits of EV Model?",
    top_k=5,
    include_sources=True
)
print(result['answer'])

# Retrieval only
chunks = client.retrieve(query="battery warranty", top_k=3)
print(f"Retrieved {chunks['count']} chunks")
```

---

## Key Learning Concepts

| Step  | Technology           | Service                       | Purpose                                                                                      |
| :---- | :------------------- | :---------------------------- | :------------------------------------------------------------------------------------------- |
| **1** | **Vector Retrieval** | `vectorstore_service.py`      | **Relevance Finding:** Retrieves top-k most similar document chunks using cosine similarity. |
| **2** | **Prompt Templates** | `prompts/prompt_templates.py` | **Context Assembly:** Formats retrieved chunks into structured prompts for the LLM.          |
| **3** | **Azure OpenAI LLM** | `llm_service.py`              | **Answer Generation:** Generates accurate, context-aware responses using GPT models.         |
| **4** | **RAG Chain**        | `rag_chain_service.py`        | **Orchestration:** Combines retrieval → prompt → LLM → post-processing in a single pipeline. |
| **5** | **FastAPI**          | `routes/query_routes.py`      | **Production API:** Exposes query endpoints with automatic documentation and validation.     |
| **6** | **Source Citations** | `query_service.py`            | **Transparency:** Returns source documents and chunk IDs for answer verification.            |
| **7** | **Error Handling**   | `query_service.py`            | **Robustness:** Handles errors gracefully with fallback responses and comprehensive logging. |
| **8** | **LCEL**             | `rag_chain_service.py`        | **Composability:** Uses LangChain Expression Language for chain composition and streaming.   |

---

## Testing the Implementation

### Running Unit Tests

The project includes a test suite using pytest. Run tests with:

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_api_client.py

# Run tests and show coverage
uv run pytest --cov=main --cov-report=term-missing
```

### Test Structure

The test suite includes:

1. **Import Tests**: Verifies all module imports work correctly
2. **Configuration Tests**: Tests configuration loading and validation
3. **API Client Tests**: Integration tests for all API endpoints

**Note**: API client tests will be automatically skipped if the server is not running on `localhost:8000`.

### Manual Testing

You can also test the API using the interactive client:

```bash
# Run interactive mode
uv run python tests/test_api_client.py interactive

# Or run comprehensive test suite
uv run python tests/test_api_client.py
```

---

## Key Implementation Details

### Vector Retrieval

- **Database**: PostgreSQL with PgVector (from S1)
- **Collection**: `smart_auto_advisor` (default, configurable via `COLLECTION_NAME` - should match S1 & S2)
- **Search Type**: Similarity search with cosine distance
- **Default Top-K**: 5 chunks (configurable per query)
- **Service**: `vectorstore_service.py` using `PGVector` from LangChain

### Prompt Engineering

- **Template**: Production-ready prompt with hallucination prevention
- **Structure**: System message + context + user question
- **Features**:
  - Explicit instructions to use only provided context
  - Fallback message for insufficient information
  - Source citation requirements
  - Safety-critical question handling
- **Service**: `prompts/prompt_templates.py`

### LLM Configuration

- **Provider**: Azure OpenAI
- **Model**: `gpt-4o-mini` (configurable via `AZURE_OPENAI_LLM_DEPLOYMENT`)
- **Temperature**: 0.1 (for consistent, factual responses)
- **Max Tokens**: 1000
- **Service**: `llm_service.py` using `AzureChatOpenAI`

### RAG Chain (LCEL)

- **Framework**: LangChain Expression Language (LCEL)
- **Components**:
  1. Retriever (similarity search)
  2. Document formatter (adds source citations)
  3. Prompt template (context assembly)
  4. LLM (answer generation)
  5. Output parser (string extraction)
- **Service**: `rag_chain_service.py`

### Error Handling

- **Graceful Failures**: Returns helpful message when context is insufficient
- **Error Logging**: Comprehensive logging for debugging
- **HTTP Status Codes**: Appropriate status codes (400, 422, 500, 503)
- **Service**: `query_service.py`

### Modular Architecture

The project follows a modular, service-oriented architecture:

- **Separation of Concerns**: Each service has a single responsibility
- **Reusability**: Services can be used independently or together
- **Testability**: Each service can be tested in isolation
- **Maintainability**: Easy to extend with new features or models

---

## Summary

You've learned how to build a **production-ready RAG query system** that:

- ✅ Retrieves relevant context from vector databases using semantic search
- ✅ Generates accurate, sourced answers using LLMs
- ✅ Exposes REST API endpoints for web and mobile integration
- ✅ Provides source citations for answer verification
- ✅ Handles errors gracefully with comprehensive logging
- ✅ Uses LangChain LCEL for composable chain orchestration
- ✅ Integrates seamlessly with S1's infrastructure and S2's ingestion pipeline

This completes the RAG pipeline! Combined with S1 (infrastructure) and S2 (ingestion), you now have a full conversational AI system that can answer questions using your company knowledge base.

Perfect foundation for building **scalable AI-powered customer support and information retrieval systems**!

---

## Next Steps

After completing S3, you have a complete RAG system:

- **Sprint 1**: Infrastructure - Vector database and embedding setup ✅
- **Sprint 2**: Ingestion Pipeline - Document processing and storage ✅
- **Sprint 3**: Query Pipeline - Semantic retrieval and answer generation ✅

**Potential Enhancements:**

- Add authentication and authorization
- Implement rate limiting
- Add caching for frequently asked questions
- Implement streaming responses
- Add multi-turn conversation support
- Integrate with frontend applications

---

## Troubleshooting

### Common Issues

1. **Database Connection Errors**

   - Verify S1 infrastructure is running
   - Check `.env` file has correct database credentials
   - Ensure PostgreSQL and PgVector extension are installed
   - Verify `COLLECTION_NAME` matches the collection used in S1 & S2 (default: `smart_auto_advisor`)

2. **Azure OpenAI Errors**

   - Verify API key and endpoint are correct
   - Check deployment names match your Azure resource
   - Ensure `AZURE_OPENAI_LLM_DEPLOYMENT` is set (required for S3)
   - Verify you have sufficient API quota

3. **Empty Retrieval Results**

   - Ensure S2 ingestion pipeline has populated the vector database
   - Verify collection name matches S1 & S2
   - Check that documents were successfully embedded
   - Try increasing `top_k` value

4. **Import Errors**

   - Run `uv sync` to ensure all dependencies are installed
   - Check Python version is 3.12+
   - Verify you're in the correct directory

5. **Server Not Starting**

   - Check all required environment variables are set
   - Verify database connection is working
   - Check logs for initialization errors
   - Ensure port 8000 is not already in use

6. **CORS Errors**

   - Set `CORS_ORIGINS` in `.env` to specific domains for production
   - Default `*` allows all origins (development only)

---

## Additional Resources

- [LangChain Documentation](https://python.langchain.com/)
- [LangChain LCEL Guide](https://python.langchain.com/docs/expression_language/)
- [PgVector Documentation](https://github.com/pgvector/pgvector)
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
