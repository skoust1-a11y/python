# Database Table Reference

**System:** Finance Risk & Investment Intelligence System (FRIIS)
Column tables in §2 are generated from `capstone/app/models.py` (SQLAlchemy metadata), so names, types, keys and defaults match the code exactly.

---

## Executive Summary

- **21 tables** across **3 logical PostgreSQL databases**: 10 in `finance_auth_db`, 9 in `finance_risk_db`, 2 in `finance_stock_db`.
- **Finance core** (5 tables) is the synthetic course dataset; the query path reads it only through 19 named, RBAC-scoped SQL templates.
- **Vectors** live in `policy_chunks` and `stock_chunks` (text `embedding` + generated pgvector `embedding_vec`, 1536 dims).
- **Every query** leaves a `turns` row, a `traces` row, `audit_log` rows for each SQL template, and an `escalations` row when handed off.

---

## 1. Database Overview

| Database | Env var | Tables |
|---|---|---|
| `finance_auth_db` | `AUTH_DATABASE_URL` | users, sessions, turns, profiles, profile_guidelines, saved_screens, escalations, traces, audit_log, idempotency_keys |
| `finance_risk_db` | `DATABASE_URL` | portfolios, portfolio_holdings, asset_risk_logs, market_indicators, investment_decisions, policy_chunks, user_documents, equity_universe, equity_fundamentals |
| `finance_stock_db` | `STOCK_DATABASE_URL` | stock_documents, stock_chunks |

On Render the three URLs share one Postgres 16 instance.

---

## 2. Table Documentation

Not shown by the ORM: on PostgreSQL, `policy_chunks` and `stock_chunks` also get
`embedding_vec vector GENERATED ALWAYS AS (CAST(embedding AS vector)) STORED` (added by `app/core/db.py::_ensure_embedding_columns`).

### `audit_log` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `audit_id` | INTEGER | no | PK, autoincrement |
| `trace_id` | VARCHAR | yes |  |
| `query_id` | VARCHAR | yes |  |
| `role` | VARCHAR | yes |  |
| `params_json` | TEXT | yes |  |
| `row_count` | INTEGER | yes |  |
| `duration_ms` | INTEGER | yes |  |
| `created_at` | DATETIME | yes | default utcnow |

### `escalations` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `escalation_id` | VARCHAR | no | PK |
| `user_id` | VARCHAR | no |  |
| `session_id` | VARCHAR | yes |  |
| `trace_id` | VARCHAR | no |  |
| `triggers` | TEXT | no |  |
| `reason` | TEXT | yes |  |
| `reviewer` | VARCHAR | yes |  |
| `envelope_json` | TEXT | yes |  |
| `created_at` | DATETIME | yes | default utcnow |

### `idempotency_keys` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `key` | VARCHAR | no | PK |
| `user_id` | VARCHAR | no |  |
| `envelope_json` | TEXT | no |  |
| `created_at` | DATETIME | yes | default utcnow |

### `traces` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `trace_id` | VARCHAR | no | PK |
| `user_id` | VARCHAR | yes |  |
| `session_id` | VARCHAR | yes |  |
| `query` | TEXT | yes |  |
| `category` | VARCHAR | yes |  |
| `outcome` | VARCHAR | yes |  |
| `spans_json` | TEXT | yes |  |
| `created_at` | DATETIME | yes | default utcnow |

### `users` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `user_id` | VARCHAR | no | PK |
| `email` | VARCHAR | no | UNIQUE |
| `password_hash` | VARCHAR | no |  |
| `full_name` | VARCHAR | yes |  |
| `role` | VARCHAR | no | default 'analyst' |
| `portfolio_ids` | TEXT | no | default '[]' |
| `status` | VARCHAR | no | default 'active' |
| `created_at` | DATETIME | yes | default utcnow |
| `last_login_at` | DATETIME | yes |  |

### `profile_guidelines` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `guideline_id` | INTEGER | no | PK, autoincrement |
| `user_id` | VARCHAR | no | FK → `users.user_id`, indexed |
| `profile_id` | VARCHAR | no | indexed |
| `use_case` | VARCHAR | no |  |
| `guideline_text` | TEXT | no |  |
| `updated_at` | DATETIME | yes | default utcnow |

UNIQUE (user_id, profile_id, use_case)

### `profiles` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `profile_id` | VARCHAR | no | PK |
| `user_id` | VARCHAR | no | FK → `users.user_id`, indexed |
| `name` | VARCHAR | no |  |
| `created_at` | DATETIME | yes | default utcnow |

