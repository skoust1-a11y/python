# Current System Architecture Analysis

**System:** Finance Risk & Investment Intelligence System (FRIIS)
**Version:** 0.4.0 (`capstone/app/core/config.py`)
**Scope of this document:** what the code in `capstone/` actually does today. Every statement links to the file that implements it (see §17).

> Educational system on synthetic data. It is **not investment advice**; every answer carries citations and the disclaimer defined in `capstone/app/core/constants.py`.

---

## 1. Current system components

| # | Component | Technology | Location |
|---|---|---|---|
| 1 | Web UI (SPA) | React 18 + TypeScript + Vite 5 + React Router 6 | `capstone/frontend/` |
| 2 | REST API | FastAPI 0.115 on Uvicorn | `capstone/app/main.py`, `capstone/app/api/routers.py` |
| 3 | Orchestrator ("graph") | Plain Python state pipeline, 8 agent steps | `capstone/app/graph.py` |
| 4 | Guardrails | Regex input guard + E1–E8 escalation rules | `capstone/app/guardrails.py` |
| 5 | Retrieval (RAG) | Hybrid pgvector cosine + lexical overlap, weighted RRF | `capstone/app/rag.py` |
| 6 | Structured data (SQL) | 19 named, parameterised, RBAC-scoped SQL templates | `capstone/app/sqlq/templates.py`, `executor.py` |
| 7 | Live market factors | Yahoo Finance chart/search + Chittorgarh IPO/GMP | `capstone/app/current.py` |
| 8 | Equity screener | Filter DSL → SQL over `equity_universe` + `equity_fundamentals` | `capstone/app/screens.py` |
| 9 | LLM gateway | OpenAI-compatible `/chat/completions` over httpx; primary + fallback provider | `capstone/app/core/llm.py` |
| 10 | Embeddings | Gemini `gemini-embedding-001`, 1536 dims | `capstone/app/core/llm.py::embed_texts` |
| 11 | Auth | PBKDF2-SHA256 passwords, HS256 JWT (stdlib `hmac`) | `capstone/app/core/security.py` |
| 12 | Databases | PostgreSQL 16 + pgvector; 3 logical DBs (auth / risk / stock) | `capstone/app/core/db.py`, `capstone/app/models.py` |
| 13 | Observability | structlog JSON logs, Prometheus `/metrics`, Langfuse ingestion, DB traces | `capstone/app/core/logging.py`, `langfuse.py` |
| 14 | Evaluation harness | 50 golden + 24 attack + 10 negative-control queries, 16 SLOs | `capstone/eval/` |
| 15 | MCP server | Chittorgarh IPO/NCD/buyback tools for the IDE | `capstone/mcp/chittorgarh_server.py` |
| 16 | Deployment | Multi-stage Docker (Node build → Python 3.11 slim), Render Blueprint | `deploy/Dockerfile`, `render.yaml` |

---

## 2. Frontend architecture

- **Stack:** React 18.3, React Router 6.28, TypeScript 5.6, Vite 5.4 with `@vitejs/plugin-react-swc`, Vitest + jsdom. No UI kit and no state library; state lives in two React contexts.
- **Contexts:** `auth/AuthContext.tsx` (JWT + current user, stored by `auth/tokenStorage.ts`) and `auth/ProfileContext.tsx` (active analysis profile).
- **Route guards** (`src/routes/`): `PublicOnlyRoute` (login/signup), `ProtectedRoute` (any signed-in user), `RoleRoute` (role allow-list).
- **API layer** (`src/api/`): one `client.ts` wrapper adds the bearer token and `X-Request-Id`; feature modules `query.ts`, `profiles.ts`, `screens.ts`, `auth.ts`.

| Route | Page | Access |
|---|---|---|
| `/login`, `/signup` | `LoginPage`, `SignupPage` | public only |
| `/app` | `OverviewPage` | signed in |
| `/app/ask` | `QueryPage` (SSE streaming chat, routing panel, sources, escalation banner) | signed in |
| `/app/upload` | `UploadPage` (policy PDFs, ticker filings, portfolio CSV) | signed in |
| `/app/portfolios` | `PortfolioPage` | signed in |
| `/app/documents`, `/app/documents/type/:useCase` | `DocumentsPage`, `DocumentTypePage` | signed in |
| `/app/screens` | `ScreensPage` (equity screener, saved screens, CSV export) | signed in |
| `/app/escalations` | `EscalationsPage` | risk_manager, compliance, admin |
| `/app/admin` | `AdminPage` (users, traces, reindex, templates, latest eval) | admin |

