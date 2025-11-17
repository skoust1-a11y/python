# Sprint 1: RAG Infrastructure Setup — Embeddings & Vector Database

## Project Context

You're building **Smart Auto Advisor**, an AI-powered conversational assistant for car manufacturers that helps customers get instant answers about vehicle models, features, pricing, and availability.

The system uses **Retrieval-Augmented Generation (RAG)** to:

1. Convert customer questions into semantic embeddings
2. Search through company knowledge bases (manuals, specs, pricing, inventory)
3. Retrieve relevant information from a vector database
4. Generate accurate, sourced answers using an LLM

This sprint (S1) focuses on the **foundation layer** — setting up the vector database infrastructure and understanding how embeddings work.

---

## Problem Statement

Before building a RAG system, you need to understand:

- How text is converted into vector embeddings
- How to store and retrieve embeddings efficiently
- How semantic similarity search works
- How to perform CRUD operations on vector data

You will complete three tasks to build this foundation:

---

### **Task 1 — Setup PostgreSQL with PgVector Extension**

#### Goal

Prepare a PostgreSQL database with vector search capabilities.

#### Requirements

1. Install PostgreSQL 14+ on your system
2. Enable the PgVector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Verify the extension is installed:
   ```sql
   \dx
   ```

**Expected Output**: PgVector extension listed with version information

---

### **Task 2 — Generate and Store Embeddings**

#### Goal

Create vector embeddings for sample automotive text and store them in the database.

#### Requirements

1. Configure Azure OpenAI credentials in `.env`
2. Run the embedding setup script:
   ```bash
   uv run python main/embedding_setup.py
   ```
3. The script will:
   - Initialize Azure OpenAI embeddings (1536 dimensions)
   - Generate embeddings for sample automotive sentences
   - Create a PGVector vectorstore
   - Insert sample data with metadata
   - Read back stored rows for the configured collection
   - Run a similarity search against the inserted documents

**Expected Output**:

- Embeddings generated successfully
- Sample data inserted into `langchain_pg_embedding` table
- Confirmation messages in logs

---

### **Task 3 — Test CRUD Operations and Similarity Search**

#### Goal

Verify that you can create, read, and search vector embeddings through both the setup script and the REST API.

#### Requirements

The `embedding_setup.py` script automatically tests:

1. **CREATE**: Insert embeddings with metadata
2. **READ**: Retrieve stored embeddings
3. **SIMILARITY SEARCH**: Find semantically similar text
   - `perform_similarity_search()`: Returns top-k results with scores (can optionally return best result)

**Test Queries**:

- "What are the features and pricing of the EcoSport Hybrid?" → Should find vehicle model and pricing content

**Expected Output**:

- Create and read operations succeed
- Similarity search returns relevant results with distance/score
- API endpoints work correctly for uploading and querying documents

---

## Project Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ with PgVector extension
- Azure OpenAI API access
- UV package manager

### Project Structure

```
.
├── main/                     # Main application package
│   ├── __init__.py          # Package initialization
│   ├── app.py               # FastAPI application setup
│   ├── config.py            # Configuration and logging setup
│   ├── embedding_setup.py   # Setup script for DB check, embeddings, CRUD (create/read), search
│   ├── sample_data.py       # Sample automotive documents
│   ├── routes/              # API routes and models
│   │   ├── __init__.py
│   │   └── routes.py        # FastAPI routes and Pydantic models
│   └── services/            # Business logic services
│       ├── __init__.py
│       └── vectorstore_service.py  # Vectorstore operations service
├── tests/                    # Test suite
│   ├── __init__.py          # Test package initialization
│   ├── conftest.py          # Shared pytest fixtures
│   ├── test_config.py       # Tests for config.py
│   ├── test_embedding_setup.py  # Tests for embedding_setup.py
│   └── test_sample_data.py  # Tests for sample_data.py
├── main.py                  # Application entry point
├── pyproject.toml           # Project dependencies and configuration
├── uv.lock                  # Lock file for reproducible builds
├── .env                     # Environment variables (create this)
├── .gitignore              # Git ignore patterns
└── README.md               # This file
```

---

## Run the Application

1. Navigate to the project directory:

   ```bash
   cd <project-root>
   ```

2. Install dependencies using UV:

   **For Linux/Windows (Same command):**

   ```bash
   uv sync
   ```

   This will automatically:

   - Create a virtual environment
   - Install all dependencies from `pyproject.toml`
   - Set up the project environment

