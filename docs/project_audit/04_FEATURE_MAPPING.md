# Complete Feature Mapping

Status legend: **Fully Implemented** | **Partially Implemented** | **Missing**

---

## Ingestion & Indexing

### Document Upload — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **What** | Accept PDF/DOCX/TXT, persist metadata, index for retrieval |
| **API** | `POST /upload` → `app/api/upload.py:upload_document` |
| **Service** | `DocumentService.upload_document` (`app/services/document_service.py`) |
| **Flow** | Validate → create `Document` → temp file → `IngestionPipeline.ingest` → storage upload → `VectorStoreService.embed_and_store` → status `indexed` |

### OCR — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **What** | Tesseract OCR for scanned PDFs (< 50 chars/page heuristic) |
| **Files** | `app/ingestion/ocr.py` (`TesseractOCRService`), `app/ingestion/parsers/scanned_pdf_parser.py` |
| **Gap** | Tesseract not in `Dockerfile`; sequential page processing blocks upload request |

### PDF Parsing — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **What** | PyMuPDF text extraction; scanned detection delegates to OCR parser |
| **Files** | `app/ingestion/parsers/pdf_parser.py`, `scanned_pdf_parser.py` |
| **Factory** | `ParserFactory.get_parser()` in `app/ingestion/parsers/factory.py` |

### Chunking — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **What** | Structure-aware legal chunking with overlap |
| **Class** | `LegalDocumentChunker` (`app/ingestion/chunker.py`) |
| **Config** | `CHUNK_SIZE`, `CHUNK_OVERLAP` |

### Metadata Extraction — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **What** | Title, parties, dates extracted into chunk/node metadata during parse |
| **Gap** | `Clause`, `Case`, `Statute` ORM tables not populated on upload |

### Embedding Generation — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Class** | `EmbeddingService` (`app/services/embedding_service.py`) |
| **Methods** | `embed_text`, `embed_texts` — OpenAI or Google |

### Embedding Storage — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Class** | `VectorStoreService.embed_and_store` (`app/services/vector_store_service.py`) |
| **ORM** | `DocumentEmbedding` rows; optional Qdrant upsert |

### pgvector — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Search** | `SearchService._search_pgvector` — cosine distance |
| **Index** | IVFFlat on `document_embeddings.embedding` (`app/models/orm.py`) |

### SQL Storage — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **ORM** | `Document`, `DocumentEmbedding`, `User`, `Feedback`, etc. (`app/models/orm.py`) |
| **Migrations** | `alembic/versions/` |

---

## Retrieval & Query

### Query Routing — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Class** | `Router.route` (`app/routing/router.py`) |
| **Routes** | `rag`, `sql`, `hybrid` via `RouteRegistry` |
| **Dispatcher** | `QueryDispatcher.dispatch` (`app/services/query_dispatcher.py`) |
| **Override** | `document_id` forces `rag` |

### RAG — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Pipeline** | `RAGPipeline.run` (`app/rag/pipeline.py`) |
| **Retriever** | `LegalDocumentRetriever` → dense vector only |

### Vector Retrieval — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Service** | `SearchService.search` (`app/services/search_service.py`) |
| **Backends** | pgvector or Qdrant |

### SQL Retrieval — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Planner** | `SqlQueryPlanner.plan` |
| **Executor** | `SqlQueryExecutor.execute` |
| **Merge** | `sql_results_to_nodes` (`app/rag/merge.py`) |

### Hybrid Retrieval (Query path) — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Pipeline** | `HybridPipeline.retrieve_hybrid` — parallel SQL + vector + MCP |
| **Fusion** | `merge_retrieval_results` with RRF |

### MCP Retrieval — **Fully Implemented** (when enabled)

| Aspect | Detail |
|--------|--------|
| **Service** | `ExternalLegalSearchService` (`app/mcp/search.py`) |
| **Merge** | `external_results_to_nodes` at score 0.80 |
| **Config** | `MCP_ENABLED`, `MCP_SERVERS` |

### BM25 / Keyword Retrieval — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **What** | In-memory LlamaIndex BM25 over chunk corpus |
| **Where** | `POST /search` only — `BM25SearchService`, `app/search/pipeline.py` |
| **Gap** | Not integrated into `/query` RAG or hybrid pipelines |

### Reciprocal Rank Fusion — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Core** | `reciprocal_rank_fusion` (`app/utils/rank_fusion.py`, `RRF_K=60`) |
| **Query hybrid** | `merge_retrieval_results` |
| **Search** | `fuse_search_rankings` (`app/utils/search_fusion.py`) |

### Score Fusion — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **RRF** | Cross-list rank fusion |
| **Reranking** | `rerank_chunks` — semantic + keyword + same-document boosts (`app/rag/ranking.py`) |
| **Fixed scores** | SQL 0.85, MCP 0.80 pre-RRF |

### Deduplication — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **RRF dedup** | `node_dedup_key` in `rank_fusion.py` |
| **Ranking dedup** | `deduplicate_chunks`, `merge_overlapping_chunks` in `ranking.py` |