Shared components: `AnswerBody`, `SourcesUsed`, `RoutingPanel`, `EscalationBanner`, `Disclaimer`, `PortfolioUploadForm`.

In production the built `frontend/dist` is served by FastAPI itself (`/assets` static mount + SPA fallback in `app/main.py`), so UI and API share one origin. Locally, Vite on `:5173` proxies `/api` to `:8000`.

---

## 3. API architecture

- **App factory:** `create_app()` in `app/main.py`. On startup the lifespan hook runs `bootstrap(reset=False)` (creates schema, seeds if empty).
- **Middleware:** CORS (origins from `CORS_ORIGINS` + `RENDER_EXTERNAL_URL`), plus one HTTP middleware that assigns/propagates `X-Request-Id` as the trace id, counts requests in Prometheus, logs method/path/status/latency, and sets `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`.
- **Error contract:** validation errors return `400 {"error": {"code": "invalid_request", "message", "field"}, "trace_id"}`.
- **Controls on `/api/v1/query`:** `Idempotency-Key` header replay (table `idempotency_keys`), per-user rate limit (`RATE_LIMIT_PER_MINUTE`, default 30), per-user daily cost budget (`DAILY_BUDGET_USD`, default $5), token cap (`MAX_TOKENS_PER_REQUEST`, default 8000).

### Endpoint groups (44 routes: 2 in `main.py`, 42 in `routers.py`)

| Tag | Routes |
|---|---|
| Health | `GET /health`, `GET /health/ready`, `GET /metrics` |
| Auth | `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`, `POST /api/v1/auth/token`, `GET /api/v1/auth/me` |
| Profiles | `GET/POST /api/v1/profiles`, `DELETE /api/v1/profiles/{id}`, `GET /api/v1/profiles/{id}/types`, `PUT/DELETE /api/v1/profiles/{id}/guidelines/{use_case}` |
| Query | `POST /api/v1/query` (JSON), `POST /api/v1/query/stream` (SSE) |
| Sessions | `GET/DELETE /api/v1/sessions`, `PATCH/DELETE /api/v1/sessions/{id}`, `GET /api/v1/sessions/{id}/turns` |
| Screens | `GET /api/v1/screens/fields`, `POST /api/v1/screens/run`, `POST /api/v1/screens/from-nl`, `GET/POST /api/v1/screens`, `GET/PUT/DELETE /api/v1/screens/{id}`, `GET /api/v1/screens/{id}/export.csv` |
| Portfolios | `GET /api/v1/portfolios`, `POST /api/v1/portfolios/upload` (CSV ≤ 1 MB) |
| Documents | `GET/POST /api/v1/documents` (PDF ≤ 5 MB), `GET /api/v1/documents/{id}`, `GET /api/v1/documents/{id}/file`, `DELETE /api/v1/documents/{id}` |
| Escalations | `GET /api/v1/escalations`, `GET /api/v1/escalations/{id}` |
| Admin | `PATCH /api/v1/admin/users/{id}` (+ legacy `/admin/users/{id}`), `POST /admin/reindex`, `GET /admin/traces/{trace_id}`, `GET /admin/templates`, `GET /admin/eval/latest` |

### SSE stream (`/api/v1/query/stream`)

`run_query` runs in a worker thread and pushes each agent name onto a queue. The response emits, in order: `progress` (one per agent step) → `routing` → either `escalation` or `citation`× N + `token` → `done` (full envelope). Errors surface as `event: error` with a code (`rate_limited`, `budget_exceeded`, `current_factors_unavailable`).

---

## 4. Document ingestion pipeline

Two corpora share one pipeline (`app/rag.py::ingest_user_pdf`, `_extract_chunks`):

| Corpus | Tables | Who writes | Types |
|---|---|---|---|
| House policy corpus | `user_documents` + `policy_chunks` (risk DB) | seed (7 system PDFs) or user upload | strategy, risk, regulatory, research, evaluation, framework, matrix |
| Ticker filings | `stock_documents` + `stock_chunks` (stock DB) | user upload with a symbol | `ar` (annual report), `concall`, `ppt`; `note` is system-generated |

Steps:

1. **Validate:** `.pdf` extension, non-empty, ≤ 5 MB, valid use case or ticker kind, ticker format.
2. **Store file:** write to local disk under the corpus root (`CorpusStore` protocol; `S3CorpusStore` is a stub reserved for cloud).
3. **Extract:** `pypdf.PdfReader`, page by page; pages under `CHUNK_MIN_CHARS` (40) are skipped.
4. **Chunk:** fixed windows of `CHUNK_SIZE_CHARS` = 1200 with `CHUNK_OVERLAP_CHARS` = 180; chunk id `pdf_{doc}_{page}_{part}`; section = `page N`.
5. **Embed:** `embed_texts` batches of 100 to Gemini; vectors are kept only if every vector has exactly `EMBEDDING_DIM` (1536) dims, so models never mix.
6. **Replace:** one document per (owner, profile, use case) or (owner, profile, symbol, kind); the previous one and its chunks are deleted.
7. **Persist:** document row + chunks; on Postgres the generated column `embedding_vec vector` is computed automatically from the text `embedding`.
8. **Rollback:** on extraction failure or zero chunks the file is removed and a `DocumentIngestError` becomes HTTP 400.

`POST /admin/reindex` rebuilds the system policy chunks from the 7 PDFs in `capstone/Documents/`.

---

## 5. Ask pipeline (`app/graph.py::run_query`)

The orchestrator is a single deterministic function that records every step as an "agent" in `routing.agents_used`, a timed span in `traces.spans_json`, and a structured log line.

```
input_guard → router → [retrieval] → [portfolio_eval] → [market_data] → [risk] → (escalation | synthesis) → persist → Langfuse
```

### 5.1 Stages

| Stage | What it does |
|---|---|
| Session + memory | Creates or reuses a session; loads the last turns for the same profile; `_carry_entities` resolves follow-ups ("that", "those") by carrying entities from prior turns. |
| `input_guard` | `classify_input` flags override intent, regulatory bypass, flag suppression, prompt injection/jailbreak, role escalation, data exfiltration, and advice solicitation. |
| `router` | `_route` applies ordered regex rules R1–R8 and returns category, confidence, action intent and rationale (table 5.2). E1 hits force `C5_ESCALATION`. |
| Short-circuits | Greeting → canned help text. Out-of-corpus topic (crypto, ESG, private equity, …) → `insufficient_evidence`. Exfiltration → `refused`. Advice request → `refused`. |
| Stock-note cache | With a ticker, a saved research note is reused unless newer filings exist or `replace_note` is set. |
| `retrieval` | `rag.retrieve` over documents visible to this user/profile/category (C1, C3, C4 or ticker mode). |
| `portfolio_eval` | `_pick_templates` chooses SQL templates from query keywords; `run_template` executes each with RBAC. |
| `market_data` | For C4 and whenever `evidence_mode="current"`: Yahoo quotes/news and Chittorgarh IPO/GMP. |
| `risk` | For C3/C4: collects flagged assets, derives risk level, detects breaches (single-sector cap 25 %, emerging-market cap 15 %). |
| Post-evidence guard | `evaluate_post_evidence` produces triggers E2–E8. |
| `escalation` | If `should_handoff` → outcome `escalated`, reviewer assigned, escalation record written; the question is **not** answered. |
| `synthesis` | Builds a deterministic grounded verdict + data tables; then asks the LLM to rewrite it with the profile guideline overlay. On any LLM failure the deterministic text is used (`synthesis_mode`). `strip_advice` removes buy/sell/hold/target-price sentences. |
| Final checks | Answered without citations → `insufficient_evidence`. Token cap exceeded → `refused`. |
| Persist | `turns`, `traces`, `escalations`; ticker answers saved as a stock `note`; `emit_query` to Langfuse. |

### 5.2 Routing rules

| Rule | Condition | Category | Confidence |
|---|---|---|---|
| R1 | Override/bypass/injection (E1) | C5_ESCALATION | 0.99 |
| R5 | Action intent + high-risk framing | C4_HIGH_RISK | 0.92 |
| R4 | Policy compared to data nouns, or policy + data operation | C3_HYBRID | 0.90 |
| R3 | Data operation only | C2_SQL | 0.95 |
| R2 | Policy language only | C1_RAG | 0.95 |
| R7 | Action intent, nothing else | C4_HIGH_RISK | 0.72 |
| R8 | Fallback | C3_HYBRID | 0.58 |

### 5.3 Category → agent path (`CATEGORY_PATHS`)

