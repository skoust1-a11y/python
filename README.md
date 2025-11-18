# Sprint 2: RAG Ingestion Pipeline — Document Processing & Vector Storage

## Project Context

You're building **Smart Auto Advisor**, an AI-powered conversational assistant for car manufacturers that helps customers get instant answers about vehicle models, features, pricing, and availability.

This sprint (S2) builds on **Sprint 1's infrastructure** to create a complete document ingestion pipeline that transforms raw documents (PDFs, HTML, text files) into searchable vector embeddings.

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
│  S2: Ingestion Pipeline (You are here)                      │
│  • Load documents (PDF, TXT, HTML, Web)                     │
│  • Chunk text intelligently                                 │
│  • Generate embeddings at scale                             │
│  • Store in vector database                                 │
│  • REST API for document upload                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  S3: Query Pipeline (Next Sprint)                           │
│  • Accept user questions                                    │
│  • Retrieve relevant context                                │
│  • Generate answers with LLM                                │
│  • Provide REST API                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Problem Statement

Real-world RAG systems need to process diverse document formats (PDFs, web pages, text files) and convert them into searchable vectors. Documents must be split into manageable chunks, embedded, and stored with metadata for accurate retrieval. Without a proper ingestion pipeline, you can't populate your knowledge base with company documents, product specs, or customer data.

You will complete three tasks to build this ingestion pipeline:

---

### **Task 1 — Document Loading and Processing**

#### Goal

Load documents from multiple sources (PDF, HTML, TXT, Web) and process them for ingestion.

#### Requirements

1. Implement document loaders for different file types:

   - PDF documents using `PyPDFLoader`
   - Text files using `TextLoader`
   - HTML files using `BSHTMLLoader`
   - Web pages using `WebBaseLoader`

2. Create a document processing service that:

   - Automatically detects file type
   - Routes files to appropriate loaders
   - Handles errors gracefully
   - Preserves source file metadata

3. Test document loading:
   ```bash
   # Test with sample documents
   uv run python -c "from main.services.document_processing_service import DocumentProcessingService; service = DocumentProcessingService(); docs = service.process_file('Documents/sample.pdf'); print(f'Loaded {len(docs)} documents')"
   ```

**Expected Output**: Documents loaded successfully with metadata preserved

---

### **Task 2 — Document Chunking and Embedding**

#### Goal

Split documents into manageable chunks and generate vector embeddings.

#### Requirements

1. Implement intelligent chunking:

   - Use `RecursiveCharacterTextSplitter`
   - Configure chunk size (default: 1000 characters)
   - Set chunk overlap (default: 200 characters)
   - Preserve sentence boundaries and context

2. Generate embeddings:

   - Use Azure OpenAI `text-embedding-3-small` model
   - Batch process chunks for efficiency
   - Store embeddings in PgVector database

3. Test chunking and embedding:
   ```bash
   # Test chunking service
   uv run python -c "from main.services.chunking_service import ChunkingService; from main.services.embedding_service import EmbeddingService; chunker = ChunkingService(); embedder = EmbeddingService(); print('Services initialized')"
   ```

**Expected Output**: Documents chunked and embeddings generated successfully

---

### **Task 3 — Complete Pipeline and REST API**

#### Goal

Build a complete ingestion pipeline with REST API endpoints for document upload and querying.

#### Requirements

1. Create pipeline orchestration service:

   - Coordinate document loading, chunking, and embedding
   - Handle batch processing
   - Provide error handling and logging

2. Implement REST API endpoints:

   - `POST /api/v1/upload` - Upload single document (auto-process)
   - `POST /api/v1/upload-multiple` - Upload multiple documents (auto-process)
   - `POST /api/v1/query` - Query vector database
   - `GET /api/v1/documents` - List all documents
   - `DELETE /api/v1/documents/{filename}` - Delete document

3. Test the complete pipeline:

   ```bash
   # Start the API server
   uv run python main.py

   # Upload a document
   curl -X POST "http://localhost:8000/api/v1/upload" \
     -F "file=@Documents/sample.pdf"

   # Query the database
   curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What are the key features?", "top_k": 5}'
   ```

**Expected Output**:

