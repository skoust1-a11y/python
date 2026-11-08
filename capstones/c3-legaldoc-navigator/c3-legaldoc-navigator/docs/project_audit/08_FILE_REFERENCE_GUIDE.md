# File Reference Guide

Quick navigation to where important logic lives.

---

## Core Application

| Feature | Purpose | Files | Classes | Functions | Dependencies |
|---------|---------|-------|---------|-----------|--------------|
| App entry | FastAPI bootstrap | `app/main.py` | — | `create_app`, `lifespan` | config, router, middleware |
| API routing | Mount all endpoints | `app/router/api_router.py` | — | `api_router` | all `app/api/*` routers |
| Configuration | Env settings | `app/core/config.py` | `Settings` | `get_settings` | pydantic-settings |
| DI | Service wiring | `app/dependencies.py` | — | `get_*` factories | all services |
| DB session | Async PostgreSQL | `app/database/session.py` | `Base` | `get_db`, `verify_database_connection` | SQLAlchemy, asyncpg |
| Exceptions | App errors | `app/core/exceptions.py` | `AppException`, `GuardrailViolationError` | — | — |
| Middleware | Request logging | `app/core/middleware.py` | `RequestLoggingMiddleware` | `dispatch` | — |

---

## API Endpoints

| Feature | Purpose | Files | Handler | Service |
|---------|---------|-------|---------|---------|
| Health | Liveness | `app/api/health.py` | `health_check` | — |
| Upload | Document ingest | `app/api/upload.py` | `upload_document` | `DocumentService` |
| Query | RAG Q&A | `app/api/query.py` | `query_documents` | `QueryService` |
| Search | BM25+semantic | `app/api/keyword_search.py` | `keyword_search` | `DocumentSearchService` |
| Documents | List/get | `app/api/documents.py` | `list_documents`, `get_document` | `DocumentService` |
| Feedback | User ratings | `app/api/feedback.py` | `submit_feedback` | `FeedbackService` |
| Handoff | Human escalation | `app/api/handoff.py` | `create_handoff` | `HandoffService` |

**Schemas:** `app/models/schemas.py`

---

## Query Pipeline

| Feature | Purpose | Files | Classes | Key Functions | Flow |
|---------|---------|-------|---------|---------------|------|
| Query orchestration | Business entry | `app/services/query_service.py` | `QueryService` | `ask`, `_align_metrics_with_evidence` | guardrails → dispatch → metrics |
| Routing dispatch | Pipeline selection | `app/services/query_dispatcher.py` | `QueryDispatcher`, `QueryResult` | `dispatch`, `_run_rag/sql/hybrid` | router → pipeline |
| Query classifier | LLM route | `app/routing/router.py` | `Router` | `route`, `_parse_response` | LLM JSON → rag/sql/hybrid |
| RAG pipeline | Dense retrieve+synth | `app/rag/pipeline.py` | `RAGPipeline` | `retrieve`, `run` | vector → rank → context → LLM |
| Hybrid pipeline | Multi-source | `app/rag/hybrid_pipeline.py` | `HybridPipeline` | `retrieve_hybrid`, `run_hybrid` | parallel SQL+vector+MCP |
| Synthesis | LLM answers | `app/rag/synthesizer.py` | `LegalResponseSynthesizer` | `synthesize_all_modes_from_context` | 3 modes + analysis eval |
| Response build | API formatting | `app/utils/response_builder.py` | — | `build_query_response` | citations, follow-ups |

---

## Retrieval

| Feature | Purpose | Files | Classes | Key Functions |
|---------|---------|-------|---------|---------------|
| Dense search | Vector similarity | `app/services/search_service.py` | `SearchService` | `search`, `_search_pgvector` |
| BM25 search | Sparse keyword | `app/services/bm25_search_service.py` | `BM25SearchService` | `search`, `_get_index` |
| BM25 index | LlamaIndex BM25 | `app/rag/bm25_retrieval.py` | — | `build_bm25_index`, `search_bm25` |
| Search pipeline | /search fusion | `app/search/pipeline.py` | — | `retrieve_search_hits` |
| Search service | /search orchestration | `app/search/service.py` | `DocumentSearchService` | `search` |
| Search format | API response | `app/search/formatter.py` | — | `format_search_response` |
| Search relevance | Hit filtering | `app/search/relevance.py` | — | `filter_bm25_hits`, `is_search_relevant` |
| Retriever | LlamaIndex wrapper | `app/rag/retriever.py` | `LegalDocumentRetriever` | `_aretrieve` |
| Merge | RRF fusion | `app/rag/merge.py` | `MergeStats` | `merge_retrieval_results`, `sql_results_to_nodes` |
| Rank fusion | RRF core | `app/utils/rank_fusion.py` | — | `reciprocal_rank_fusion`, `node_dedup_key` |
| Search fusion | BM25+semantic RRF | `app/utils/search_fusion.py` | — | `fuse_search_rankings` |
| Ranking | Dedup/rerank | `app/rag/ranking.py` | `RankingStats` | `rank_retrieval_results`, `rerank_chunks` |
| Context | Prompt blocks | `app/rag/context_builder.py` | `LegalContextBuilder` | `build` |
| Confidence | Scoring | `app/rag/confidence.py` | `ConfidenceResult` | `compute_confidence_score`, `compute_confidence` |
| SQL planner | LLM → plan | `app/services/sql_query_planner.py` | `SqlQueryPlanner` | `plan` |
| SQL executor | DB retrieval | `app/services/sql_query_executor.py` | `SqlQueryExecutor` | `execute` |
| MCP search | External DBs | `app/mcp/search.py` | `ExternalLegalSearchService` | `search` |