| Category | Label | Path |
|---|---|---|
| C1_RAG | Investment Policy Interpretation | retrieval → synthesis |
| C2_SQL | Portfolio & Risk Data Lookup | portfolio_eval → synthesis |
| C3_HYBRID | Hybrid Risk Evaluation | retrieval → portfolio_eval → risk → synthesis |
| C4_HIGH_RISK | High-Risk Financial Decisions | retrieval → portfolio_eval → market_data → risk → synthesis |
| C5_ESCALATION | Escalation / Human Handoff | escalation |

### 5.4 Outcomes

`answered`, `refused`, `escalated`, `insufficient_evidence` (`OUTCOMES` in `constants.py`).

### 5.5 Response envelope (`QueryResponse`)

`trace_id`, `session_id`, `outcome`, `answer`, `data_tables`, `citations[]` (type `doc` | `sql` | quote | news), `routing{category, category_label, path, agents_used, confidence, rationale}`, `risk{level, rationale, escalation_flag, breaches, flagged_assets}`, `escalation{required, triggers, trigger_details, escalation_id, reason, recommended_reviewer}`, `gaps`, `latency_ms`, `usage`, `cost_usd`, `synthesis_mode`, `disclaimer`, and — for admin/compliance only — the raw evidence bundle.

---

## 6. Retrieval architecture (`app/rag.py::retrieve`)

1. **Visibility filter** — `visible_doc_ids(owner, category, symbol, profile)`: system docs + the user's own uploads for the active profile, narrowed by use case; ticker mode searches only `stock_chunks` for that symbol.
2. **Dense scores** — query embedded once; on Postgres, `1 - (embedding_vec <=> :q)` is computed in SQL with a `vector_dims` guard. Without pgvector the same cosine is computed in Python.
3. **Lexical scores** — token overlap ratio between query and chunk text + section + title; a weak floor (`RETRIEVAL_WEAK_SCORE` = 0.2) for substring hits.
4. **Fusion** — weighted reciprocal rank fusion: `Σ weight / (k + rank)`, with `RETRIEVAL_VECTOR_WEIGHT` = 0.5, `RETRIEVAL_LEXICAL_WEIGHT` = 0.5, `RETRIEVAL_RRF_K` = 60.
5. **Floor** — a chunk is dropped when `max(dense, lexical) < RETRIEVAL_MIN_SCORE` (0.35).
6. **Top-k** — `RETRIEVAL_TOP_K` = 5 (request may ask up to 10).

Each hit carries `chunk_id, doc_id, doc_title, section, page, score, filename, origin, role`; those become `doc` citations with a 280-character excerpt.

---

## 7. LLM architecture (`app/core/llm.py`)

- **One protocol:** every provider is called through the OpenAI-compatible `POST {base}/chat/completions` using `httpx`; no vendor SDK.
- **Providers:** `openai` (gpt-4o-mini router / gpt-4o agent), `grok` (xAI), `gemini` (OpenAI-compatible endpoint), `groq`, `ollama` (local).
- **Failover chain:** `LLM_PROVIDER` then `LLM_FALLBACK_PROVIDER` (Render uses openai → gemini). Endpoints without a key are skipped.
- **Retries:** `LLM_MAX_RETRIES` = 2 with exponential backoff on 429/5xx/network errors; `insufficient_quota` and other 4xx fail fast.
- **Temperature:** 0.0. **Timeout:** 20 s.
- **Where the LLM is used:** answer rewriting in synthesis (grounded text in, grounded text out), natural-language → screen definition, and the optional LLM-as-judge SLO in eval. **Routing and guardrails never call the LLM**, so they stay deterministic and testable.
- **Prompts:** `app/prompts/` — router, retrieval, portfolio_eval, market_data, risk, synthesis, synthesis_stock, escalation + refusals (insufficient_evidence, non_advice, override_refusal).
- **Cost control:** token/cost estimate per request, per-user daily budget and rate limit (`app/core/budget.py`).

---

## 8. Evaluation / quality pipeline (`capstone/eval/`)

| Asset | Count |
|---|---|
| `golden/golden_queries.jsonl` | 50 (C1 15, C2 10, C3 10, C4 10, C5 5) |
| `golden/attack_suite.jsonl` | 24 |
| `golden/negative_controls.jsonl` | 10 |

`python -m eval.run --suite all [--judge]` scores 16 SLOs (`eval/score.py`) and writes `eval/reports/<run>/report.md`. The final report (`eval/reports/final/report.md`) passes 15/15 measured SLOs; SLO 7 (LLM-as-judge) is filled only with `--judge`.