- Documents uploaded and processed successfully
- Embeddings stored in vector database
- Query returns relevant results with scores

---

## Prerequisites

Before starting S2, ensure you have completed **Sprint 1**:

- ✅ PostgreSQL 14+ with PgVector extension installed and configured
- ✅ Azure OpenAI API access with `text-embedding-3-small` deployment
- ✅ S1 infrastructure tested and working
- ✅ Database connection verified

---

## Project Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ with PgVector extension (from S1)
- Azure OpenAI API access (from S1)
- UV package manager

### Project Structure

```
.
├── main/                                    # Main application package
│   ├── __init__.py                         # Package initialization
│   ├── app.py                              # FastAPI application setup
│   ├── config.py                           # Configuration and logging setup
│   ├── routes/                             # API routes
│   │   ├── __init__.py
│   │   └── ingestion_routes.py            # FastAPI routes for ingestion & query
│   ├── services/                           # Business logic services
│   │   ├── __init__.py
│   │   ├── # Document Loaders
│   │   ├── pdf_loader_service.py          # PDF document loading service
│   │   ├── text_loader_service.py         # Text file loading service
│   │   ├── html_loader_service.py         # HTML file loading service (uses BSHTMLLoader)
│   │   ├── web_loader_service.py          # Web page loading service
│   │   ├── # Document Processing
│   │   ├── document_processing_service.py  # Multi-source processing & file type detection
│   │   ├── chunking_service.py            # Document chunking service
│   │   ├── # Orchestration
│   │   ├── injection_pipeline_service.py  # Complete pipeline orchestration
│   │   ├── # Storage & Query
│   │   ├── embedding_service.py           # Embedding generation & vector storage
│   │   └── query_service.py               # Vector similarity search service
│   └── utils/                              # Utility functions
│       ├── __init__.py
│       ├── file_type_detector.py          # File type detection utility
│       └── file_utils.py                  # File management utilities
├── Documents/                              # Documents directory (all uploaded files stored here)
│   ├── *.pdf                               # PDF documents
│   ├── *.txt                               # Text documents
│   └── *.html                              # HTML documents
├── tests/                                  # Test directory
│   ├── __init__.py
│   ├── test_pipeline.py                   # Pipeline tests
│   └── verify_ingestion.py                # Ingestion verification script
├── main.py                                 # Application entry point (runs FastAPI server)
├── pyproject.toml                          # Project dependencies and configuration
├── uv.lock                                 # Lock file for reproducible builds
├── .env                                    # Environment variables (create this - not in git)
├── .env.example                            # Environment variables template
├── .gitignore                             # Git ignore patterns
└── README.md                              # This file

Note: Old files at root level (config.py, utils.py, rag_ingestion_pipeline.py, api.py)
      are deprecated and kept for reference only. Use the modular structure in main/.
```

---

## Run the Application

### Step 1: Install Dependencies

1. Navigate to the project directory:

   ```bash
   cd s2-build-rag-ingestion-pipeline-with-langchain
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

2. **Add Configuration** (same as S1, but with optional chunking settings):

   ```env
   # Database Configuration (Same as S1)
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=automind_db
   COLLECTION_NAME=automind_embedding

   # Azure OpenAI Configuration (Same as S1)
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your_azure_api_key
   AZURE_OPENAI_DEPLOYMENT=text-embedding-3-small
   AZURE_OPENAI_API_VERSION=2024-02-01

   # Chunking Configuration (Optional - S2 specific)
   CHUNK_SIZE=1000
   CHUNK_OVERLAP=200
   ```

   **Note**: Make sure there are no spaces around the `=` sign in the `.env` file.

   **Important**: Use the same database and collection name as S1 to maintain continuity.

3. **Prepare Documents**: Place your documents in the `Documents/` folder (PDF, TXT, HTML files).

### Step 3: Run the Ingestion Pipeline

**Option A: REST API Ingestion (Recommended)**

Start the FastAPI server:

```bash
uv run python main.py
```

The API will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

Then upload documents via HTTP (documents are automatically processed and embeddings stored):

```bash
# Upload a single document (automatically processes and stores embeddings)
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@Documents/sample.pdf"

