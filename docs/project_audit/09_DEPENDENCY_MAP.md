# Dependency Map

---

## Query API Tree

```
POST /query (app/api/query.py)
├── QueryService (app/services/query_service.py)
│   ├── GuardrailValidator (app/guardrails/validator.py)
│   │   ├── create_legal_guard (app/guardrails/guard.py)
│   │   │   ├── LegalAdviceDetector
│   │   │   ├── CitationRequiredValidator
│   │   │   └── UnsupportedClaimDetector
│   │   └── get_fallback_response (app/guardrails/fallbacks.py)
│   ├── QueryDispatcher (app/services/query_dispatcher.py)
│   │   ├── Router (app/routing/router.py)
│   │   │   └── LLMService
│   │   ├── RAGEngine → RAGPipeline (app/rag/pipeline.py)
│   │   │   ├── LegalDocumentRetriever (app/rag/retriever.py)
│   │   │   │   └── SearchService → EmbeddingService
│   │   │   ├── rank_retrieval_results (app/rag/ranking.py)
│   │   │   ├── LegalContextBuilder (app/rag/context_builder.py)
│   │   │   ├── ContextCompressionService
│   │   │   ├── validate_retrieved_evidence (app/utils/evidence_validator.py)
│   │   │   └── LegalResponseSynthesizer (app/rag/synthesizer.py)
│   │   │       ├── LLMService
│   │   │       └── PromptManager (app/prompts/manager.py)
│   │   ├── HybridPipeline (app/rag/hybrid_pipeline.py) [sql/hybrid routes]
│   │   │   ├── SqlQueryPlanner → LLMService
│   │   │   ├── SqlQueryExecutor
│   │   │   ├── merge_retrieval_results (app/rag/merge.py)
│   │   │   │   └── reciprocal_rank_fusion (app/utils/rank_fusion.py)
│   │   │   ├── ExternalLegalSearchService (app/mcp/search.py) [hybrid only]
│   │   │   └── (same context/synth as RAG)
│   │   └── SqlQueryPlanner [sql route]
│   ├── estimate_cost (app/evaluation/cost.py) [if Langfuse]
│   ├── trace_query (app/evaluation/tracing.py) [if Langfuse]
│   └── answer_metrics / metrics_evaluator
└── build_query_response (app/utils/response_builder.py)
    └── format_document_citations (app/utils/citation_formatter.py)
```

---

## Search API Tree

```
POST /search (app/api/keyword_search.py)
├── DocumentSearchService (app/search/service.py)
│   └── retrieve_search_hits (app/search/pipeline.py)
│       ├── BM25SearchService (app/services/bm25_search_service.py)
│       │   ├── build_bm25_index (app/rag/bm25_retrieval.py)
│       │   └── tokenize_query (app/utils/bm25_tokenizer.py)
│       ├── SearchService → EmbeddingService
│       ├── filter_bm25_hits / filter_semantic_hits (app/search/relevance.py)
│       └── fuse_search_rankings (app/utils/search_fusion.py)
│           └── reciprocal_rank_fusion (app/utils/rank_fusion.py)
└── format_search_response (app/search/formatter.py)
```

---

## Upload API Tree

```
POST /upload (app/api/upload.py)
└── DocumentService (app/services/document_service.py)
    ├── validate_file_extension (app/utils/file_utils.py)
    ├── IngestionPipeline (app/ingestion/pipeline.py)
    │   ├── ParserFactory → PDFParser / DocxParser / TxtParser
    │   │   └── ScannedPDFParser → TesseractOCRService
    │   └── LegalDocumentChunker (app/ingestion/chunker.py)
    ├── DocumentStorageService (app/services/storage_service.py)
    └── VectorStoreService (app/services/vector_store_service.py)
        ├── EmbeddingService
        └── QdrantVectorService [if qdrant backend]
```

---

## Application Bootstrap

```
app/main.py
├── setup_logging (app/core/logging.py)
├── api_router (app/router/api_router.py)
├── RequestLoggingMiddleware (app/core/middleware.py)
├── lifespan
│   ├── verify_database_connection (app/database/session.py)
│   ├── get_langfuse_client (app/evaluation/tracing.py)
│   └── QdrantVectorService.ensure_collection [optional]
└── settings (app/core/config.py)
```

---

## Dependency Injection Graph