### `saved_screens` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `screen_id` | VARCHAR | no | PK |
| `user_id` | VARCHAR | no | FK → `users.user_id` |
| `profile_id` | VARCHAR | no | indexed, default 'default' |
| `name` | VARCHAR | no |  |
| `description` | TEXT | yes |  |
| `definition` | TEXT | no |  |
| `is_public` | BOOLEAN | yes | default False |
| `created_at` | DATETIME | yes | default utcnow |
| `updated_at` | DATETIME | yes | default utcnow |

### `sessions` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `session_id` | VARCHAR | no | PK |
| `user_id` | VARCHAR | no | FK → `users.user_id` |
| `title` | VARCHAR | yes |  |
| `created_at` | DATETIME | yes | default utcnow |
| `expires_at` | DATETIME | yes |  |

### `turns` (finance_auth_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `turn_id` | INTEGER | no | PK, autoincrement |
| `session_id` | VARCHAR | no | FK → `sessions.session_id` |
| `user_id` | VARCHAR | no |  |
| `query` | TEXT | no |  |
| `profile_id` | VARCHAR | no | indexed, default 'default' |
| `outcome` | VARCHAR | no |  |
| `category` | VARCHAR | yes |  |
| `answer` | TEXT | yes |  |
| `envelope_json` | TEXT | yes |  |
| `created_at` | DATETIME | yes | default utcnow |

### `asset_risk_logs` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `risk_id` | INTEGER | no | PK |
| `asset_name` | VARCHAR(150) | yes |  |
| `risk_type` | VARCHAR(100) | yes |  |
| `risk_score` | INTEGER | yes |  |
| `risk_level` | VARCHAR(50) | yes |  |
| `risk_description` | TEXT | yes |  |
| `assessment_date` | DATE | yes |  |
| `escalation_flag` | BOOLEAN | yes | default False |
| `created_at` | DATETIME | yes | default utcnow |

### `equity_universe` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `symbol` | VARCHAR | no | PK |
| `company_name` | VARCHAR | no |  |
| `sector` | VARCHAR | yes |  |
| `industry` | VARCHAR | yes |  |
| `exchange` | VARCHAR | yes |  |
| `market_cap_cr` | NUMERIC | yes |  |
| `is_active` | BOOLEAN | yes | default True |

### `market_indicators` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `indicator_id` | INTEGER | no | PK |
| `indicator_name` | VARCHAR(150) | yes |  |
| `region` | VARCHAR(100) | yes |  |
| `indicator_value` | FLOAT | yes |  |
| `measurement_date` | DATE | yes |  |
| `trend_direction` | VARCHAR(50) | yes |  |
| `created_at` | DATETIME | yes | default utcnow |

### `policy_chunks` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `chunk_id` | VARCHAR | no | PK |
| `doc_id` | VARCHAR | no |  |
| `doc_title` | VARCHAR | no |  |
| `doc_category` | VARCHAR | yes |  |
| `section` | VARCHAR | yes |  |
| `page` | INTEGER | yes |  |
| `chunk_text` | TEXT | no |  |
| `token_count` | INTEGER | yes |  |
| `embedding` | TEXT | yes |  |

### `portfolios` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `portfolio_id` | INTEGER | no | PK |
| `portfolio_name` | VARCHAR(150) | no |  |
| `portfolio_manager` | VARCHAR(150) | yes |  |
| `risk_category` | VARCHAR(50) | yes |  |
| `total_value` | NUMERIC | yes |  |
| `benchmark_index` | VARCHAR(100) | yes |  |
| `created_at` | DATETIME | yes | default utcnow |

### `user_documents` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `doc_id` | VARCHAR | no | PK |
| `owner_id` | VARCHAR | no | indexed |
| `doc_title` | VARCHAR | no |  |
| `filename` | VARCHAR | no |  |
| `category` | VARCHAR | no |  |
| `role` | VARCHAR | no |  |
| `use_case` | VARCHAR | no | default 'all' |
| `profile_id` | VARCHAR | no | indexed, default 'default' |
| `created_at` | DATETIME | yes | default utcnow |

### `equity_fundamentals` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `id` | INTEGER | no | PK, autoincrement |
| `symbol` | VARCHAR | yes | FK → `equity_universe.symbol` |
| `period_end` | DATE | no |  |
| `period_type` | VARCHAR | no |  |
| `pe` | NUMERIC | yes |  |
| `pb` | NUMERIC | yes |  |
| `roe` | NUMERIC | yes |  |
| `roce` | NUMERIC | yes |  |
| `debt_to_equity` | NUMERIC | yes |  |
| `current_ratio` | NUMERIC | yes |  |
| `sales_growth_3y` | NUMERIC | yes |  |
| `profit_growth_3y` | NUMERIC | yes |  |
| `dividend_yield` | NUMERIC | yes |  |
| `promoter_holding` | NUMERIC | yes |  |

