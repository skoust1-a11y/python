# C3 LegalDoc Navigator

Production-grade **AI Legal Document Analysis System** built with Python 3.12, FastAPI, LlamaIndex, PostgreSQL 16 + pgvector, and a React frontend. Upload legal documents, ask natural-language questions, and receive grounded answers with citations—routed automatically through RAG, structured SQL, or hybrid retrieval.

For detailed architecture diagrams (system, sequence, class, ER, RAG pipeline, query router, hybrid retrieval, guardrails, deployment), see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 |
| API | FastAPI + Uvicorn |
| RAG | LlamaIndex |
| Database | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 (async) |
| LLMs | OpenAI (primary), Anthropic (fallback) |
| Safety | Guardrails AI |
| Observability | Langfuse (optional) |
| Frontend | React 19 + Vite + Tailwind CSS 4 |
| Cloud deployment | Vercel + Render + Neon + Qdrant + S3 |

## Features

- **Document ingestion** — PDF, DOCX, and TXT parsing with structure-aware chunking and OCR for scanned PDFs
- **Semantic search** — pgvector cosine similarity over OpenAI embeddings
- **Intelligent routing** — LLM classifies queries into RAG, SQL, or hybrid retrieval paths
- **Hybrid retrieval** — Parallel vector + SQL + optional MCP external search with RRF merge
- **Guardrails** — Pre-query validation and post-response safety checks with legal disclaimers
- **Human handoff** — Automatic escalation for low-confidence or high-risk queries
- **Feedback & evaluation** — User ratings and offline RAGAS benchmarks

## Prerequisites

- **Python 3.12+**
- **Node.js 20+** (for the frontend)
- **PostgreSQL + pgvector** (local, Supabase, or optional Docker for development)
- **OpenAI API key** (required for embeddings and chat)
- **Anthropic API key** (optional, used as LLM fallback)

## Cloud Deployment

The production deployment uses managed services and does not require Docker:

- Frontend: Vercel
- Backend: Render
- Database: Neon PostgreSQL
- Vector search: Qdrant Cloud
- File storage: S3-compatible object storage (AWS S3 / Cloudflare R2)
- Secrets: platform environment variables

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the complete deployment guide.

## Quick Start

### 1. Clone and configure environment

```bash
git clone <repository-url>
cd c3-legaldoc-navigator

cp .env.example .env
```

Edit `.env` and set at minimum:

```env
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key   # optional fallback
DATABASE_URL=postgresql+asyncpg://legaldoc:legaldoc_secret@localhost:5432/legaldoc_navigator
DATABASE_SYNC_URL=postgresql+psycopg2://legaldoc:legaldoc_secret@localhost:5432/legaldoc_navigator
```

### 2. Start PostgreSQL locally

```bash
docker compose up -d postgres
```

Wait for the health check to pass:

```bash
docker compose ps
```

### 3. Install Python dependencies

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the API is running:

- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

### 6. Start the frontend (optional)

In a separate terminal:

```bash
cd frontend
cp .env.example .env    # if present; defaults work with Vite proxy
npm install
npm run dev
```

Open http://localhost:3000 — the Vite dev server proxies API calls to port 8000.

### 7. Upload a sample document

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@data/uploads/sample_contract.txt"
```

### 8. Ask a question

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key terms in this contract?"}'
```

## Optional Local Docker (Full Stack)

Run both the API and PostgreSQL in containers:

```bash
cp .env.example .env
# Edit .env with your API keys

docker compose up --build
```

This starts:

| Service | Container | Port |
|---|---|---|
| API | `legaldoc-api` | 8000 |
| PostgreSQL | `legaldoc-postgres` | 5432 |

Run migrations inside the API container:

```bash
docker compose exec api alembic upgrade head
```

Upload storage is persisted via volume mount at `./data/uploads`.

## Project Structure

```
c3-legaldoc-navigator/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/                    # HTTP route handlers
│   ├── router/                 # Route aggregation
│   ├── services/               # Application / use-case layer
│   ├── ingestion/              # Document parsing & chunking
│   ├── rag/                    # RAG & hybrid retrieval pipelines
│   ├── routing/                # LLM query router
│   ├── guardrails/             # Input/output safety validation
│   ├── handoff/                # Human escalation logic
│   ├── mcp/                    # MCP external legal search
│   ├── evaluation/             # RAGAS benchmarks & tracing
│   ├── models/                 # ORM entities & Pydantic schemas
│   ├── database/               # DB engine & sessions
│   ├── prompts/                # LLM prompt templates
│   └── core/                   # Config, exceptions, logging
├── frontend/                   # React + Vite UI
├── alembic/                    # Database migrations
├── data/
│   ├── uploads/                # Uploaded document storage
│   └── evaluation/             # Benchmark datasets & results
├── docs/
│   └── ARCHITECTURE.md         # Architecture documentation (Mermaid)
├── scripts/                    # DB init scripts
├── docker-compose.yml
├── render.yaml
├── runtime.txt
├── requirements.txt
└── .env.example
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/upload` | Upload and index a legal document (PDF, DOCX, TXT) |
| `GET` | `/documents` | List indexed documents (paginated) |
| `GET` | `/document/{document_id}` | Get document details |
| `POST` | `/query` | Ask a question (RAG / SQL / hybrid) |
| `POST` | `/feedback` | Submit user rating (1–5) |
| `POST` | `/handoff` | Evaluate or create human escalation |

Interactive API docs: http://localhost:8000/docs

## Environment Variables

See [`.env.example`](.env.example) for the complete list. Key variables:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL connection string | — |
| `DATABASE_SYNC_URL` | Sync URL for Alembic migrations | — |
| `OPENAI_API_KEY` | OpenAI API key (embeddings + chat) | — |
| `ANTHROPIC_API_KEY` | Anthropic API key (fallback chat) | — |
| `VECTOR_DIMENSION` | Embedding vector size | 1536 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Ingestion chunking parameters | 1024 / 128 |
| `TOP_K_RETRIEVAL` | Chunks retrieved per query | 5 |
| `SIMILARITY_THRESHOLD` | Minimum cosine similarity | 0.7 |
| `ENABLE_GUARDRAILS` | Toggle safety validation | true |
| `MCP_ENABLED` | Enable external MCP legal search | false |
| `ENABLE_LANGFUSE` | Enable observability tracing | false |

## Development

### Linting

```bash
ruff check app/
```

### Tests

```bash
pytest
```

### Frontend build

```bash
cd frontend
npm run build
```

For production, set `VITE_API_BASE_URL` to your API host (e.g. `http://localhost:8000`).

### Offline evaluation

Run RAGAS benchmarks against the golden dataset:

```bash
python -m app.evaluation.runner
```

Results are written to `data/evaluation/results/`.

## Architecture Overview

```
Upload PDF/DOCX/TXT
      │
      ▼
  Ingestion Pipeline  ──►  Structure-aware Chunker
      │                         │
      ▼                         ▼
  OpenAI Embeddings  ──►  pgvector (document_embeddings)
                                  │
User Question ──► Guardrails ──► Query Router ──► RAG | SQL | Hybrid
                                  │                    │
                                  ▼                    ▼
                          Guardrails (post)     LLM Synthesis
                                  │
                                  ▼
                          QueryResponse + citations
```

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for full Mermaid diagrams covering system architecture, sequence flows, class diagrams, ER schema, RAG pipeline, query router, hybrid retrieval, guardrails, and deployment topology.

## License

Internal — C3 Project.