```
get_db (per-request AsyncSession)
├── get_query_service
│   ├── get_query_dispatcher
│   │   ├── get_query_router → get_llm_service
│   │   ├── get_rag_pipeline
│   │   ├── get_hybrid_pipeline
│   │   ├── get_sql_query_planner
│   │   ├── get_llm_service
│   │   ├── get_embedding_service
│   │   └── get_prompt_manager
│   └── get_guardrail_validator
├── get_document_service
├── get_document_search_service
│   ├── get_bm25_search_service
│   ├── get_embedding_service
│   └── SearchService (inline)
├── get_feedback_service
└── get_handoff_service
```

---

## External Service Dependencies

```
                    ┌─────────────┐
                    │   FastAPI   │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ PostgreSQL │  │ LLM APIs   │  │ Embeddings │
    │ + pgvector │  │ OpenAI etc │  │ OpenAI/Gem │
    └────────────┘  └────────────┘  └────────────┘
           │               │
           ▼               ▼
    ┌────────────┐  ┌────────────┐
    │ Qdrant     │  │ Langfuse   │ (optional)
    │ (optional) │  └────────────┘
    └────────────┘
           │
           ▼
    ┌────────────┐  ┌────────────┐
    │ S3/Supabase│  │ MCP Servers│ (optional)
    │ storage    │  └────────────┘
    └────────────┘
```

---

## Dead Code / Unused / Legacy

| Item | Evidence | Risk if removed |
|------|----------|-----------------|
| **`ChatHistory` ORM + table** | No reads/writes in services | Low — needed when memory implemented |
| **`DisclaimerValidator`** | Exported but not in `create_legal_guard` | Low — `_ensure_disclaimer` covers it |
| **`compute_confidence()` full multi-signal** | Defined in `confidence.py`; only `compute_confidence_score` used in pipelines | Low — alternative API |
| **`app/prompts/templates.py` legacy RAG templates** | `RAG_QA_PROMPT_TEMPLATE` may be unused; routing prompts still used | Low — verify grep before delete |
| **`Clause`/`Case`/`Statute` ORM at ingest** | Tables exist; upload doesn't populate | Medium — SQL route depends on seeded data |
| **`fusion_search_service.py`** | In git status as added; **file not on disk**; zero imports | None — phantom/staged file |
| **`User` model + auth** | No API auth middleware | Low until auth added |
| **`API_V1_PREFIX` config** | Defined, never applied to router | Low — documentation confusion |
| **`app/services/__init__.py`** | Empty `__all__` | None |

---

## Duplicate Implementations

| Area | Instances | Notes |
|------|-----------|-------|
| **Search paths** | `/query` dense vs `/search` BM25+dense | Intentional separation — candidate for unification |
| **Fusion utilities** | `merge_retrieval_results` vs `fuse_search_rankings` | Both use same `reciprocal_rank_fusion` — acceptable |
| **Confidence scoring** | `compute_confidence_score`, `compute_confidence`, `compute_confidence_from_evidence`, `MetricsEvaluator` | Multiple overlapping calculators |
| **Disclaimer enforcement** | `DisclaimerValidator` + `_ensure_disclaimer` | Redundant paths |

---

## Legacy Implementations

| Item | Status |
|------|--------|
| IVFFlat pgvector indexes | Functional but older than HNSW recommendation |
| `templates.py` monolithic prompts | Superseded by per-mode prompt modules for synthesis |
| Manual DI defaults (`or ConcreteClass()`) | Pre-FastAPI-Depends pattern still in constructors |

---

## Critical Files (Modify with Care)

| File | Why |
|------|-----|
| `app/core/config.py` | Import-time validators; misconfig fails startup |
| `app/database/session.py` | Session lifecycle affects all DB operations |
| `app/services/query_service.py` | Main user-facing Q&A path |
| `app/rag/merge.py` | RRF fusion correctness |
| `app/guardrails/validator.py` | Safety boundary |
| `app/models/schemas.py` | API contract / frontend compatibility |
| `app/dependencies.py` | DI graph for all endpoints |
| `alembic/versions/*` | Schema migrations irreversible without care |

---

## Utility Files (High Reuse)

| File | Used By |
|------|---------|
| `app/utils/rank_fusion.py` | merge, search_fusion |
| `app/utils/evidence_validator.py` | query_service, pipelines |
| `app/utils/response_builder.py` | query API |
| `app/utils/citation_formatter.py` | response_builder, frontend types |
| `app/utils/bm25_tokenizer.py` | bm25_search_service, search/relevance |
| `app/utils/answer_metrics.py` | query_service |
| `app/utils/tokens.py` | cost, chunker, compression |

---

## Related Documents

- [08_FILE_REFERENCE_GUIDE.md](./08_FILE_REFERENCE_GUIDE.md)
- [10_GAP_ANALYSIS.md](./10_GAP_ANALYSIS.md)