UNIQUE (symbol, period_end, period_type)

### `investment_decisions` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `decision_id` | INTEGER | no | PK |
| `portfolio_id` | INTEGER | yes | FK → `portfolios.portfolio_id` |
| `asset_name` | VARCHAR(150) | yes |  |
| `decision_type` | VARCHAR(50) | yes |  |
| `decision_reason` | TEXT | yes |  |
| `risk_assessment_reference` | INTEGER | yes | FK → `asset_risk_logs.risk_id` |
| `decision_date` | DATE | yes |  |
| `approval_status` | VARCHAR(50) | yes |  |
| `created_at` | DATETIME | yes | default utcnow |

### `portfolio_holdings` (finance_risk_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `holding_id` | INTEGER | no | PK |
| `portfolio_id` | INTEGER | yes | FK → `portfolios.portfolio_id` |
| `asset_name` | VARCHAR(150) | yes |  |
| `asset_type` | VARCHAR(100) | yes |  |
| `sector` | VARCHAR(100) | yes |  |
| `allocation_percentage` | FLOAT | yes |  |
| `market_value` | NUMERIC | yes |  |
| `buy_price` | NUMERIC | yes |  |
| `buy_date` | DATE | yes |  |
| `last_updated` | DATE | yes |  |

### `stock_chunks` (finance_stock_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `chunk_id` | VARCHAR | no | PK |
| `doc_id` | VARCHAR | no | indexed |
| `doc_title` | VARCHAR | no |  |
| `doc_category` | VARCHAR | yes |  |
| `section` | VARCHAR | yes |  |
| `page` | INTEGER | yes |  |
| `chunk_text` | TEXT | no |  |
| `token_count` | INTEGER | yes |  |
| `embedding` | TEXT | yes |  |

### `stock_documents` (finance_stock_db)

| Column | Type | Null | Key / default |
|---|---|---|---|
| `doc_id` | VARCHAR | no | PK |
| `owner_id` | VARCHAR | no | indexed |
| `symbol` | VARCHAR | no | indexed |
| `doc_title` | VARCHAR | no |  |
| `filename` | VARCHAR | no |  |
| `kind` | VARCHAR | no | default 'ar' |
| `body` | TEXT | yes |  |
| `profile_id` | VARCHAR | no | indexed, default 'default' |
| `created_at` | DATETIME | yes | default utcnow |

---

## 3. Group Tables by Domain

| Domain | Tables | Purpose |
|---|---|---|
| Identity | `users` | accounts, role, portfolio scope, status |
| Conversation / memory | `sessions`, `turns` | chat history; last turns feed follow-up resolution |
| Personalisation | `profiles`, `profile_guidelines` | analysis profiles and per-use-case guideline overlays for synthesis |
| Screener | `saved_screens`, `equity_universe`, `equity_fundamentals` | equity screens, universe, fundamentals |
| Finance core | `portfolios`, `portfolio_holdings`, `asset_risk_logs`, `market_indicators`, `investment_decisions` | synthetic course data read by SQL templates |
| House RAG corpus | `user_documents`, `policy_chunks` | 7 system policy PDFs + user house PDFs |
| Ticker research | `stock_documents`, `stock_chunks` | annual reports, concalls, presentations, saved research notes |
| Human-in-the-loop | `escalations` | handoff records with triggers and reviewer |
| Observability | `traces`, `audit_log` | per-agent spans, SQL audit |
| API reliability | `idempotency_keys` | replay-safe `POST /api/v1/query` |

---

## 4. Application Flow to Table Mapping

| Flow | Reads | Writes |
|---|---|---|
| Signup / login | `users` | `users` (`last_login_at`) |
| Every authenticated request | `users` | – |
| Ask (`/api/v1/query[/stream]`) | `sessions`, `turns`, `profiles`, `profile_guidelines`, `policy_chunks`, `user_documents`, finance core, `stock_*` | `sessions`, `turns`, `traces`, `audit_log`, `escalations`, `idempotency_keys`, `stock_documents` (note) |
| Upload policy PDF | `user_documents` | `user_documents`, `policy_chunks` |
| Upload ticker filing | `stock_documents` | `stock_documents`, `stock_chunks` |
| Upload portfolio CSV | `portfolios` | `portfolios`, `portfolio_holdings`, `users.portfolio_ids` |
| Screener | `equity_universe`, `equity_fundamentals`, `saved_screens` | `saved_screens` |
| Escalation queue | `escalations` | – |
| Admin traces | `traces` | – |
| Admin reindex | – | `policy_chunks` |
| Readiness probe | `policy_chunks` (counts) | – |

