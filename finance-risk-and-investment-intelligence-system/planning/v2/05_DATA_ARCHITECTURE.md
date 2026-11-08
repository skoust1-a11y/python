# Data Architecture (v2)

---

## 1. Database split (ADR-020)

| DB | Connection env | Write roles |
|---|---|---|
| `finance_auth_db` | `AUTH_DATABASE_URL` | app auth service |
| `finance_risk_db` | `DATABASE_URL` (RO for queries) | migrate/seed/ingest jobs |

Local: one Postgres instance, two databases.

---

## 2. Finance DB — course tables

| Table | Purpose | Capstone rows |
|---|---|---|
| `portfolios` | Portfolio registry | 20 |
| `portfolio_holdings` | Positions | 120 |
| `asset_risk_logs` | Risk scores / flags | 150 |
| `market_indicators` | Macro indicators | 80 |
| `investment_decisions` | Decision history | 100 |
| `policy_chunks` | RAG chunks + embeddings | ~400–900 |
| `equity_universe` | Screening symbols | 500–2000 (synthetic) |
| `equity_fundamentals` | Screening ratios | seeded |

Schema source: `../capstone/capstone_finance_risk_and_investment_dataset.md`.

---

## 3. Auth DB

| Table | Purpose |
|---|---|
| `users` | signup/login, role, portfolio_ids |
| `sessions` | session_id, user, TTL |
| `turns` | last N turns for memory |
| `saved_screens` | screen JSON definitions |

---

## 4. Unstructured corpus

7 PDFs under `Documents/` → ingest → `policy_chunks` with `{doc_id, section, page, category}`.

**Manual QA (GATE-2 blocker):** limits tables in docs 02, 03, 06, 07 extract legibly.

---

## 5. Golden dataset

| File | Count | Purpose |
|---|---|---|
| `eval/golden/golden_queries.jsonl` | 50 | Graded specification |
| `eval/golden/attack_suite.jsonl` | ≥20 | Safety |
| `eval/golden/negative_controls.jsonl` | ≥10 | Refusal / no-data |
| `eval/golden/screen_queries.jsonl` | 10 (optional) | Screening |

Label fields: category, risk_level, retrieval_mode, escalation_expected, ground_truth refs.

---

## 6. Risk semantics (authoritative)

```
risk_score ∈ [0,100]
Low:    score < 30
Medium: 30 ≤ score ≤ 69
High:   score ≥ 70
escalation_flag = TRUE iff score > 80
```

---

## 7. Data lifecycle

| Event | Action |
|---|---|
| Schema change | Versioned migration SQL; never migrate-on-boot in prod |
| PDF update | Re-ingest job; bump chunk version in eval header |
| Seed regen | Fixed seed for reproducible golden comparisons |
