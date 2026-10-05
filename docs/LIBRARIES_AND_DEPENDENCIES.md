# Libraries and Dependencies

**System:** Finance Risk & Investment Intelligence System (FRIIS)
**Manifests:** `capstone/requirements.txt` (backend, pinned), `capstone/frontend/package.json` (UI), `deploy/Dockerfile` (runtime images).
"Used in" columns were checked against actual `import` statements in `capstone/app`, `capstone/eval`, `capstone/mcp`.

---

## 1. Overview

The system is intentionally dependency-light:

- **15 pinned Python packages**: 12 runtime (11 actually imported) + 3 test/lint tools.
- **3 runtime npm packages** (React, React DOM, React Router) and 7 dev packages.
- **No LLM SDKs and no orchestration framework.** All LLM providers are called over plain HTTPS with `httpx` using the OpenAI-compatible `/chat/completions` contract; the multi-agent pipeline is plain Python in `app/graph.py`. This keeps routing and guardrails deterministic, testable, and free of vendor lock-in.
- **Security primitives come from the standard library:** `hashlib.pbkdf2_hmac` for passwords, `hmac` + `base64` for HS256 JWT, `secrets`/`uuid` for ids.

---

## 2. Backend Libraries

| Package | Version | Used in | Purpose |
|---|---|---|---|
| `fastapi` | 0.115.6 | `app/main.py`, `app/api/*` | REST API, dependency injection, OpenAPI docs at `/docs` |
| `uvicorn[standard]` | 0.32.1 | Docker `CMD`, local dev | ASGI server |
| `pydantic` | 2.10.3 | `app/schemas.py` | request/response models (`QueryRequest`, `QueryResponse`, …) |
| `pydantic-settings` | 2.6.1 | `app/core/config.py` | typed settings from env / `.env` with validators |
| `python-multipart` | 0.0.20 | FastAPI `UploadFile`, `Form` | PDF and CSV uploads |
| `starlette` | (FastAPI dep) | `app/main.py` | raw `Response` for `/metrics`, static files for the SPA |

---

## 3. AI / LLM Libraries

| Library | Status | Notes |
|---|---|---|
| `httpx` 0.28.1 | **used** | the only client for LLMs (`app/core/llm.py`), Gemini embeddings, Yahoo Finance (`app/current.py`) and Langfuse (`app/core/langfuse.py`) |
| OpenAI / Gemini / Groq / xAI SDKs | **not used** | replaced by one OpenAI-compatible HTTP call |
| LangChain / LangGraph / CrewAI | **not used** | orchestration is a hand-written state pipeline; earlier planning ADRs mention LangGraph but the code does not import it |

Supported providers (config only, no extra packages): `openai`, `grok` (xAI), `gemini`, `groq`, `ollama`.

---

## 4. RAG and Retrieval Libraries

| Capability | Implementation |
|---|---|
| PDF text extraction | `pypdf` 5.1.0 (`PdfReader`, lazy import in `app/rag.py`) |
| Chunking | stdlib string slicing (1200 chars, 180 overlap) |
| Embeddings | Gemini `batchEmbedContents` via `httpx` |
| Vector similarity | pgvector `<=>` in SQL; stdlib `math` cosine fallback |
| Lexical scoring | stdlib `re` tokeniser + set overlap |
| Fusion | weighted reciprocal rank fusion, ~10 lines in `rag._rrf` |

No vector-DB client, no LangChain retriever, no BM25 package.

---

## 5. Database Libraries

| Package | Version | Purpose |
|---|---|---|
| `sqlalchemy` | 2.0.36 | ORM models, engines, sessions, `text()` for templated SQL |
| `psycopg[binary]` | 3.2.13 | PostgreSQL driver (`postgresql+psycopg://`) |
| pgvector (Postgres extension) | server side | `vector` type, generated `embedding_vec` column, cosine operator |

No migration tool: `create_all` + idempotent `ADD COLUMN IF NOT EXISTS` in `app/core/db.py`.

---

## 6. Authentication and Security

| Need | Implementation |
|---|---|
| Password hashing | stdlib `hashlib.pbkdf2_hmac("sha256", …, 200_000)` |
| JWT (HS256) | stdlib `hmac` + `hashlib.sha256` + `base64.urlsafe_b64encode` in `app/core/security.py` |
| Bearer extraction | `fastapi.security.HTTPBearer` |
| Constant-time compare | `hmac.compare_digest` |
| CORS | `fastapi.middleware.cors.CORSMiddleware` |

---

## 7. Observability and Logging

| Package | Version | Used in | Purpose |
|---|---|---|---|
| `structlog` | 24.4.0 | `app/core/logging.py` | JSON logs bound to `trace_id`, per-agent log files |
| `prometheus-client` | 0.21.1 | `app/main.py` | `frii_requests_total` counter, `/metrics` |
| Langfuse | HTTP API | `app/core/langfuse.py` | trace + generation events via `httpx` POST to `/api/public/ingestion` (no SDK) |

