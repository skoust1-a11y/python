# Operations (v2)

Capstone engineering readiness. Product RT/user workspace: `../production/`.

---

## 1. Runtime layout

| Process | Port | Notes |
|---|---|---|
| API (uvicorn) | 8000 | Stateless |
| Postgres | 5432 | auth + finance DBs |
| React dev | 5173 | Vite; CORS to API |
| OTel collector | 4317 | Optional |

---

## 2. Environment (minimum)

```bash
APP_ENV=local|ci|prod
AUTH_DATABASE_URL=postgresql+asyncpg://...
DATABASE_URL=postgresql+asyncpg://...  # RO user for query path
LLM_API_KEY=...
JWT_SECRET=...                         # Sprint 8+
VITE_API_BASE_URL=http://localhost:8000
CURRENT_FACTORS_ENABLED=false          # capstone: always false
```

Prod: refuse stub auth and placeholder secrets (ADR-016). Live quotes/news stay off until production providers are connected (`../production/03_Realtime_Market_Data.md`).

---

## 3. Observability

| Signal | Requirement |
|---|---|
| Logs | JSON stdout: trace_id, category, outcome, latency_ms, cost_usd |
| Traces | Span per graph node |
| Metrics | Prometheus `/metrics`: requests, latency histogram, escalations |
| Health | `/health` liveness; `/health/ready` DB + index + LLM |

---

## 4. Runbooks (must exist)

| ID | Scenario | Action |
|---|---|---|
| RB-001 | Escalation miss on golden | P0: freeze, unit test, fix rule, add attack case |
| RB-002 | Retrieval empty for known doc | Re-ingest; check chunk QA |
| RB-003 | SQL template wrong rows | Fix template + golden ground truth |
| RB-004 | p95 latency breach | Profile spans; reduce fetch_k; parallelize |
| RB-005 | JWT/auth failure prod | Check secret rotation; clock skew |

Full text: v1 `../05_Project_Setup_Readiness.md` §5.

---

## 5. Deploy (capstone demo)

- Multi-stage Dockerfile, non-root user
- `deploy/compose.prod.yml` with external DB URL
- Same image local and cloud (ADR-017)

Checklist: `../16_Production_and_Cloud_Readiness.md` §6.

---

## 6. Backup & restore (demo)

- Postgres volume snapshot before schema changes
- Re-ingest PDFs from `Documents/` if vector corrupted
- Auth DB separate backup from finance DB
