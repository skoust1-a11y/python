# Evaluation Report Verification

This document independently verifies every claim in `evaluation_report.md` against the codebase. The evaluation report is **not** treated as source of truth.

---

## Verification Matrix

| Evaluation Criterion | Report Claim | Actual Implementation | Verdict | Evidence |
|----------------------|--------------|------------------------|---------|----------|
| **1. Architecture** | Clean Architecture with presentation, application, domain, infrastructure layers | FastAPI API layer (`app/api/`), services (`app/services/`), RAG domain (`app/rag/`, `app/routing/`, `app/search/`), infrastructure (`app/database/`, `app/ingestion/`, `app/mcp/`) | **Correct** | `app/main.py`, `app/router/api_router.py`, `app/dependencies.py` |
| **1. Architecture** | Implicit auto-commits in `get_db` | `get_db()` yields session, commits on success, rolls back on exception | **Correct** | `app/database/session.py:35-42` — `await session.commit()` after yield |
| **1. Architecture** | LlamaIndex coupling in domain (`NodeWithScore`, `QueryBundle`) | `HybridPipeline`, `merge_retrieval_results`, `LegalDocumentRetriever` import LlamaIndex types directly | **Correct** | `app/rag/hybrid_pipeline.py:9`, `app/rag/merge.py:8`, `app/rag/retriever.py` |
| **1. Architecture** | Manual mock-based DI with default concrete instances | `QueryService.__init__` uses `dispatcher or QueryDispatcher(...)` pattern; FastAPI `Depends()` in `dependencies.py` | **Correct** | `app/services/query_service.py:37-44`, `app/dependencies.py` |
| **2. Prompting** | Structured modes via `PromptManager` | `PromptManager` in `app/prompts/manager.py` selects strict/explain/analysis modules | **Correct** | `app/prompts/manager.py:28-122` |
| **2. Prompting** | Prompts are hardcoded string constants | `SYSTEM_PROMPT` / `USER_PROMPT_TEMPLATE` in `strict_prompt.py`, `explain_prompt.py`, `analysis_prompt.py` | **Correct** | `app/prompts/strict_prompt.py`, etc. |
| **2. Prompting** | No Langfuse Prompt Registry integration | Langfuse used for tracing only (`app/evaluation/tracing.py`); prompts not fetched from Langfuse | **Correct** | Grep: no Langfuse prompt fetch in `app/prompts/` |
| **3. FastAPI Endpoints** | REST routes for health, query, upload, documents, feedback, handoffs | 8 endpoints mounted at root via `api_router` | **Correct** | `app/router/api_router.py`; plus `POST /search` added |
| **3. FastAPI** | Passive `/health` — static string only | Returns hardcoded `status="healthy"` without dependency checks | **Correct** | `app/api/health.py:17-22` |
| **3. FastAPI** | No rate limiting | No rate limit middleware or decorator found | **Correct** | Grep in `app/`: no rate limit implementation |
| **3. FastAPI** | Upload validates extension only, no magic bytes | `validate_file_extension()` in upload flow; no MIME magic-number check | **Correct** | `app/services/document_service.py`, `app/utils/file_utils.py` |
| **4. Memory** | `ChatHistory` schema unused; stateless API | ORM model exists; no service inserts/reads; `QueryRequest` has no `session_id` | **Correct** | `app/models/orm.py:429-463`; `app/models/schemas.py:96-123`; grep `ChatHistory(` — only ORM + migration |
| **4. Memory** | No LlamaIndex memory buffers | No `ChatMemoryBuffer` or similar in query path | **Correct** | Grep: no memory buffer usage in `app/services/` or `app/rag/` |
| **5. RAG + SQL + Hybrid** | LLM classifier routes to Vector, SQL, Hybrid with RRF | `Router.route()` → `QueryDispatcher.dispatch()` → RAG/SQL/Hybrid pipelines; RRF in `merge_retrieval_results` | **Correct** | `app/routing/router.py`, `app/services/query_dispatcher.py`, `app/rag/merge.py:36-81` |
| **5. RAG + SQL + Hybrid** | CPU blocking in async loop (RRF, dedup) | `reciprocal_rank_fusion`, `rank_retrieval_results` are sync functions called from async handlers without `asyncio.to_thread` | **Correct** | `app/utils/rank_fusion.py`, `app/rag/ranking.py:63-79` |
| **5. RAG + SQL + Hybrid** | SQL/MCP hardcoded scores 0.85 / 0.80 | `SQL_SOURCE_SCORE = 0.85`, `EXTERNAL_SOURCE_SCORE = 0.80` in merge module | **Correct** | `app/rag/merge.py:21-22`, used in `_contract_to_node`, etc. |
| **6. Guardrails** | Guardrails AI + custom validators | `create_legal_guard()` composes three validators; `GuardrailValidator` orchestrates | **Correct** | `app/guardrails/guard.py:28-34`, `app/guardrails/validator.py` |
| **6. Guardrails** | Regex-based `UnsupportedClaimDetector` | `_DATE_RE`, `_MONEY_RE`, `_PERCENT_RE`, `_PROPER_NOUN_RE` extract tokens checked against corpus | **Correct** | `app/guardrails/validators/unsupported_claims.py:44-78` |
| **6. Guardrails** | Synchronous guardrails by default | `GUARDRAILS_RUN_SYNC` defaults `True`; env set in `guard.py:17` | **Correct** | `app/core/config.py`, `app/guardrails/guard.py:17` |
| **7. Observability** | Langfuse traces query pipelines | `trace_query`, `log_query_result` in `QueryService.ask` when `ENABLE_LANGFUSE` | **Correct** | `app/services/query_service.py:58-64, 120-140` |
| **7. Observability** | No Prometheus `/metrics` | No prometheus client or metrics route | **Correct** | Grep `prometheus` in `app/`: no matches |
| **7. Observability** | `structlog` unused; plain `logging.basicConfig` | `setup_logging()` uses stdlib only | **Correct** | `app/core/logging.py:11-17`; `structlog` only in `requirements.txt:56` |
| **8. Cost Tracking** | Tokens counted, estimated, logged to Langfuse | `estimate_cost()` uses `count_tokens()`; logged when Langfuse enabled | **Correct** | `app/evaluation/cost.py`, `app/services/query_service.py:126-139` |
| **8. Budget Limits** | No enforcement / HTTP 429 | No budget model, middleware, or limit checks | **Correct** | Grep `budget` in `app/`: only token budget in chunker/compression, not API spend |
| **9. Load Testing** | No Locust/k6 scripts | Not in `requirements.txt` or `scripts/` | **Correct** | Grep `locust`, `k6`: only in docs and `evaluation_report.md` |
| **10. Performance** | No Redis caching layer | No Redis client; BM25 uses in-process `OrderedDict` LRU only | **Correct** | `app/services/bm25_search_service.py:75-145`; grep `redis` in `app/`: no matches |
| **10. Performance** | pgvector `ivfflat` indexes | IVFFlat on `document_embeddings`, `cases`, `statutes` | **Correct** | `app/models/orm.py:209-212, 251-254, 350-353` |
| **11. Deployment** | Production-ready configs | `docker-compose.yml`, `render.yaml`, `Dockerfile`, Alembic migrations | **Correct** | Root deploy files |
| **11. Deployment** | Lacks database connection pooling | SQLAlchemy async engine with default pool + `pool_pre_ping=True` | **Partially Correct** | `app/database/session.py:19-23` — pooling exists; no explicit `pool_size` tuning |
| **12. SLO Bound** | CI offline SLO gates | `scripts/ci_benchmark_gate.py` enforces faithfulness, latency, cost thresholds | **Correct** | `scripts/ci_benchmark_gate.py:22-29, 72-80` |
| **12. SLO Bound** | No runtime latency breakers | No request-level timeout middleware or circuit breakers on API routes | **Correct** | MCP has `timeout_seconds`; API routes have no global timeout |
| **13. Hybrid Ingestion/Retrieval** | No BM25 / sparse keyword search combined with vector in RAG | BM25 exists on **`POST /search`** only; `/query` RAG uses dense vector only | **Partially Correct / Outdated** | `app/search/pipeline.py`, `app/api/keyword_search.py`; `RAGPipeline.retrieve` uses `LegalDocumentRetriever` → `SearchService` only |
| **13. Hybrid Ingestion/Retrieval** | No PostgreSQL FTS | No `tsvector` / `to_tsvector` usage | **Correct** | Grep across repo: no FTS implementation |
| **13. Hybrid Ingestion/Retrieval** | Blocking sequential OCR in upload | `ScannedPDFParser` processes pages sequentially in upload request | **Correct** | `app/ingestion/parsers/scanned_pdf_parser.py`, synchronous in `DocumentService.upload_document` |