| # | SLO | Target |
|---|---|---|
| 1 | Faithfulness | ≥ 80 % |
| 2 | Answer relevance | ≥ 75 % |
| 3 | Context precision | ≥ 70 % |
| 4 | Latency C1/C2 p95 | ≤ 2000 ms |
| 5 | Accuracy | ≥ 85 % |
| 6 | Recall | ≥ 75 % |
| 7 | LLM-as-judge | ≥ 80 % |
| 8 | Task success | ≥ 90 % |
| 9 | SQL correctness | ≥ 95 % |
| 10 | Source attribution | 100 % |
| 11 | Critical misclassification | < 3 % |
| 12 | Escalation recall | 100 % |
| 13 | RBAC violations | 0 |
| 14 | Guardrail effectiveness | 100 % |
| 15 | Query routing accuracy | ≥ 95 % |
| 16 | Risk classification | ≥ 95 % |

Unit/integration tests: 85 pytest tests in `capstone/tests/` with an 85 % coverage gate (`pyproject.toml`); Vitest for the frontend.

---

## 9. Authentication and authorization

- **Signup/login:** email + password; PBKDF2-HMAC-SHA256, 200 000 rounds, 16-byte salt.
- **Token:** HS256 JWT built with stdlib `hmac`; claims `sub, email, role, portfolio_ids ("ALL" or list), iat, exp`; TTL `SESSION_TTL_MINUTES` = 60.
- **Every request** re-reads the user row, so deactivated users are rejected immediately.
- **Stub mode** (`AUTH_MODE=stub`, `X-Debug-Role` header) exists for tests and is refused when `APP_ENV=prod`; production also refuses the default `JWT_SECRET`.

| Role | Portfolio scope | Escalations | Traces / evidence bundle | Admin |
|---|---|---|---|---|
| analyst | own `portfolio_ids` | own | – | – |
| risk_manager | ALL | all | – | – |
| compliance | ALL | all | yes | – |
| admin | ALL | all | yes | yes |

**Row-level security for SQL** (`app/sqlq/executor.py`): each template declares `rbac = none | portfolio_id | asset_via_holdings`; the executor injects `portfolio_id IN (...)` or an `asset_name IN (SELECT … FROM portfolio_holdings …)` sub-query, then re-checks every returned row and raises `RbacViolation` (HTTP 403) on any leak. Every execution is written to `audit_log`.

---

## 10. Data and storage architecture

| Store | Contents |
|---|---|
| `finance_auth_db` | users, sessions, turns, profiles, profile_guidelines, saved_screens, escalations, traces, audit_log, idempotency_keys |
| `finance_risk_db` | portfolios, portfolio_holdings, asset_risk_logs, market_indicators, investment_decisions, policy_chunks (+ `embedding_vec`), user_documents, equity_universe, equity_fundamentals |
| `finance_stock_db` | stock_documents, stock_chunks (+ `embedding_vec`) |
| Local disk | policy PDFs (`capstone/Documents/`), uploaded PDFs, logs |

On Render all three URLs point to **one** Postgres instance (table names do not collide). Details: `CURRENT_DATABASE_ARCHITECTURE.md`.

---

## 11. Observability

| Signal | Implementation |
|---|---|
| Structured logs | structlog JSON; per-agent log files under `logs/`; every line bound to `trace_id`, `session_id`, `role`, `category` |
| Request metrics | Prometheus counter `frii_requests_total{path,method}` at `GET /metrics` |
| Readiness | `GET /health/ready` checks DB, vector index (chunk + embedded counts), LLM, template count |
| Traces | `traces` table: query, category, outcome, per-agent spans with duration; `GET /admin/traces/{id}` |
| Audit | `audit_log` for every SQL template run (role, params, row count, duration) |
| LLM observability | `emit_query` posts trace + generation events to the Langfuse ingestion API when keys are set |
| Cost | `usage` and `cost_usd` in each envelope; daily budget per user |

---

## 12. Deployment architecture

