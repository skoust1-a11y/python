# Production — Architecture & APIs

## Services (logical)
- `api` — FastAPI (auth, workspace CRUD, query orchestration)
- `worker` — ingest docs, provider sync jobs
- `finance_auth_db` — identities
- `workspace_db` — user portfolios/metrics (may be same Postgres instance, **different database**)
- `knowledge_db` — org-scoped `policy_chunks` / doc vectors (pgvector)
- Object storage — uploaded PDFs
- Secret manager — provider keys, JWT secrets

## Core APIs
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/workspace/portfolios` | Create book |
| POST | `/api/v1/workspace/positions/import` | CSV/JSON upsert |
| POST | `/api/v1/workspace/documents` | Upload strategy/risk docs |
| POST | `/api/v1/workspace/metrics/definitions` | Register metrics |
| POST | `/api/v1/workspace/metrics/values` | Upsert values |
| POST | `/api/v1/workspace/providers/connect` | Store provider config ref |
| POST | `/api/v1/workspace/providers/sync` | Pull quotes/fundamentals |
| POST | `/api/v1/query` | Agent query. Body: `options.evidence_mode` = `corpus` (docs+SQL) or `current` (plus live quotes/news) |
| GET | `/api/v1/auth/me` | Includes `features.current_factors` for the UI toggle |

Agents use **read-only** SQL templates on workspace tables. No LLM-authored SQL. No LLM writes to positions/metrics.

`current` calls `ProviderAdapter` + `NewsAdapter` only when `CURRENT_FACTORS_ENABLED=true` and keys exist; otherwise **409**. See `03_Realtime_Market_Data.md`.