# Upload multiple documents (automatically processes and stores embeddings)
# Note: Use the same field name 'files' for all files
curl -X POST "http://localhost:8000/api/v1/upload-multiple" \
  -F "files=@Documents/sample.pdf" \
  -F "files=@Documents/policy.txt" \
  -F "files=@Documents/guidelines.txt"

# Query the vector database
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the key features?", "top_k": 5}'
```

---

## API Endpoints

The application provides REST API endpoints for document ingestion and querying.

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Health Check

**Endpoint**: `GET /health`

**Description**: Check API health status.

**Response**:

```json
{
  "status": "healthy",
  "documents_dir": "/path/to/Documents",
  "total_documents": 3
}
```

#### 2. List Documents

**Endpoint**: `GET /api/v1/documents`

**Description**: List all uploaded documents.

**Response**:

```json
[
  {
    "filename": "sample.pdf",
    "size": 102400,
    "extension": ".pdf",
    "uploaded_at": "2024-01-15T10:30:00"
  }
]
```

#### 3. Upload Document

**Endpoint**: `POST /api/v1/upload`

**Description**: Upload a single document (PDF, TXT, or HTML) and automatically generate embeddings.

**Request**: `multipart/form-data` with `file` field

**Response**:

```json
{
  "filename": "20240115_103000_sample.pdf",
  "size": 102400,
  "saved_path": "Documents/20240115_103000_sample.pdf",
  "message": "Document uploaded and processed successfully",
  "chunks_created": 15,
  "embeddings_stored": 15
}
```

#### 4. Upload Multiple Documents

**Endpoint**: `POST /api/v1/upload-multiple`

**Description**: Upload multiple documents at once. Each document is automatically processed and embeddings are stored.

**Request**: `multipart/form-data` with multiple `files`

**Response**:

```json
[
  {
    "filename": "sample.pdf",
    "size": 102400,
    "saved_path": "Documents/sample.pdf",
    "message": "Uploaded and processed successfully",
    "chunks_created": 15,
    "embeddings_stored": 15
  }
]
```

#### 5. Query Vector Database

**Endpoint**: `POST /api/v1/query`

**Description**: Query the vector database for semantically similar documents.

**Request Body**:

```json
{
  "query": "What are the key features?",
  "top_k": 5
}
```

**Response**:

```json
{
  "success": true,
  "query": "What are the key features?",
  "results": [
    {
      "content": "The system includes advanced features...",
      "metadata": {
        "source_file": "sample.pdf",
        "file_type": "pdf",
        "chunk_id": 5
      },
      "score": 0.85
    }
  ],
  "count": 1
}
```

#### 6. Delete Document

**Endpoint**: `DELETE /api/v1/documents/{filename}`

**Description**: Delete a specific document.

**Response**:

```json
{
  "status": "success",
  "message": "Deleted document: sample.pdf"
}
```

#### 7. Delete All Documents

**Endpoint**: `DELETE /api/v1/documents`

**Description**: Delete all documents from the Documents directory.

**Response**:

```json
{
  "status": "success",
  "message": "Deleted 3 document(s)",
  "deleted_count": 3
}
```

### API Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Key Learning Concepts

| Step  | Technology                  | Service                                                                                              | Purpose                                                                                   |
| :---- | :-------------------------- | :--------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------- |
| **1** | **Document Loaders**        | `pdf_loader_service.py`, `text_loader_service.py`, `html_loader_service.py`, `web_loader_service.py` | **Format Support:** Handles PDF, HTML, TXT, Web with automatic parsing.                   |
| **2** | **Document Processing**     | `document_processing_service.py`                                                                     | **Multi-Source:** Routes files to appropriate loaders based on type.                      |
| **3** | **Text Splitters**          | `chunking_service.py`                                                                                | **Chunking Strategy:** Splits documents while preserving sentence boundaries and context. |
| **4** | **Azure OpenAI Embeddings** | `embedding_service.py`                                                                               | **Vector Generation:** Converts text chunks into searchable embeddings.                   |
| **5** | **PgVector Storage**        | `embedding_service.py`                                                                               | **Persistent Storage:** Stores embeddings with metadata for fast retrieval.               |
| **6** | **Metadata Enrichment**     | All services                                                                                         | **Source Tracking:** Preserves file name, page number, and document type for citations.   |
| **7** | **Pipeline Orchestration**  | `injection_pipeline_service.py`                                                                      | **Workflow:** Coordinates all steps from loading to storage.                              |
| **8** | **Query Service**           | `query_service.py`                                                                                   | **Retrieval:** Performs similarity search on stored embeddings.                           |
| **9** | **REST API**                | `ingestion_routes.py`                                                                                | **Production Ready:** Enables programmatic document upload and ingestion workflows.       |

---

## Testing the Implementation

### Running Unit Tests

The project includes a test suite using pytest. Run tests with:

```bash
# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=main --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=main --cov-report=html