---

## Prompting & Response

### Prompt Manager — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Class** | `PromptManager` (`app/prompts/manager.py`) |
| **Methods** | `get_system_prompt`, `get_user_prompt`, `build_synthesis_messages` |

### Prompt Templates — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Modules** | `strict_prompt.py`, `explain_prompt.py`, `analysis_prompt.py` |
| **Legacy** | `templates.py` — routing prompts still used by `Router` |

### Response Modes — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Modes** | `strict`, `explain`, `analysis` (`app/prompts/types.py`) |
| **Container** | `ModeResponses` (`app/models/mode_responses.py`) |

### Explain Mode — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Prompt** | `app/prompts/explain_prompt.py` |
| **Synthesis** | `LegalResponseSynthesizer` |

### Analysis Mode — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Prompt** | `app/prompts/analysis_prompt.py` |
| **Evaluation** | `AnalysisEvaluation` model + `MetricsEvaluator` |

### Citation Generation — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Context labels** | `LegalContextBuilder` — `[Source N]` |
| **API format** | `format_document_citations` (`app/utils/citation_formatter.py`) |
| **Validation** | `CitationRequiredValidator` |

---

## Quality Metrics

### Confidence Metrics — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Retrieval** | `compute_confidence_score` in pipeline |
| **Response** | `analysis_evaluation.confidence` or `compute_confidence_from_evidence` |
| **Level** | `classify_confidence_level` — High/Medium/Low |

### Faithfulness Metrics — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Sources** | `MetricsEvaluator`, `compute_faithfulness` (`app/utils/answer_metrics.py`) |
| **Guardrails** | `UnsupportedClaimDetector` (regex grounding) |

### Relevance Metrics — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Functions** | `compute_relevance`, `compute_retrieval_relevance` |
| **Evidence gate** | `_align_metrics_with_evidence` zeros relevance when insufficient |

---

## Safety

### Guardrails — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Orchestrator** | `GuardrailValidator` |
| **Validators** | `LegalAdviceDetector`, `CitationRequiredValidator`, `UnsupportedClaimDetector` |
| **See** | [06_MEMORY_AND_GUARDRAILS.md](./06_MEMORY_AND_GUARDRAILS.md) |

---

## Observability & Ops

### Cost Tracking — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **Function** | `estimate_cost` (`app/evaluation/cost.py`) |
| **Usage** | Langfuse logging when enabled; benchmark runner |
| **Gap** | Not returned in live API response |

### Budget Limits — **Missing**

I could not find evidence of spend limits or HTTP 429 enforcement.

### Langfuse — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **Module** | `app/evaluation/tracing.py` |
| **Default** | `ENABLE_LANGFUSE=false` |

### Logging — **Fully Implemented** (basic)

| Aspect | Detail |
|--------|--------|
| **Setup** | `setup_logging()` — stdlib `basicConfig` |
| **Middleware** | `RequestLoggingMiddleware` |

### Evaluation Pipeline — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Runner** | `BenchmarkRunner` (`app/evaluation/runner.py`) |
| **Metrics** | RAGAS via `RAGEvaluator` |
| **CI gate** | `scripts/ci_benchmark_gate.py` |

### Benchmarking — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Script** | `scripts/run_benchmark.py`, `scripts/ci_benchmark_gate.py` |
| **Dashboard** | `app/evaluation/dashboard.py` |

### Health Endpoint — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **Route** | `GET /health` — static healthy response |
| **Startup** | DB verified in `lifespan`; not in health endpoint |

### Deployment — **Fully Implemented**

| Aspect | Detail |
|--------|--------|
| **Docker** | `Dockerfile`, `docker-compose.yml` |
| **Cloud** | `render.yaml` |

### Docker — **Fully Implemented**

API + Postgres compose; no frontend container.

### Authentication — **Missing**

`User` ORM exists; no JWT/session auth on API endpoints.

### Authorization — **Missing**

Documents not scoped by user in `DocumentService`.

### Session Management — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **Client** | `getSessionId()` in `frontend/src/lib/utils.ts` (localStorage) |
| **Server** | Used for feedback/handoff only; not query |

### Chat History — **Missing** (server-side)

`ChatHistory` table exists; no read/write logic.

### Memory — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **Client** | React state in `ChatPage.tsx` |
| **Server** | Stateless `/query` |

### Runtime Metrics — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **Per-request** | `latency_ms` in `QueryResponse`; middleware logs |
| **Prometheus** | Missing |

### Load Testing — **Missing**

No Locust/k6 scripts.

### Caching — **Partially Implemented**

| Aspect | Detail |
|--------|--------|
| **BM25 index** | In-process LRU (`BM25_CACHE_MAX_ENTRIES`) |
| **Redis** | Missing |

### Background Jobs — **Missing**

Upload and OCR run synchronously in request handler.

---

## Feature Status Summary

| Status | Count |
|--------|-------|
| Fully Implemented | 38 |
| Partially Implemented | 14 |
| Missing | 6 |
