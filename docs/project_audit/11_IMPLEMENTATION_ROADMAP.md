# Implementation Roadmap

Prioritized by **evaluation ROI** = expected marks ÷ implementation effort.

---

## A. Critical for Evaluation Marks

High weight, low–medium effort, safe to implement.

### A1. Server-Side Conversational Memory

| Field | Value |
|-------|-------|
| **Reason** | Evaluation criterion 4 marked "Critical Failure"; `ChatHistory` exists but unused |
| **Criterion** | Memory Management |
| **Files** | `app/models/schemas.py`, `app/api/query.py`, `app/services/query_service.py`, new `app/services/chat_service.py`, `app/prompts/manager.py` |
| **Effort** | 3–5 days |
| **Complexity** | Medium |
| **Risk** | Medium — prompt token growth, migration for existing clients |
| **Eval Impact** | ★★★★★ |

**Implementation sketch:**
1. Add `session_id: UUID | None` to `QueryRequest`
2. `ChatService.append_turn(session_id, role, message)` after each query
3. Load last N turns in `QueryService.ask` → inject into `PromptManager`
4. Frontend: pass `getSessionId()` on query calls

---

### A2. Integrate BM25 into `/query` Retrieval

| Field | Value |
|-------|-------|
| **Reason** | Report gap on sparse+dense hybrid; `/search` proves BM25 works but `/query` is dense-only |
| **Criterion** | Hybrid Ingestion and Retrieval (13) |
| **Files** | `app/rag/pipeline.py`, `app/rag/hybrid_pipeline.py`, `app/rag/merge.py`, `app/dependencies.py` |
| **Effort** | 2–4 days |
| **Complexity** | Medium |
| **Risk** | Low–Medium — latency from BM25 index build; reuse `BM25SearchService` |
| **Eval Impact** | ★★★★★ |

**Implementation sketch:**
1. In `retrieve` / `retrieve_hybrid`, `asyncio.gather` BM25 + vector
2. Fuse via existing `reciprocal_rank_fusion` before `rank_retrieval_results`
3. Feature flag: `ENABLE_QUERY_BM25=true`

---

### A3. Deep Health Endpoint

| Field | Value |
|-------|-------|
| **Reason** | Report correctly flags passive `/health` |
| **Criterion** | FastAPI Endpoint Setup (3) |
| **Files** | `app/api/health.py`, optional `app/services/health_service.py` |
| **Effort** | 0.5–1 day |
| **Complexity** | Low |
| **Risk** | Low |
| **Eval Impact** | ★★★☆☆ |

**Checks:** `SELECT 1`, optional Qdrant ping, embedding dimension sanity.

---

### A4. Locust Load Test Script

| Field | Value |
|-------|-------|
| **Reason** | Criterion 9 completely missing |
| **Criterion** | Load Testing |
| **Files** | `scripts/locustfile.py`, README section |
| **Effort** | 1 day |
| **Complexity** | Low |
| **Risk** | Low |
| **Eval Impact** | ★★★★☆ |

**Scenarios:** concurrent `/query`, `/search`, `/upload` with sample files.

---

### A5. Budget Limit Middleware

| Field | Value |
|-------|-------|
| **Reason** | Cost tracked but not enforced |
| **Criterion** | Cost Tracking & Budget Limits (8) |
| **Files** | new `app/services/budget_service.py`, `app/core/middleware.py`, `config.py` |
| **Effort** | 2–3 days |
| **Complexity** | Medium |
| **Risk** | Medium — false positives block legitimate users |
| **Eval Impact** | ★★★★☆ |

---

### A6. Prometheus `/metrics` Endpoint

| Field | Value |
|-------|-------|
| **Reason** | No operational metrics |
| **Criterion** | Observability (7) |
| **Files** | `app/core/metrics.py`, `app/api/metrics.py` or mount on router, `requirements.txt` |
| **Effort** | 2–3 days |
| **Complexity** | Medium |
| **Risk** | Low |
| **Eval Impact** | ★★★★☆ |

**Metrics:** request count, latency histogram, error rate, optional DB pool.

---

### A7. Activate structlog JSON Logging

| Field | Value |
|-------|-------|
| **Reason** | Dependency installed but unused |
| **Criterion** | Observability (7) |
| **Files** | `app/core/logging.py` |
| **Effort** | 0.5–1 day |
| **Complexity** | Low |
| **Risk** | Low |
| **Eval Impact** | ★★★☆☆ |

---

## B. Nice to Have

Strengthens project; lower evaluation mark impact.

### B1. Rate Limiting Middleware