# Run specific test file
uv run pytest tests/test_pipeline.py
```

### Integration Testing

The test suite includes integration testing:

1. **Document Loading Test**: Verifies all document loaders work correctly
2. **Chunking Test**: Tests document chunking with various sizes
3. **Embedding Generation Test**: Creates embeddings for chunks
4. **Storage Test**: Stores embeddings in vector database
5. **Query Test**: Performs similarity search on stored data

Run integration tests:

```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_pipeline.py

# Verify ingestion manually
uv run python tests/verify_ingestion.py
```

---

## Key Implementation Details

### Document Loaders

- **PDF**: `PyPDFLoader` from LangChain Community
- **Text**: `TextLoader` with UTF-8 encoding
- **HTML**: `BSHTMLLoader` (BeautifulSoup-based)
- **Web**: `WebBaseLoader` for web page scraping

### Chunking Strategy

- **Splitter**: `RecursiveCharacterTextSplitter`
- **Default Chunk Size**: 1000 characters (~200-250 tokens)
- **Default Overlap**: 200 characters (~40-50 tokens)
- **Separators**: `["\n\n", "\n", ". ", " ", ""]` (preserves context)

### Embedding Model

- **Provider**: Azure OpenAI
- **Model**: text-embedding-3-small
- **Dimensions**: 1536
- **Use Case**: Semantic search for document content

### Vector Database

- **Database**: PostgreSQL 14+ (from S1)
- **Extension**: PgVector (from S1)
- **Collection**: `automind_embedding` (same as S1)

### Modular Architecture

The project follows a modular, service-oriented architecture:

- **Separation of Concerns**: Each service has a single responsibility
- **Reusability**: Services can be used independently or together
- **Testability**: Each service can be tested in isolation
- **Maintainability**: Easy to extend with new document types or processing steps

---

## Summary

You've learned how to build a **production-ready document ingestion pipeline** that:

- ✅ Loads documents from multiple formats (PDF, HTML, TXT, Web)
- ✅ Intelligently chunks text while preserving context
- ✅ Generates embeddings in batch for efficiency
- ✅ Stores vectors with rich metadata for source attribution
- ✅ Provides REST API endpoints for automated workflows
- ✅ Uses modular, reusable service components
- ✅ Integrates seamlessly with S1's infrastructure

This pipeline populates your vector database, enabling the query pipeline (S3) to answer customer questions using your company knowledge base!

---

## Next Steps

After completing S2, you're ready for:

- **Sprint 3**: Query Pipeline - Build the RAG query system that retrieves relevant context and generates answers using an LLM

---

## Troubleshooting

### Common Issues

1. **Database Connection Errors**

   - Verify S1 infrastructure is running
   - Check `.env` file has correct database credentials
   - Ensure PostgreSQL and PgVector extension are installed

2. **Azure OpenAI Errors**

   - Verify API key and endpoint are correct
   - Check deployment name matches your Azure resource
   - Ensure you have sufficient API quota

3. **Document Loading Failures**

   - Verify file format is supported (PDF, TXT, HTML)
   - Check file is not corrupted
   - Ensure file size is within limits (10 MB default)

4. **Import Errors**
   - Run `uv sync` to ensure all dependencies are installed
   - Check Python version is 3.12+
   - Verify you're in the correct directory

---

## Additional Resources

- [LangChain Documentation](https://python.langchain.com/)
- [PgVector Documentation](https://github.com/pgvector/pgvector)
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