- **Image** (`deploy/Dockerfile`): stage 1 `node:20-alpine` builds the React app; stage 2 `python:3.11-slim` installs `requirements.txt`, copies the API and `frontend/dist`, runs as non-root `appuser` (uid 10001), `uvicorn app.main:app` on `$PORT`.
- **Render Blueprint** (`render.yaml`): one free Docker web service `frii-api` (health check `/health`) + one free Postgres 16 `frii-db`. `JWT_SECRET` is generated; API keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`, Langfuse) are entered in the dashboard.
- **Local:** Postgres on `localhost:5432`, `uvicorn --reload :8000`, `npm run dev :5173`.

---

## 13. Scope boundaries

| In scope and implemented | Deliberately out of scope |
|---|---|
| RAG + SQL + hybrid routing, 5 categories | Trading or order execution |
| E1–E8 escalation with reviewer assignment | Buy/sell/hold advice (stripped and refused) |
| Portfolio CSV upload, policy + filing PDF upload | Real customer data (all data synthetic) |
| Live quotes/news/IPO data behind `CURRENT_FACTORS_ENABLED` | S3 object storage (stub only) |
| Equity screener with saved screens and CSV export | External identity provider (local JWT instead) |

---

## 14. Current end-to-end system flow

1. User signs in at `/login`; the SPA stores the JWT.
2. On `/app/ask` the user types a question; the SPA calls `POST /api/v1/query/stream` with the active profile.
3. Middleware stamps `X-Request-Id`; the route checks rate limit, budget, and profile ownership.
4. `input_guard` and `router` classify the request (deterministic).
5. Retrieval, SQL templates, market data and risk run as the category requires; each emits a `progress` event.
6. `evaluate_post_evidence` decides: escalate, refuse for missing evidence, or synthesise.
7. Synthesis produces a cited answer; the LLM may rephrase it; advice language is stripped.
8. Turn, trace and escalation rows are written; Langfuse receives the trace.
9. The SPA renders routing, answer, data tables, sources and any escalation banner; reviewers see escalations at `/app/escalations`.

---

## 15. Architecture connection matrix

| From → To | Protocol | Purpose |
|---|---|---|
| Browser → FastAPI | HTTPS JSON / SSE | all features |
| FastAPI → `finance_auth_db` | SQLAlchemy + psycopg 3 | identity, memory, audit, traces |
| FastAPI → `finance_risk_db` | SQLAlchemy + psycopg 3 | finance tables, policy chunks, equities |
| FastAPI → `finance_stock_db` | SQLAlchemy + psycopg 3 | ticker filings |
| FastAPI → LLM provider | HTTPS (OpenAI-compatible) | answer rewrite, NL screen, judge |
| FastAPI → Gemini embeddings | HTTPS | chunk + query vectors |
| FastAPI → Yahoo Finance | HTTPS | quotes, news (current mode) |
| FastAPI → Chittorgarh | `chittorgarh_client` | IPO / GMP / NCD / buybacks (current mode) |
| FastAPI → Langfuse | HTTPS ingestion API | traces and generations |
| Prometheus → FastAPI | HTTP scrape `/metrics` | request counters |
| Cursor IDE → MCP server | stdio MCP | Chittorgarh tools for developers |

---

## 16. Diagram input

The diagrams in this folder were drawn from the tables above:

- `Architecture.png` — layers of §1, cloud mapping of §12, cross-cutting controls of §9 and §11.
- `WorkFlow.png` — stages of §5, routing of §5.2, escalation triggers E1–E8.
- `Database_diagrams.png` — tables and relationships of `CURRENT_DATABASE_ARCHITECTURE.md`.

---

## 17. Evidence index

| Topic | File |
|---|---|
| App factory, middleware, health, metrics | `capstone/app/main.py` |
| All routes | `capstone/app/api/routers.py` |
| Auth dependencies, role guards | `capstone/app/api/deps.py` |
| Settings and defaults | `capstone/app/core/config.py` |
| Categories, paths, triggers, reviewers, policy docs | `capstone/app/core/constants.py` |
| Orchestrator | `capstone/app/graph.py` |
| Guardrails | `capstone/app/guardrails.py` |
| Retrieval and ingestion | `capstone/app/rag.py` |
| SQL templates and executor | `capstone/app/sqlq/templates.py`, `capstone/app/sqlq/executor.py` |
| Models | `capstone/app/models.py` |
| LLM + embeddings | `capstone/app/core/llm.py` |
| Password + JWT | `capstone/app/core/security.py` |
| Live factors | `capstone/app/current.py` |
| Evaluation | `capstone/eval/run.py`, `capstone/eval/score.py`, `capstone/eval/reports/final/report.md` |
| Frontend routes | `capstone/frontend/src/App.tsx` |
| Container + cloud | `deploy/Dockerfile`, `render.yaml` |
