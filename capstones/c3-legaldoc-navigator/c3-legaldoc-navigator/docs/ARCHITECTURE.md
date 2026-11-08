# C3 LegalDoc Navigator — Architecture Documentation

Production-grade **AI Legal Document Analysis System** built with Python 3.12, FastAPI, LlamaIndex, PostgreSQL 16 + pgvector, and a React frontend. The system ingests legal documents (PDF, DOCX, TXT), indexes them for semantic search, and answers natural-language questions via RAG, structured SQL retrieval, or a hybrid of both—with optional external legal database search via MCP.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Sequence Diagrams](#2-sequence-diagrams)
3. [Class Diagram](#3-class-diagram)
4. [Entity-Relationship Diagram](#4-entity-relationship-diagram)
5. [RAG Pipeline](#5-rag-pipeline)
6. [Query Router](#6-query-router)
7. [Hybrid Retrieval Flow](#7-hybrid-retrieval-flow)
8. [Guardrails](#8-guardrails)
9. [Deployment Diagram](#9-deployment-diagram)

---

## 1. System Architecture

The application follows **Clean Architecture**: dependencies flow inward from presentation → application → domain → infrastructure.

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        UI["React + Vite UI<br/>(port 3000)"]
    end

    subgraph Presentation["Presentation Layer"]
        Main["main.py<br/>FastAPI App"]
        API["app/api/*<br/>HTTP Handlers"]
        Router["app/router/api_router.py"]
    end

    subgraph Application["Application Layer"]
        QS["QueryService"]
        DS["DocumentService"]
        HS["HandoffService"]
        FS["FeedbackService"]
        QD["QueryDispatcher"]
        GV["GuardrailValidator"]
    end

    subgraph Domain["Domain Layer"]
        Ingest["IngestionPipeline"]
        RAG["RAGPipeline"]
        Hybrid["HybridPipeline"]
        Route["Router"]
        Handoff["HandoffEvaluator"]
        Eval["BenchmarkRunner"]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        DB[("PostgreSQL 16<br/>+ pgvector")]
        OpenAI["OpenAI API<br/>(embeddings + chat)"]
        Anthropic["Anthropic API<br/>(fallback chat)"]
        MCP["MCP Servers<br/>(external legal DBs)"]
        Langfuse["Langfuse<br/>(observability)"]
        Storage["Local Upload Storage<br/>data/uploads/"]
    end

    UI -->|HTTP REST| Main
    Main --> Router --> API
    API --> QS & DS & HS & FS
    QS --> GV & QD
    QD --> Route & RAG & Hybrid
    DS --> Ingest
    HS --> Handoff
    Ingest --> Storage
    Ingest --> OpenAI
    RAG --> DB
    RAG --> OpenAI & Anthropic
    Hybrid --> DB
    Hybrid --> OpenAI & Anthropic
    Hybrid --> MCP
    QS --> Langfuse
    DS --> DB
    Ingest --> DB
```

### Layer Responsibilities

| Layer | Packages | Responsibility |
|---|---|---|
| **Presentation** | `app/api/`, `app/router/`, `app/main.py` | HTTP routing, request validation, response mapping |
| **Application** | `app/services/`, `app/guardrails/` | Use-case orchestration, guardrail enforcement |
| **Domain** | `app/ingestion/`, `app/rag/`, `app/routing/`, `app/handoff/`, `app/evaluation/` | Business logic, retrieval pipelines, routing |
| **Infrastructure** | `app/database/`, `app/core/`, `app/mcp/`, `app/utils/` | Persistence, config, external integrations |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/upload` | Upload and index a legal document |
| `GET` | `/documents` | Paginated document list |
| `GET` | `/document/{document_id}` | Document detail |
| `POST` | `/query` | RAG / SQL / hybrid Q&A |
| `POST` | `/feedback` | Submit user rating (1–5) |
| `POST` | `/handoff` | Evaluate or create human escalation |

---

## 2. Sequence Diagrams

### 2.1 Document Upload & Indexing

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React UI
    participant API as Upload API
    participant DS as DocumentService
    participant IP as IngestionPipeline
    participant PF as ParserFactory
    participant CH as LegalDocumentChunker
    participant VS as VectorStoreService
    participant ES as EmbeddingService
    participant DB as PostgreSQL

    User->>UI: Select PDF/DOCX/TXT file
    UI->>API: POST /upload (multipart)
    API->>DS: upload_document(file)

    DS->>DS: Validate extension & size
    DS->>DS: Save file to UPLOAD_DIR
    DS->>DS: Compute content hash
    DS->>DB: INSERT Document (status=processing)

    DS->>IP: ingest(file_path)
    IP->>PF: select_parser(file_type)
    PF-->>IP: PDF / DOCX / TXT parser
    IP->>IP: parse document text
    IP->>CH: chunk (structure-aware, tiktoken)
    CH-->>IP: TextNode[]

    DS->>VS: embed_and_store(document_id, nodes)
    VS->>ES: embed_texts(chunks)
    ES->>ES: OpenAI text-embedding-3-small
    ES-->>VS: vectors (1536-dim)
    VS->>DB: INSERT DocumentEmbedding rows

    DS->>DB: UPDATE Document (status=indexed, chunk_count)
    DS-->>API: DocumentUploadResponse
    API-->>UI: 200 OK + document metadata
    UI-->>User: Upload success
```

### 2.2 Query Processing (Full Lifecycle)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React UI
    participant API as Query API
    participant QS as QueryService
    participant GV as GuardrailValidator
    participant QD as QueryDispatcher
    participant RT as Router
    participant LLM as LLM Service
    participant Pipe as RAG / Hybrid Pipeline
    participant DB as PostgreSQL
    participant MCP as MCP Servers
    participant LF as Langfuse

    User->>UI: Ask legal question
    UI->>API: POST /query {question, document_id?}
    API->>QS: ask(request)

    QS->>GV: validate_query(question)
    alt Blocked query
        GV-->>QS: GuardrailViolationError
        QS-->>UI: 400 Bad Request
    end

    QS->>LF: start_trace(query)
    QS->>QD: dispatch(question)

    QD->>RT: route(question)
    RT->>LLM: classify (rag | sql | hybrid)
    LLM-->>RT: RoutingResult
    RT-->>QD: route + confidence + reason

    alt route = rag
        QD->>Pipe: RAGEngine.query()
        Pipe->>DB: pgvector cosine search
        Pipe->>LLM: synthesize answer (COMPACT mode)
    else route = sql
        QD->>LLM: SqlQueryPlanner.plan()
        QD->>Pipe: HybridPipeline.run_sql()
        Pipe->>DB: ORM structured queries
        Pipe->>LLM: synthesize_from_context()
    else route = hybrid
        QD->>LLM: SqlQueryPlanner.plan()
        QD->>Pipe: HybridPipeline.run_hybrid()
        par Parallel retrieval
            Pipe->>DB: pgvector search
            Pipe->>DB: SQL queries (clauses, cases, statutes)
            Pipe->>MCP: external legal search
        end
        Pipe->>Pipe: RRF merge + deduplicate
        Pipe->>LLM: synthesize_from_context()
    end

    Pipe-->>QD: QueryResult
    QD-->>QS: answer + sources + confidence

    QS->>GV: validate_response_detailed(answer, sources)
    alt Guardrail violation
        GV->>GV: get_fallback_response()
    end
    GV->>GV: append legal disclaimer
    GV-->>QS: GuardrailValidationResult

    QS->>LF: end_trace(result)
    QS-->>API: QueryResponse
    API-->>UI: answer + citations + routing metadata
    UI-->>User: Display grounded answer
```

### 2.3 Human Handoff Escalation

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Handoff API
    participant HS as HandoffService
    participant EV as HandoffEvaluator
    participant SM as SummaryGenerator
    participant DB as PostgreSQL

    User->>API: POST /handoff {query, answer, confidence, sources}
    API->>HS: evaluate_and_escalate()

    HS->>EV: evaluate_escalation_triggers()
    EV->>EV: Check confidence threshold
    EV->>EV: Check citation presence
    EV->>EV: Check high-risk patterns

    alt Escalation triggered
        HS->>SM: generate_summary(conversation)
        SM-->>HS: structured summary
        HS->>DB: INSERT HandoffEscalation (status=pending)
        HS-->>API: HandoffResponse (escalated=true)
    else No escalation
        HS-->>API: HandoffResponse (escalated=false)
    end

    API-->>User: Escalation result
```

---

## 3. Class Diagram

Core classes across the application, domain, and infrastructure layers.

```mermaid
classDiagram
    direction TB

    %% Presentation
    class FastAPIApp {
        +create_app() FastAPI
        +lifespan()
    }

    %% Application Services
    class QueryService {
        -guardrail_validator: GuardrailValidator
        -dispatcher: QueryDispatcher
        +ask(request: QueryRequest) QueryResponse
    }

    class DocumentService {
        -ingestion_pipeline: IngestionPipeline
        -vector_store: VectorStoreService
        +upload_document(file) DocumentUploadResponse
        +list_documents() list
        +get_document(id) DocumentDetail
    }

    class QueryDispatcher {
        -router: Router
        -rag_engine: RAGEngine
        -hybrid_pipeline: HybridPipeline
        -sql_planner: SqlQueryPlanner
        +dispatch(question) QueryResult
    }

    class LLMService {
        +get_llm(provider) LLM
    }

    class EmbeddingService {
        +embed_texts(texts) list~vector~
    }

    class SearchService {
        +search(query, top_k) list~SearchHit~
    }

    class VectorStoreService {
        +embed_and_store(doc_id, nodes) int
    }

    %% Domain - Routing
    class Router {
        -registry: RouteRegistry
        -llm_service: LLMService
        +route(query) RoutingResult
    }

    class RouteRegistry {
        -routes: dict
        +register(route: RouteDefinition)
        +names() frozenset
    }

    class RoutingResult {
        +route: str
        +reason: str
        +confidence: float
    }

    %% Domain - RAG
    class RAGPipeline {
        -session: AsyncSession
        -llm_service: LLMService
        -embedding_service: EmbeddingService
        +run(question) RAGPipelineResult
    }

    class RAGEngine {
        -pipeline: RAGPipeline
        +query(question) RAGPipelineResult
    }

    class LegalDocumentRetriever {
        -search_service: SearchService
        +aretrieve(query_bundle) list~Node~
    }

    class LegalContextBuilder {
        +build(nodes) str
    }

    class LegalResponseSynthesizer {
        -llm: LLM
        +synthesize(question, context) str
        +synthesize_from_context(question, nodes) str
    }

    class HybridPipeline {
        -session: AsyncSession
        -sql_planner: SqlQueryPlanner
        -external_search: ExternalLegalSearchService
        +run_hybrid(question, plan) HybridPipelineResult
        +run_sql(question, plan) HybridPipelineResult
    }

    class SqlQueryPlanner {
        +plan(question) SqlQueryPlan
    }

    class SqlQueryExecutor {
        +execute(plan) SqlRetrievalResult
    }

    %% Domain - Ingestion
    class IngestionPipeline {
        -parser_factory: ParserFactory
        -chunker: LegalDocumentChunker
        +ingest(path) list~TextNode~
    }

    class ParserFactory {
        +select_parser(file_type) DocumentParser
    }

    class LegalDocumentChunker {
        +chunk(text, metadata) list~TextNode~
    }

    %% Guardrails
    class GuardrailValidator {
        -guard: Guard
        +validate_query(query) void
        +validate_response_detailed(response) GuardrailValidationResult
    }

    class LegalAdviceDetector {
        +validate(value, metadata) ValidationResult
    }

    class CitationRequiredValidator {
        +validate(value, metadata) ValidationResult
    }

    class UnsupportedClaimDetector {
        +validate(value, metadata) ValidationResult
    }

    %% MCP
    class ExternalLegalSearchService {
        -connection_manager: MCPConnectionManager
        +search(query) ExternalSearchResult
    }

    class MCPConnectionManager {
        +search_all(query) list~ExternalLegalHit~
    }

    %% Relationships
    FastAPIApp --> QueryService
    FastAPIApp --> DocumentService
    QueryService --> GuardrailValidator
    QueryService --> QueryDispatcher
    QueryDispatcher --> Router
    QueryDispatcher --> RAGEngine
    QueryDispatcher --> HybridPipeline
    QueryDispatcher --> SqlQueryPlanner
    Router --> RouteRegistry
    Router --> LLMService
    RAGEngine --> RAGPipeline
    RAGPipeline --> LegalDocumentRetriever
    RAGPipeline --> LegalContextBuilder
    RAGPipeline --> LegalResponseSynthesizer
    RAGPipeline --> SearchService
    HybridPipeline --> LegalDocumentRetriever
    HybridPipeline --> SqlQueryExecutor
    HybridPipeline --> ExternalLegalSearchService
    HybridPipeline --> LegalResponseSynthesizer
    DocumentService --> IngestionPipeline
    DocumentService --> VectorStoreService
    IngestionPipeline --> ParserFactory
    IngestionPipeline --> LegalDocumentChunker
    SearchService --> EmbeddingService
    VectorStoreService --> EmbeddingService
    GuardrailValidator --> LegalAdviceDetector
    GuardrailValidator --> CitationRequiredValidator
    GuardrailValidator --> UnsupportedClaimDetector
    ExternalLegalSearchService --> MCPConnectionManager
    LegalDocumentRetriever --> SearchService
    SqlQueryPlanner --> LLMService
    LegalResponseSynthesizer --> LLMService
```

---

## 4. Entity-Relationship Diagram

PostgreSQL schema managed by Alembic migrations (`alembic/versions/001`–`005`).

```mermaid
erDiagram
    User ||--o{ Document : owns
    User ||--o{ ChatHistory : has
    User ||--o{ HandoffEscalation : requests

    Document ||--o{ Clause : contains
    Document ||--o{ DocumentEmbedding : has
    Document ||--o{ Citation : "sources (document)"
    Document ||--o{ Feedback : receives
    Document ||--o{ ChatHistory : scoped_to
    Document ||--o{ HandoffEscalation : scoped_to

    Clause ||--o{ Clause : "parent/child"
    Clause ||--o{ DocumentEmbedding : links
    Clause ||--o{ Citation : "sources (clause)"

    Case ||--o{ Citation : cited_in
    Statute ||--o{ Citation : cited_in

    User {
        uuid id PK
        string email UK
        string hashed_password
        string role
        boolean is_active
        datetime created_at
    }

    Document {
        uuid id PK
        uuid user_id FK
        string filename
        string file_type
        string status
        string content_hash
        int chunk_count
        string contract_id UK
        array parties_involved
        jsonb doc_metadata
    }

    Clause {
        uuid id PK
        uuid document_id FK
        uuid parent_clause_id FK
        string clause_number
        text content
        string risk_level
        int position_order
    }

    DocumentEmbedding {
        uuid id PK
        uuid document_id FK
        uuid clause_id FK
        int chunk_index
        vector embedding
        text chunk_text
        string embedding_model
    }

    Case {
        uuid id PK
        string case_citation UK
        string case_name
        string court
        string jurisdiction
        vector embedding
        text full_text
    }

    Statute {
        uuid id PK
        string statute_code UK
        string section_number
        string jurisdiction
        vector embedding
        text full_text
    }

    Citation {
        uuid id PK
        string source_type
        uuid source_document_id FK
        uuid source_clause_id FK
        uuid cited_case_id FK
        uuid cited_statute_id FK
        text citation_text
    }

    Feedback {
        uuid id PK
        int rating
        text query_text
        uuid document_id FK
        uuid session_id
    }

    HandoffEscalation {
        uuid id PK
        uuid session_id
        uuid user_id FK
        uuid document_id FK
        text query_text
        text summary
        jsonb conversation_history
        jsonb sources
        float confidence_score
        jsonb escalation_reasons
        string status
    }

    ChatHistory {
        uuid id PK
        uuid user_id FK
        uuid document_id FK
        uuid session_id
        string role
        text message
        string provider
        string model
    }
```

> **Note:** Upload currently populates `documents` and `document_embeddings`. The `clauses`, `cases`, `statutes`, and `citations` tables support structured SQL and hybrid retrieval when pre-seeded with reference data.

---

## 5. RAG Pipeline

The RAG pipeline performs semantic retrieval over document embeddings stored in pgvector, then synthesizes a grounded answer using LlamaIndex COMPACT mode.

```mermaid
flowchart LR
    subgraph Input
        Q["User Question"]
        DID["document_id (optional filter)"]
    end

    subgraph Retrieval
        ES["EmbeddingService<br/>text-embedding-3-small"]
        SS["SearchService<br/>pgvector cosine similarity"]
        RET["LegalDocumentRetriever<br/>top_k + threshold filter"]
    end

    subgraph Context
        CB["LegalContextBuilder<br/>numbered [Source N] blocks"]
    end

    subgraph Generation
        SYN["LegalResponseSynthesizer<br/>LlamaIndex COMPACT mode"]
        LLM["OpenAI / Anthropic LLM"]
    end

    subgraph Output
        CONF["compute_confidence_score<br/>rank-weighted avg"]
        RES["RAGPipelineResult<br/>answer + sources + confidence"]
    end

    Q --> RET
    DID --> RET
    RET --> ES
    ES --> SS
    SS -->|"top_k nodes"| CB
    CB --> SYN
    SYN --> LLM
    LLM --> SYN
    SYN --> CONF
    CONF --> RES
```

### RAG Configuration

| Parameter | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | 1024 | Token chunk size during ingestion |
| `CHUNK_OVERLAP` | 128 | Overlap between consecutive chunks |
| `TOP_K_RETRIEVAL` | 5 | Number of chunks retrieved per query |
| `SIMILARITY_THRESHOLD` | 0.7 | Minimum cosine similarity score |
| `VECTOR_DIMENSION` | 1536 | Embedding vector size |
| `OPENAI_EMBEDDING_MODEL` | text-embedding-3-small | Embedding model |

### Pipeline Stages

1. **Embed query** — Convert the user question to a 1536-dimensional vector via OpenAI.
2. **Vector search** — Query `document_embeddings` using pgvector IVFFlat cosine distance, optionally scoped to a single document.
3. **Build context** — Format retrieved chunks into numbered source blocks for the LLM prompt.
4. **Synthesize** — LlamaIndex COMPACT synthesis generates an answer grounded in the retrieved context.
5. **Score confidence** — Rank-weighted average of retrieval similarity scores (0.0–1.0).

---

## 6. Query Router

An LLM-powered classifier selects the optimal retrieval strategy based on query intent.

```mermaid
flowchart TD
    Q["User Question"] --> RT["Router.route()"]

    RT --> LLM["LLM Classification<br/>(OpenAI / Anthropic)"]
    LLM --> JSON{"Parse JSON response<br/>{route, reason, confidence}"}

    JSON -->|valid route| VAL{"Validate route<br/>in RouteRegistry"}
    JSON -->|invalid / missing| FB["Fallback → rag"]

    VAL -->|rag| R1["Semantic search over<br/>document embeddings"]
    VAL -->|sql| R2["Structured ORM queries<br/>on clauses, cases, statutes"]
    VAL -->|hybrid| R3["Parallel vector + SQL<br/>+ optional MCP search"]

    VAL -->|unknown route| FB
    VAL -->|low confidence| FB

    R1 --> QD["QueryDispatcher"]
    R2 --> QD
    R3 --> QD
    FB --> QD

    QD --> OUT["QueryResult<br/>+ RoutingResult metadata"]
```

### Route Definitions

| Route | Use Case | Example Queries |
|---|---|---|
| **rag** | Semantic search over document text | "Summarize this NDA", "What does the indemnity clause say?" |
| **sql** | Structured metadata / entity lookups | "List all high-risk clauses", "Find cases citing Section 12" |
| **hybrid** | Combined semantic + structured + external | "Compare indemnity terms with relevant case law" |

### Fallback Behavior

The router falls back to `rag` when:
- LLM response is not valid JSON
- Route name is not in the registry
- Confidence is below the configured threshold

---

## 7. Hybrid Retrieval Flow

Hybrid mode runs three retrieval paths in parallel, merges results via Reciprocal Rank Fusion (RRF), deduplicates, and synthesizes a unified answer.

```mermaid
flowchart TB
    Q["User Question"] --> PLAN["SqlQueryPlanner<br/>(LLM → SqlQueryPlan)"]

    PLAN --> PARALLEL

    subgraph PARALLEL["asyncio.gather — Parallel Retrieval"]
        direction LR
        V["Vector Path<br/>LegalDocumentRetriever<br/>→ pgvector search"]
        S["SQL Path<br/>SqlQueryExecutor<br/>→ ORM queries"]
        E["External Path<br/>ExternalLegalSearchService<br/>→ MCP servers"]
    end

    V --> VN["Vector Nodes"]
    S --> SN["SQL Nodes<br/>(score: 0.85)"]
    E --> EN["External Nodes<br/>(score: 0.80)"]

    VN --> MERGE
    SN --> MERGE
    EN --> MERGE

    subgraph MERGE["merge_retrieval_results()"]
        RRF["Reciprocal Rank Fusion<br/>(k = 60)"]
        DEDUP["Deduplication<br/>clause_id → doc+chunk → entity → hash"]
        RRF --> DEDUP
    end

    DEDUP --> CTX["LegalContextBuilder<br/>merged context"]
    CTX --> SYN["LegalResponseSynthesizer<br/>synthesize_from_context()"]
    SYN --> OUT["HybridPipelineResult<br/>answer + sources + merge_stats"]
```

### Merge Strategy

| Step | Detail |
|---|---|
| **RRF scoring** | `score = Σ 1/(k + rank)` across vector, SQL, and external ranked lists (k=60) |
| **Dedup keys** | `clause_id` → `document_id + chunk_index` → `source_type + entity_id` → content hash |
| **SQL node score** | Fixed at 0.85 |
| **External node score** | Fixed at 0.80 |
| **Max results** | `top_k × 2` after merge |

### MCP External Search

When `MCP_ENABLED=true`, the hybrid pipeline queries configured MCP servers (CourtListener, etc.) via stdio, SSE, or streamable HTTP transports. Failures degrade gracefully to empty external results.

---

## 8. Guardrails

Multi-layer safety enforcement for legal AI compliance, built on Guardrails AI with custom validators.

```mermaid
flowchart TB
    subgraph PreQuery["Pre-Query Validation"]
        PQ1["Query length check<br/>(MAX_QUERY_LENGTH = 2000)"]
        PQ2["Prompt injection detection<br/>(blocked patterns)"]
        PQ1 --> PQ2
        PQ2 -->|fail| REJECT["400 GuardrailViolationError"]
        PQ2 -->|pass| DISPATCH["QueryDispatcher"]
    end

    subgraph PostResponse["Post-Response Validation"]
        DISPATCH --> LLM_OUT["LLM Answer + Sources"]

        LLM_OUT --> GUARD["Guardrails AI Guard Pipeline"]

        subgraph Validators["Custom Validators (on_fail=refrain)"]
            V1["LegalAdviceDetector<br/>Block prescriptive advice<br/>without citations"]
            V2["CitationRequiredValidator<br/>Require citations for<br/>substantive legal content"]
            V3["UnsupportedClaimDetector<br/>Block unsupported<br/>factual claims"]
        end

        GUARD --> V1 --> V2 --> V3

        V3 -->|blocking failure| FB["get_fallback_response()<br/>Safe canned answer"]
        V3 -->|pass| DISC["Append legal disclaimer<br/>(DISCLAIMER_FOOTER)"]

        FB --> DISC
        DISC --> RESPONSE["QueryResponse to client"]
    end

    subgraph Handoff["Optional Human Handoff"]
        RESPONSE --> EVAL{"evaluate_escalation_triggers()"}
        EVAL -->|confidence < 0.70| ESC["Create HandoffEscalation"]
        EVAL -->|no citations| ESC
        EVAL -->|high-risk patterns| ESC
        EVAL -->|ok| DONE["Return to user"]
        ESC --> DONE
    end
```

### Guardrail Controls

| Control | Setting | Default |
|---|---|---|
| Master toggle | `ENABLE_GUARDRAILS` | `true` |
| Max query length | `MAX_QUERY_LENGTH` | 2000 |
| Handoff threshold | `HANDOFF_CONFIDENCE_THRESHOLD` | 0.70 |
| Sync validation | `GUARDRAILS_RUN_SYNC` | `true` |

### Escalation Triggers

1. Confidence score below 0.70
2. No supporting citations in the answer (unless "insufficient information" response)
3. High-risk legal advice patterns detected in the question

---

## 9. Deployment Diagram

```mermaid
flowchart TB
    subgraph DevMachine["Developer Machine"]
        Browser["Browser<br/>localhost:3000"]
        Vite["Vite Dev Server<br/>(React UI)"]
        Uvicorn["Uvicorn<br/>localhost:8000<br/>(FastAPI API)"]
        Venv["Python 3.12 venv"]
        EnvFile[".env"]
    end

    subgraph DockerCompose["Docker Compose (Production / Local)"]
        subgraph APIContainer["legaldoc-api"]
            FastAPI["FastAPI + Uvicorn<br/>:8000"]
            AppCode["app/ package"]
            UploadVol["/app/data/uploads<br/>(volume mount)"]
        end

        subgraph PGContainer["legaldoc-postgres"]
            PG["PostgreSQL 16<br/>+ pgvector extension"]
            PGData["postgres_data volume"]
        end
    end

    subgraph External["External Services"]
        OpenAI["OpenAI API"]
        Anthropic["Anthropic API"]
        MCPExt["MCP Legal DB Servers"]
        LangfuseCloud["Langfuse Cloud"]
    end

    Browser --> Vite
    Vite -->|proxy /query, /upload, etc.| Uvicorn
    Browser -->|docker mode| FastAPI

    Uvicorn --> Venv
    Uvicorn --> EnvFile
    Uvicorn --> PG

    FastAPI --> AppCode
    FastAPI --> UploadVol
    FastAPI --> PG
    FastAPI --> OpenAI
    FastAPI --> Anthropic
    FastAPI -.->|optional| MCPExt
    FastAPI -.->|optional| LangfuseCloud

    PG --> PGData
```

### Deployment Options

| Mode | Command | Components |
|---|---|---|
| **Local dev (API only)** | `uvicorn app.main:app --reload` | Python venv + local/Docker Postgres |
| **Local dev (full stack)** | `docker compose up -d postgres` + API + `npm run dev` | Postgres in Docker, API + UI on host |
| **Docker full stack** | `docker compose up --build` | API + Postgres containers |
| **Frontend production** | `npm run build` → serve `dist/` | Static build with `VITE_API_BASE_URL` |

### Container Details

| Service | Image / Build | Port | Volumes |
|---|---|---|---|
| `api` | `Dockerfile` (Python 3.12-slim) | 8000 | `./data/uploads:/app/data/uploads` |
| `postgres` | `pgvector/pgvector:pg16` | 5432 | `postgres_data`, `scripts/init-db.sql` |

### Database Migrations

```bash
alembic upgrade head
```

Runs migrations `001` (initial schema) through `005` (handoff escalations table).

---

## Related Documentation

- [README](../README.md) — Setup instructions and quick start
- [`.env.example`](../.env.example) — Full environment variable reference
- OpenAPI docs — `http://localhost:8000/docs` (when running)