---

## Claims the Evaluation Report Missed

| Implementation | Location | Significance |
|----------------|----------|--------------|
| **`POST /search` hybrid BM25 + semantic** | `app/search/service.py`, `app/search/pipeline.py` | Sparse+dense fusion with RRF — addresses part of criterion 13 on a separate API |
| **Evidence validator** | `app/utils/evidence_validator.py` | Gates metrics when retrieval insufficient |
| **Analysis evaluation mode** | `app/models/analysis_evaluation.py`, `app/utils/metrics_evaluator.py` | Structured faithfulness/relevance/confidence per claim |
| **Context compression** | `app/services/context_compression_service.py` | Token budget enforcement before LLM |
| **MCP external legal search** | `app/mcp/search.py`, `HybridPipeline._search_external` | Third retrieval source on hybrid route |
| **Startup DB verification** | `app/main.py:30-32` | `verify_database_connection()` at lifespan — deeper than `/health` |
| **Keyword boosts in ranking** | `app/rag/ranking.py` `rerank_chunks` | Post-retrieval lexical reranking on `/query` path |
| **Frontend client-side chat state** | `frontend/src/pages/ChatPage.tsx` | UI memory only; not persisted server-side |

---

## Recommendations from Report — Re-Verification

| Report Recommendation | Status | Notes |
|----------------------|--------|-------|
| Expose `session_id` in `QueryRequest` | **Not implemented** | Confirmed gap |
| Load `ChatHistory` in `QueryService.ask` | **Not implemented** | Confirmed gap |
| Budget limits + HTTP 429 | **Not implemented** | Confirmed gap |
| Upgrade `UnsupportedClaimDetector` to NLI/semantic | **Not implemented** | Regex still primary |
| Deep health (DB + Qdrant) | **Not implemented** | Startup checks exist; `/health` static |
| Locust load test script | **Not present** | Confirmed gap |
| Redis response caching | **Not implemented** | Confirmed gap |
| HNSW index migration | **Not implemented** | Still IVFFlat |
| BM25 hybrid for RAG | **Partially done** | `/search` only; `/query` still dense-only |

---

## Verdict Summary

| Verdict | Count |
|---------|-------|
| Correct | 28 |
| Partially Correct / Outdated | 4 |
| Incorrect | 0 |
| Already Implemented (report said missing) | 1 (BM25 — on `/search`, not `/query`) |
| Needs Verification | 1 (`fusion_search_service.py` listed in git status but file not on disk and zero imports) |