| Effort | 1 day | **Criterion** 3 | **Impact** ★★★☆☆ |
| slowapi or custom token bucket on `/query`, `/upload` |

### B2. Redis Query Cache

| Effort | 3–4 days | **Criterion** 10 | **Impact** ★★★☆☆ |
| Cache identical questions + document scope |

### B3. Async Upload / Background OCR

| Effort | 3–5 days | **Criterion** 13 | **Impact** ★★★☆☆ |
| Celery/ARQ or FastAPI BackgroundTasks for ingest |

### B4. Semantic UnsupportedClaimDetector

| Effort | 3–5 days | **Criterion** 6 | **Impact** ★★★☆☆ |
| NLI mini-model or Ragas faithfulness local check |

### B5. HNSW Index Migration

| Effort | 2–3 days | **Criterion** 10 | **Impact** ★★☆☆ |
| Alembic migration `ivfflat` → `hnsw` |

### B6. Wire `compute_confidence` Multi-Signal

| Effort | 1 day | **Criterion** 7 | **Impact** ★★☆☆ |
| Replace fragmented confidence paths |

### B7. Populate Clause Table on Ingest

| Effort | 3–5 days | **Criterion** 5 | **Impact** ★★☆☆ |
| Structured SQL route becomes useful |

### B8. Frontend Handoff UI

| Effort | 1–2 days | — | **Impact** ★☆☆☆ |

### B9. Tesseract in Dockerfile

| Effort | 0.5 day | **Criterion** 13 | **Impact** ★★☆☆ |

### B10. Langfuse Prompt Registry

| Effort | 2–3 days | **Criterion** 2 | **Impact** ★★☆☆ |

---

## C. Not Worth Implementing (Low Eval ROI)

| Feature | Reason | Effort | Eval Benefit |
|---------|--------|--------|--------------|
| Full PostgreSQL FTS | BM25 already covers sparse on `/search`; integrating BM25 into `/query` is higher ROI | 3–5 days | Low |
| Replace LlamaIndex entirely | Massive rewrite; marginal eval gain | Weeks | Low |
| Custom vector DB | pgvector/Qdrant sufficient | Weeks | None |
| Kubernetes manifests | Optional deployment criterion; Docker+Render adequate | 1–2 weeks | Low |
| Full OAuth2 user system | High effort; not explicit eval criterion unless security scored | 1–2 weeks | Medium cost |
| Real-time WebSocket chat | REST memory sufficient for eval | 1 week | Low |
| `fusion_search_service.py` stub | File not on disk; functionality in `search_fusion.py` | — | None |

---

## ROI Ranking (All Recommendations)

| Rank | Item | Effort | Eval Impact | ROI | Phase |
|------|------|--------|-------------|-----|-------|
| 1 | A4 Locust load tests | Low | High | ★★★★★ | A |
| 2 | A3 Deep health | Low | Medium | ★★★★★ | A |
| 3 | A7 structlog JSON | Low | Medium | ★★★★☆ | A |
| 4 | A2 BM25 in `/query` | Medium | Very High | ★★★★☆ | A |
| 5 | A1 Chat memory | Medium | Critical | ★★★★☆ | A |
| 6 | A5 Budget limits | Medium | High | ★★★★☆ | A |
| 7 | A6 Prometheus | Medium | High | ★★★★☆ | A |
| 8 | B1 Rate limiting | Low | Medium | ★★★☆☆ | B |
| 9 | B9 Tesseract in Docker | Low | Low | ★★★☆☆ | B |
| 10 | B4 Semantic guardrails | Medium | Medium | ★★★☆☆ | B |
| 11 | B2 Redis cache | Medium | Medium | ★★☆☆☆ | B |
| 12 | B5 HNSW migration | Medium | Low | ★★☆☆☆ | B |
| 13 | B3 Async upload | High | Medium | ★★☆☆☆ | B |
| 14 | B7 Clause population | High | Low | ★★☆☆☆ | B |
| 15 | B10 Langfuse prompts | Medium | Low | ★★☆☆☆ | B |

---

## Suggested Implementation Order

**Week 1 (quick wins):** A3 → A4 → A7 → B1 → B9

**Week 2 (high impact):** A1 (memory) → A2 (BM25 in query)

**Week 3 (ops):** A5 → A6

**Backlog:** B2–B8, C items

---

## Related Documents

- [10_GAP_ANALYSIS.md](./10_GAP_ANALYSIS.md)
- [01_EXECUTIVE_SUMMARY.md](./01_EXECUTIVE_SUMMARY.md)
