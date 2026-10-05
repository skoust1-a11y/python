# Capstone

Local **Postgres** (cloud later). Three separate databases on your machine:

| Database | Role |
|---|---|
| `frii_auth_db` | users, sessions, turns, screens, traces |
| `frii_risk_db` | course finance tables, policy chunks, equities |
| `frii_stock_db` | stock documents / chunks |

## Setup

Postgres must already be running on `localhost:5432`. Create the databases once:

```bash
psql -h localhost -d postgres -c "CREATE DATABASE frii_auth_db;"
psql -h localhost -d postgres -c "CREATE DATABASE frii_risk_db;"
psql -h localhost -d postgres -c "CREATE DATABASE frii_stock_db;"
```

```bash
cd capstone
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set the DB user to your OS user if needed
python -m app.sqlq.seed --reset
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:5173 — login first (`analyst@local` / `Password123`). Vite proxies `/api` to the API on port 8000.

Seeded logins (password `Password123`): `admin@local`, `analyst@local` (portfolios 1–2), `risk@local`, `compliance@local`.

## Retrieval

Hybrid search: pgvector cosine (computed in Postgres from a generated `embedding_vec` column) fused with keyword overlap by weighted reciprocal rank fusion (`RETRIEVAL_VECTOR_WEIGHT`, `RETRIEVAL_LEXICAL_WEIGHT`, `RETRIEVAL_RRF_K`). Without the `vector` extension it falls back to Python cosine.

## Checks

```bash
pytest                                   # backend, coverage gate 85%
python -m eval.run --suite all --judge   # 16 SLOs; --judge fills SLO 7 via the configured LLM
python -m eval.human_sheet               # eval/reports/human_eval.xlsx: 60 policy + 50 golden rows, 0-100 LLM judge scores
cd frontend && npm test                  # Vitest
```

Human review: fill the `Human_*`, `Reviewer` and `Review_Notes` columns in `eval/reports/human_eval.xlsx`, then run `python -m eval.human_sheet --rescore` (no pipeline calls). The `Agreement` sheet compares LLM and human scores, and reviewer input is kept across re-runs. `Field_Reference` explains every column.

`CURRENT_FACTORS_ENABLED=true` turns on **Documents + current**. That path still runs corpus + SQL, then adds live Yahoo quotes/news (NSE/BSE via `.NS`/`.BO`) and Chittorgarh IPO/GMP when the question mentions them. Golden-set eval stays on `corpus`. Set the flag to false to get 409 again.
