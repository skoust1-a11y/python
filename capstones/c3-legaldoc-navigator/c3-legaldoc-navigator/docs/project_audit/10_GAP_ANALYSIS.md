# Implementation Gap Analysis

Comparison of codebase vs `evaluation_report.md` and evaluation criteria, incorporating **new BM25 `/search` implementation**.

---

## Features Truly Missing

| Feature | Why Missing | Files to Change | Effort | Risk | Eval Impact |
|---------|-------------|-----------------|--------|------|-------------|
| **Server-side chat memory** | Never wired; schema-only `ChatHistory` | `schemas.py`, `query_service.py`, new `chat_service.py`, `query.py` | 3–5 days | Medium | **Critical** (criterion 4) |
| **Budget limit enforcement** | Cost only estimated/logged | New `budget_service.py`, middleware, config, optional ORM | 2–3 days | Medium | **High** (criterion 8) |
| **Load testing scripts** | Never created | `scripts/locustfile.py`, docs | 1 day | Low | **High** (criterion 9) |
| **Prometheus metrics** | Not started | `app/core/metrics.py`, `/metrics` route, `prometheus_client` dep | 2–3 days | Low | **High** (criterion 7) |
| **API authentication** | `User` model unused | middleware, auth deps, document scoping | 5+ days | High | Medium |
| **Redis response cache** | No cache layer | new cache module, query_service integration | 3–4 days | Medium | Medium (criterion 10) |
| **PostgreSQL FTS** | BM25 chosen over FTS | migrations, search service | 3–5 days | Medium | Low (BM25 covers sparse) |
| **Runtime SLO breakers** | Only CI gates | middleware timeouts, circuit breakers | 2–3 days | Medium | Medium (criterion 12) |
| **Rate limiting** | Not implemented | middleware (slowapi, etc.) | 1 day | Low | Medium (criterion 3) |

---

## Features Partially Implemented

| Feature | Current State | Gap | Files | Effort | Eval Impact |
|---------|---------------|-----|-------|--------|-------------|
| **BM25 / sparse retrieval** | Full on `/search` | Not in `/query` RAG/hybrid | `rag/pipeline.py`, `hybrid_pipeline.py`, `merge.py` | 2–4 days | **High** (criterion 13) |
| **Health checks** | Static `/health`; DB at startup | No runtime dependency probes | `app/api/health.py` | 0.5–1 day | Medium (criterion 3) |
| **Cost tracking** | Langfuse + benchmarks | No API response; no limits | `query_service.py`, middleware | 1–2 days | High (criterion 8) |
| **Observability/logging** | Stdlib logs + optional Langfuse | No structlog JSON, no metrics | `app/core/logging.py` | 0.5–1 day | High (criterion 7) |
| **OCR ingestion** | Code complete | Not in Docker; blocking upload | `Dockerfile`, optional async jobs | 1–2 days | Medium |
| **Structured DB tables** | Schema + SQL route | Upload doesn't populate Clause/Case/Statute | `document_service.py`, ingest | 3–5 days | Medium |
| **Handoff** | API + persistence | Frontend not wired | `frontend/` | 1–2 days | Low |
| **Connection pooling** | SQLAlchemy defaults | No tuned pool config | `session.py`, config | 0.5 day | Low |
| **Confidence scoring** | Multiple calculators | `compute_confidence` not wired to main path | `query_service.py` | 1 day | Low |

---

## Features Implemented but Overlooked by Evaluation Report

| Feature | Evidence | Evaluator Impact |
|---------|----------|------------------|
| **`POST /search` BM25 + semantic + RRF** | `app/search/pipeline.py`, `app/api/keyword_search.py` | Report says "no BM25" — **outdated** for search path |
| **Evidence validator + metric alignment** | `app/utils/evidence_validator.py`, `query_service._align_metrics_with_evidence` | Strengthens faithfulness story |
| **Analysis mode structured evaluation** | `AnalysisEvaluation`, `MetricsEvaluator` | Beyond basic metrics |
| **MCP external legal search** | `HybridPipeline._search_external` | Third hybrid source |
| **Context compression** | `ContextCompressionService` | Performance/scalability |
| **Keyword reranking on query path** | `rerank_chunks` in `ranking.py` | Partial lexical signal without BM25 |
| **CI benchmark gates** | `scripts/ci_benchmark_gate.py` | SLO criterion partially met |
| **Multi-provider LLM fallback** | `LLMService`, config | Resilience |
| **Frontend evidence UI** | `DirectEvidenceResults.tsx`, `SearchPage.tsx` | UX for `/search` |
| **BM25 index LRU cache** | `BM25SearchService._cache` | In-process caching exists |

---

## Features Implemented Differently Than Report Assumes

| Report Assumption | Actual Implementation |
|-----------------|----------------------|
| Single RAG retrieval path | Two paths: `/query` (LLM) and `/search` (evidence) |
| BM25 would be in RAG pipeline | BM25 is a **separate API** for direct evidence search |
| Health should check Qdrant | Qdrant checked at **startup** only when `VECTOR_BACKEND=qdrant` |
| Langfuse for prompts | Langfuse for **tracing only** |
| Memory via LlamaIndex buffers | Would need custom `ChatHistory` service — no LlamaIndex memory today |

---

## Architecture Weaknesses

| Weakness | Evidence | Severity |
|----------|----------|----------|
| LlamaIndex types in domain layer | `NodeWithScore` throughout `app/rag/` | Medium |
| Auto-commit in `get_db` | `session.py:39` — commits on read endpoints | Medium |
| Sync CPU work in async handlers | RRF, ranking, guardrails | Medium |
| Stateless query despite chat UI | `ChatPage` vs `QueryRequest` | High |
| Dual search architectures | Maintenance burden, eval confusion | Medium |
| Upload synchronous | OCR blocks HTTP | Medium |
| No auth on document endpoints | `DocumentService` lists all documents | High (production) |

---

## Potential Bugs

| Issue | Evidence | Likelihood |
|-------|----------|------------|
| Scanned PDF fails in Docker | No Tesseract in `Dockerfile` | High in container deploy |
| `fusion_search_service.py` staged but missing | Git status vs filesystem | Low — cleanup needed |
| False positive guardrail blocks | Regex `UnsupportedClaimDetector` | Medium |
| SQL route empty results | Case/Statute tables unpopulated | Medium without seed data |
| `get_db` commit on read-only errors | Commits even when no changes | Low |

---

## Technical Debt

### Critical
- No server-side conversational memory (eval criterion failure)
- No API authentication/authorization

### High
- BM25 not integrated into `/query` (eval report gap persists for main path)
- No budget limits
- No Prometheus/operational metrics
- Shallow health endpoint

### Medium
- IVFFlat vs HNSW indexes
- Sync guardrails blocking event loop
- Unused `ChatHistory` schema misleading
- Multiple overlapping confidence calculators
- `DisclaimerValidator` dead in guard pipeline

### Low
- Unused `structlog` dependency
- `API_V1_PREFIX` unused
- Empty `app/services/__init__.py`
- Legacy prompts in `templates.py`

---

## Related Documents

- [02_EVALUATION_REPORT_VERIFICATION.md](./02_EVALUATION_REPORT_VERIFICATION.md)
- [11_IMPLEMENTATION_ROADMAP.md](./11_IMPLEMENTATION_ROADMAP.md)