### SQL template → table

| Template | Table(s) | RBAC mode |
|---|---|---|
| `portfolios.by_risk_category`, `.by_manager`, `.by_benchmark`, `.all_in_scope` | portfolios | portfolio_id |
| `holdings.by_portfolio`, `.by_sector`, `.by_allocation_threshold`, `.sector_concentration_by_portfolio`, `.top_by_market_value` | portfolio_holdings | portfolio_id |
| `risk_logs.by_score_threshold`, `.by_asset`, `.by_level`, `.escalation_flagged`, `.latest_by_asset` | asset_risk_logs | asset_via_holdings |
| `market_indicators.latest_by_name_region`, `.by_trend` | market_indicators | none |
| `decisions.by_portfolio`, `.by_approval_status` | investment_decisions | portfolio_id |
| `equities.by_symbol` | equity_universe + equity_fundamentals | none |

---

## 5. Table Dependency Map

```
users ─┬─< sessions ─< turns
       ├─< profiles
       ├─< profile_guidelines
       └─< saved_screens

portfolios ─┬─< portfolio_holdings
            └─< investment_decisions >─ asset_risk_logs

equity_universe ─< equity_fundamentals

user_documents  ··< policy_chunks     (logical, by doc_id)
stock_documents ··< stock_chunks      (logical, by doc_id)

traces ··< escalations, audit_log     (logical, by trace_id)
```

`─<` declared foreign key (one-to-many) · `··<` application-level link.

Seed / reset order (`app/sqlq/seed.py::bootstrap`): users → portfolios → holdings → risk logs → market indicators → decisions → golden extensions → policy chunks → equities.

---

## 6. Important Identifiers

| Column | Meaning |
|---|---|
| `users.portfolio_ids` | JSON list of allowed portfolio ids, or `"ALL"`; source of SQL row-level security for analysts |
| `*.profile_id` | active analysis profile; `default` when none is chosen |
| `turns.envelope_json`, `escalations.envelope_json`, `idempotency_keys.envelope_json` | full `QueryResponse` JSON, so any past answer can be re-rendered or audited |
| `traces.spans_json` | ordered list of `{name, duration_ms, …}` for each agent step |
| `escalations.triggers` | JSON list such as `["E2","E6"]` |
| `audit_log.params_json` | bound slot values of the SQL template run |
| `policy_chunks.doc_id` | system doc slug (e.g. `07_Investment_Risk_Assessment_Framework`) or `udoc_…` |
| `stock_documents.body` | stored JSON envelope when `kind = note` (cached research note) |

---

## 7. Vector Data

| Table | Text column | Vector column | Model | Dims |
|---|---|---|---|---|
| `policy_chunks` | `chunk_text` | `embedding` (TEXT JSON) → `embedding_vec` (vector, generated) | `gemini-embedding-001` | 1536 |
| `stock_chunks` | `chunk_text` | same | same | 1536 |

Chunks are 1200 characters with 180 overlap, one section label per PDF page. Similarity is exact cosine (`<=>`) filtered by allowed `doc_id`; no ANN index is needed at this corpus size. Without pgvector the same score is computed in Python.

---

## 8. Currently Unused / Reserved Columns

| Column | Status |
|---|---|
| `sessions.expires_at` | never written; the JWT `exp` claim (60 min) is the real session limit |
| `saved_screens.is_public` | stored; sharing UI not built |
| `policy_chunks.token_count`, `stock_chunks.token_count` | word count stored for diagnostics |
| `user_documents.role` | derived from use case; kept for citation metadata |

No table is unused: every table above is read or written by at least one route.

---

## 9. Source References

| Topic | File |
|---|---|
| ORM models | `capstone/app/models.py` |
| Engines, column upgrades, pgvector | `capstone/app/core/db.py` |
| SQL templates | `capstone/app/sqlq/templates.py` |
| Executor + audit | `capstone/app/sqlq/executor.py` |
| Seed | `capstone/app/sqlq/seed.py` |
| CSV import | `capstone/app/sqlq/import_portfolio.py` |
| Retrieval + ingestion | `capstone/app/rag.py` |