---

## Configuration

1. Create a `.env` file in the project root:

   **For Linux:**

   ```bash
   touch .env
   ```

   **For Windows (PowerShell):**

   ```powershell
   New-Item -Path .env -ItemType File
   ```

   **For Windows (CMD):**

   ```cmd
   type nul > .env
   ```

2. Add your configuration to the `.env` file:

   ```env
   # Database Configuration
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=db_name
   COLLECTION_NAME=smart_auto_advisor

   # Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your_azure_api_key
   AZURE_OPENAI_DEPLOYMENT=text-embedding-3-small
   AZURE_OPENAI_API_VERSION=2024-02-01

   # Vector Store Configuration
   COLLECTION_NAME=automind_embedding
   ```

   **Note**: Make sure there are no spaces around the `=` sign in the `.env` file.

   To get an Azure OpenAI API key:

   - Visit [Azure Portal](https://portal.azure.com/)
   - Create an Azure OpenAI resource
   - Deploy the `text-embedding-3-small` model
   - Copy the endpoint and API key

3. **Seed Initial Data** (Required before starting the API):

   Before starting the FastAPI application, you need to seed the vectorstore with initial sample data. The `embedding_setup.py` script will:

   - Verify database connection and PgVector extension
   - Initialize the vectorstore service
   - Insert sample documents from `sample_data.py` (vehicle catalog and pricing information)
   - Display stored embeddings
   - Run a test similarity search

   **For Linux/Windows (Same command):**

   ```bash
   uv run python main/embedding_setup.py
   ```

   **Expected Output**:

   ```
   ================================================================================
   TESTING DATABASE CONNECTION
   ================================================================================
   PostgreSQL version: PostgreSQL 14.x
   PgVector extension already enabled ✅

   ================================================================================
   INITIALIZING VECTORSTORE SERVICE
   ================================================================================
   ✅ Azure OpenAI Embedding model initialized
   ✅ PGVector store initialized

   ================================================================================
   INSERTING SAMPLE DOCUMENTS
   ================================================================================
   ✅ Inserted 2 documents
      - doc_vehicle_001: Vehicle Catalog
      - doc_pricing_001: Pricing Guide
   ```

   **Note**: On Windows, you can use either PowerShell or CMD for these commands.

   **Important**: You must run this script at least once before starting the FastAPI application to ensure the vectorstore has data to query.

4. **Start the FastAPI Application**:

   Once the initial data is seeded, start the FastAPI server:

   **For Linux/Windows (Same command):**

   ```bash
   uv run python main.py
   ```

   The API will be available at `http://localhost:8000`

   - API Documentation: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`

---

## Testing the Implementation

### Running Unit Tests

The project includes a comprehensive test suite using pytest. Run tests with:

```bash
# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=main --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=main --cov-report=html

# Run specific test file
uv run pytest tests/test_config.py
```

### Integration Testing

The `embedding_setup.py` script includes integration testing:

1. **Database Connection Test**: Verifies PostgreSQL and PgVector are working
2. **Embedding Generation Test**: Creates sample embeddings
3. **CRUD Operations Test**: Tests all database operations
4. **Similarity Search Test**: Performs semantic search

**Expected Console Output**:

```
================================================================================
TESTING DATABASE CONNECTION
================================================================================
PostgreSQL version: PostgreSQL 14.x
PgVector extension already enabled ✅

================================================================================
INITIALIZING AZURE EMBEDDINGS
================================================================================
✅ Azure OpenAI Embedding model ready

================================================================================
INITIALIZING PGVECTOR STORE
================================================================================

================================================================================
INSERTING SAMPLE DOCUMENTS
================================================================================
✅ Inserted 5 documents

================================================================================
READING EMBEDDINGS
================================================================================
📄 ID: ...
   Content: ...
   Metadata: {...}

================================================================================
SIMILARITY SEARCH FOR: How do we calibrate the engine sensor?
================================================================================
Rank 1 | Distance=... | Similarity=...
   Content: ...
   Metadata: {...}
```

---

## Key Implementation Details

### Embedding Model

- **Provider**: Azure OpenAI
- **Model**: text-embedding-3-small
- **Dimensions**: 1536
- **Use Case**: Semantic search for automotive content

### Vector Database

- **Database**: PostgreSQL 14+
- **Extension**: PgVector
- **Collection**: `automind_embedding`

### CRUD Operations

- **Create**: `vectorstore.add_documents(documents)` or via API endpoint `POST /api/v1/upload`
- **Read**: Direct SQL queries to `langchain_pg_embedding`
- **Search**: `POST /api/v1/query` - Returns top-k matching documents

---

## API Endpoints

The application provides REST API endpoints for uploading documents and querying the vectorstore.

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Upload Document

**Endpoint**: `POST /api/v1/upload`

**Description**: Upload/add string data to the vectorstore with a unique document ID.

**Request Body**:

```json
{
  "doc_id": "doc_vehicle_001",
  "content": "The 2024 EcoSport Hybrid model features a 2.5L hybrid powertrain delivering 191 horsepower, advanced driver-assistance systems including adaptive cruise control and lane-keeping assist, and a 12.3-inch infotainment display with wireless Apple CarPlay and Android Auto. Available in three trim levels: Base ($28,500), Premium ($32,000), and Luxury ($36,500).",
  "metadata": {
    "document": "Vehicle Catalog",
    "category": "Models & Features",
    "model": "EcoSport Hybrid 2024",
    "section": "Product Specifications"
  }
}
```

**Example 2 - Pricing Information**:

```json
{
  "doc_id": "doc_pricing_002",
  "content": "Pricing and availability for the 2024 EcoSport Hybrid: Base trim starts at $28,500 MSRP with financing options available at 2.9% APR for qualified buyers. Premium trim priced at $32,000 includes additional safety features and premium audio system. Current inventory status: 8 Base models, 5 Premium models, and 2 Luxury models available.",
  "metadata": {
    "document": "Pricing Guide",
    "category": "Pricing & Availability",
    "model": "EcoSport Hybrid 2024",
    "section": "Sales Information"
  }
}
```

**Example 3 - Maintenance Information**:

```json
{
  "doc_id": "doc_maintenance_003",
  "content": "Recommended maintenance schedule for EcoSport Hybrid: Oil change every 10,000 miles or 12 months, brake pad inspection at 30,000 miles, transmission fluid service at 60,000 miles. All maintenance services include complimentary multi-point inspection and tire rotation.",
  "metadata": {
    "document": "Maintenance Guide",
    "category": "Service & Maintenance",
    "model": "EcoSport Hybrid 2024",
    "section": "Maintenance Schedule"
  }
}
```

**Response**:

```json
{
  "success": true,
  "message": "Document added successfully",
  "document_id": "uuid-here"
}
```

#### 2. Query Vectorstore

**Endpoint**: `POST /api/v1/query`

**Description**: Query the vectorstore for semantically similar documents.

**Request Body**:

```json
{
  "query": "What are the features and pricing of the EcoSport Hybrid?",
  "top_k": 1
}
```

**Example 2 - Maintenance Query**:

```json
{
  "query": "When should I service the transmission?",
  "top_k": 2
}
```

**Example 3 - Pricing Query**:

```json
{
  "query": "What financing options are available?",
  "top_k": 1
}
```

**Response**:

```json
{
  "success": true,
  "query": "What are the features and pricing of the EcoSport Hybrid?",
  "results": [
    {
      "content": "The 2024 EcoSport Hybrid model features a 2.5L hybrid powertrain...",
      "metadata": {
        "id": "doc_vehicle_001",
        "document": "Vehicle Catalog",
        "category": "Models & Features",
        "model": "EcoSport Hybrid 2024"
      }
    }
  ],
  "count": 1
}
```

### API Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## How This Fits the RAG Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  S1: Infrastructure (You are here)                          │
│  • PostgreSQL + PgVector setup                              │
│  • Embedding generation                                     │
│  • CRUD operations                                          │
│  • Similarity search                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  S2: Ingestion Pipeline (Next Sprint)                       │
│  • Load documents (PDF, TXT, HTML)                          │
│  • Chunk text intelligently                                 │
│  • Generate embeddings at scale                             │
│  • Store in vector database                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  S3: Query Pipeline (Final Sprint)                          │
│  • Accept user questions                                    │
│  • Retrieve relevant context                                │
│  • Generate answers with LLM                                │
│  • Provide REST API                                         │
└─────────────────────────────────────────────────────────────┘
```