---

## Ingestion

| Feature | Purpose | Files | Classes | Key Functions |
|---------|---------|-------|---------|---------------|
| Upload service | Full ingest flow | `app/services/document_service.py` | `DocumentService` | `upload_document` |
| Ingestion | Parse+chunk | `app/ingestion/pipeline.py` | `IngestionPipeline` | `ingest`, `parse_document` |
| PDF parser | Text/scanned | `app/ingestion/parsers/pdf_parser.py` | `PDFParser` | `parse` |
| OCR | Tesseract | `app/ingestion/ocr.py` | `TesseractOCRService` | `extract_text_from_page_image` |
| Chunker | Legal chunks | `app/ingestion/chunker.py` | `LegalDocumentChunker` | `chunk_to_nodes` |
| Vector store | Embed+persist | `app/services/vector_store_service.py` | `VectorStoreService` | `embed_and_store` |
| Embeddings | API calls | `app/services/embedding_service.py` | `EmbeddingService` | `embed_texts` |
| Storage | File backends | `app/services/storage_service.py` | `DocumentStorageService` | `upload_document` |

---

## Guardrails & Safety

| Feature | Purpose | Files | Classes | Key Functions |
|---------|---------|-------|---------|---------------|
| Orchestrator | Pre/post validation | `app/guardrails/validator.py` | `GuardrailValidator` | `validate_query`, `validate_response_detailed` |
| Guard pipeline | Validator composition | `app/guardrails/guard.py` | — | `create_legal_guard` |
| Legal advice | Block advice | `app/guardrails/validators/legal_advice.py` | `LegalAdviceDetector` | `_validate` |
| Citations | Require cites | `app/guardrails/validators/citation_required.py` | `CitationRequiredValidator` | `_validate` |
| Unsupported claims | Fact grounding | `app/guardrails/validators/unsupported_claims.py` | `UnsupportedClaimDetector` | `_validate` |
| Fallbacks | Safe responses | `app/guardrails/fallbacks.py` | — | `get_fallback_response` |
| Evidence | Retrieval quality | `app/utils/evidence_validator.py` | — | `validate_retrieved_evidence` |

---

## Prompts

| Feature | Purpose | Files | Classes | Key Functions |
|---------|---------|-------|---------|---------------|
| Manager | Mode selection | `app/prompts/manager.py` | `PromptManager` | `build_synthesis_messages` |
| Strict mode | Citations required | `app/prompts/strict_prompt.py` | — | `SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE` |
| Explain mode | Accessible answers | `app/prompts/explain_prompt.py` | — | constants |
| Analysis mode | Evaluation | `app/prompts/analysis_prompt.py` | — | constants |
| Shared | Common strings | `app/prompts/shared.py` | — | `EVIDENCE_NONE_FOUND_RESPONSE` |
| Routing prompts | Classifier | `app/prompts/templates.py` | — | `QUERY_ROUTING_SYSTEM_PROMPT` |
| Types | Mode enum | `app/prompts/types.py` | — | `RESPONSE_MODES` |

---

## Observability & Evaluation

| Feature | Purpose | Files | Classes | Key Functions |
|---------|---------|-------|---------|---------------|
| Langfuse | Tracing | `app/evaluation/tracing.py` | — | `trace_query`, `log_query_result` |
| Cost | Token USD | `app/evaluation/cost.py` | `CostBreakdown` | `estimate_cost` |
| Benchmark | Offline eval | `app/evaluation/runner.py` | `BenchmarkRunner` | `run_benchmark` |
| RAGAS | Quality metrics | `app/evaluation/metrics.py` | `RAGEvaluator` | `compute_ragas_scores` |
| CI gate | Threshold checks | `scripts/ci_benchmark_gate.py` | — | `_run` |
| Answer metrics | Runtime scores | `app/utils/answer_metrics.py` | — | `compute_faithfulness`, `compute_relevance` |
| Metrics eval | Deterministic | `app/utils/metrics_evaluator.py` | `MetricsEvaluator` | `evaluate` |
| Analysis parser | Parse LLM eval | `app/utils/analysis_parser.py` | — | parse functions |

---

## Database Models

| Model | Table | File | Purpose |
|-------|-------|------|---------|
| `User` | users | `app/models/orm.py` | Auth user (unused in API) |
| `Document` | documents | same | Uploaded files |
| `DocumentEmbedding` | document_embeddings | same | Chunks + vectors |
| `Clause` | clauses | same | Structured clauses (schema only at ingest) |
| `Case` | cases | same | Legal cases + embedding |
| `Statute` | statutes | same | Statutes + embedding |
| `Citation` | citations | same | Entity links |
| `Feedback` | feedback | same | User ratings |
| `HandoffEscalation` | handoff_escalations | same | Escalations |
| `ChatHistory` | chat_history | same | **Unused** chat turns |

---

## Tests (Key Coverage)

| Area | File |
|------|------|
| BM25 | `tests/test_bm25_search.py` |
| Search fusion | `tests/test_search_fusion.py`, `tests/test_search_relevance.py` |
| Merge/RRF | `tests/test_merge.py`, `tests/test_ranking.py` |
| Guardrails | `tests/test_guardrails.py` |
| Metrics | `tests/test_answer_metrics.py`, `tests/test_metrics_evaluator.py` |
| Pipeline evidence | `tests/test_pipeline_evidence.py` |
| Query response | `tests/test_query_response.py` |

---

## Related Documents

- [09_DEPENDENCY_MAP.md](./09_DEPENDENCY_MAP.md)
- [03_ARCHITECTURE_ANALYSIS.md](./03_ARCHITECTURE_ANALYSIS.md)