---

## 8. Document Processing

| Format | Library |
|---|---|
| PDF upload + policy corpus | `pypdf` |
| Portfolio CSV upload | stdlib `csv` + `io` + `decimal` (`app/sqlq/import_portfolio.py`) |
| Screen export CSV | stdlib `csv` (`GET /api/v1/screens/{id}/export.csv`) |

---

## 9. Frontend Libraries

| Package | Version | Kind | Purpose |
|---|---|---|---|
| `react` | ^18.3.1 | runtime | UI |
| `react-dom` | ^18.3.1 | runtime | DOM renderer |
| `react-router-dom` | ^6.28.0 | runtime | routing + `ProtectedRoute` / `RoleRoute` guards |
| `typescript` | ^5.6.3 | dev | type checking (`tsc -b`) |
| `vite` | ^5.4.11 | dev | dev server (proxy `/api` → `:8000`) and build |
| `@vitejs/plugin-react-swc` | ^3.11.0 | dev | fast JSX/TS transform |
| `vitest` | ^2.1.9 | dev | unit tests |
| `jsdom` | ^25.0.1 | dev | DOM for tests |
| `@types/react`, `@types/react-dom` | ^18.3 | dev | typings |

SSE streaming uses the browser `fetch` + `ReadableStream`; no HTTP client or state library is installed.

---

## 10. Testing Libraries

| Package | Version | Use |
|---|---|---|
| `pytest` | 8.3.4 | 85 backend tests in `capstone/tests/` |
| `pytest-cov` | 6.0.0 | coverage with `fail_under = 85` (`pyproject.toml`) |
| FastAPI `TestClient` | (FastAPI dep) | API tests |
| `vitest` + `jsdom` | see §9 | frontend tests (`quality.test.ts`, `api/query.test.ts`) |
| Eval harness | in-repo (`capstone/eval/`) | 50 golden, 24 attack, 10 negative-control queries → 16 SLOs |

---

## 11. Development / Build Tools

| Tool | Version | Use |
|---|---|---|
| `ruff` | 0.8.4 | lint (`E`, `F`), line length 140, target py39 |
| Docker multi-stage | `node:20-alpine` → `python:3.11-slim` | one image with API + built UI, non-root user |
| Render Blueprint | `render.yaml` | free web service + Postgres 16 |
| `cov.sh` | repo script | coverage run helper |

---

## 12. External Services and SDKs

| Service | Access | Required? |
|---|---|---|
| OpenAI (default LLM) | HTTPS, `OPENAI_API_KEY` | optional — deterministic synthesis works without it |
| Gemini (fallback LLM + embeddings) | HTTPS, `GEMINI_API_KEY` | optional — lexical retrieval works without embeddings |
| Groq / xAI / Ollama | HTTPS / local | optional alternatives |
| Langfuse Cloud | HTTPS, public + secret key | optional |
| Yahoo Finance chart + search | HTTPS, no key | only for `evidence_mode = current` |
| Chittorgarh / InvestorGain | `chittorgarh_client` package | only for IPO/GMP questions in current mode |
| Render | Docker + managed Postgres | cloud hosting |

---

## 13. Potentially Unused / Missing Dependencies

| Item | Finding | Suggested action |
|---|---|---|
| `python-jose[cryptography]` | listed in `requirements.txt`, **never imported** (JWT is hand-rolled with `hmac`) | remove from `requirements.txt` |
| `chittorgarh_client` | imported lazily in `app/current.py`, **not listed**; missing package degrades gracefully to a gap message | add as optional or document |
| `mcp` | imported by `capstone/mcp/chittorgarh_server.py` (IDE tool), **not listed** | document as dev-only |

---

## 14. Dependency Summary Matrix

| Layer | Third-party | Standard library |
|---|---|---|
| API | fastapi, uvicorn, pydantic, pydantic-settings, python-multipart | json, time, contextlib |
| Orchestration | – | re, time, typing |
| Guardrails | – | re, datetime |
| Retrieval | pypdf, httpx | re, math |
| SQL | sqlalchemy, psycopg | decimal, csv |
| LLM | httpx | time |
| Auth | – | hashlib, hmac, base64, secrets, uuid |
| Observability | structlog, prometheus-client, httpx | logging |
| Frontend | react, react-dom, react-router-dom | – |
| Test / build | pytest, pytest-cov, ruff, vite, vitest, typescript | – |

---

## Summary

The backend runs on 11 runtime packages; everything an AI project usually pulls in via large frameworks (LLM SDKs, orchestration, vector clients, auth libraries) is covered by `httpx`, pgvector, and the Python standard library. The one cleanup item is removing the unused `python-jose` pin.
