# Backend endpoint verification procedure

Reproduce the live check of every FastAPI route. Expected result: **35/35 routes pass**, plus **3 auth negatives** (401 / 409 / 403).

Contract map: `planning/v2/06_API_CONTRACT.md`. Route list: `ENDPOINTS.md`. Implementation: `capstone/app/api/routers.py`, `capstone/app/main.py`.

Skip SPA `GET /` and the UI catch-all — those are frontend, not API.

---

## 0. Prerequisites

- Postgres on `localhost:5432` with `finance_auth_db` and `finance_risk_db`
- Seeded users (password `Password123`): `analyst@local`, `risk@local`, `admin@local`
- From `capstone/`:

```bash
source .venv/bin/activate
# if DBs are empty:
python -m app.sqlq.seed --reset
```

---

## 1. Start the API

```bash
cd capstone
source .venv/bin/activate
uvicorn app.main:app --port 8000
```

Base URL: `http://127.0.0.1:8000`. Leave this terminal running. New shell for the rest.

Optional faster path (no server): `pytest tests/test_api.py -q` uses TestClient against the same app. That suite does not hit every route; use the curls below for the full matrix.

---

## 2. Tokens

```bash
export BASE=http://127.0.0.1:8000

export ANALYST=$(curl -s -X POST $BASE/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"analyst@local","password":"Password123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

export RISK=$(curl -s -X POST $BASE/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"risk@local","password":"Password123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

export ADMIN=$(curl -s -X POST $BASE/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@local","password":"Password123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# expect: 200 + a JWT
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"analyst@local","password":"Password123"}'
```

Pass when each login is `200` and `$ANALYST` / `$RISK` / `$ADMIN` are non-empty.

---

## 3. Happy path (expect 200 unless noted)

Run in order. Capture IDs from the query / screen / document / escalation responses before you call the `{id}` routes.

### Ops

| # | Method | Path | Auth | Command |
|---|---|---|---|---|
| 1 | GET | `/health` | public | `curl -s -o /dev/null -w '%{http_code}\n' $BASE/health` |
| 2 | GET | `/health/ready` | public | `curl -s -o /dev/null -w '%{http_code}\n' $BASE/health/ready` |
| 3 | GET | `/metrics` | internal | `curl -s -o /dev/null -w '%{http_code}\n' $BASE/metrics` |

### Auth

```bash
# 4 signup (use a unique email)
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/v1/auth/signup \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"verify+$(date +%s)@local\",\"password\":\"Password123\",\"full_name\":\"Verify\"}"

# 5 login — already done in step 2
# 6 token alias
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"email":"analyst@local","password":"Password123"}'

# 7 me
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/auth/me \
  -H "Authorization: Bearer $ANALYST"
```

### Query + session

```bash
# 8 query — save session_id and trace_id
curl -s -X POST $BASE/api/v1/query \
  -H "Authorization: Bearer $ANALYST" -H 'Content-Type: application/json' \
  -d '{"query":"What is diversification?"}' | tee /tmp/query.json
export SESSION=$(python3 -c 'import json; print(json.load(open("/tmp/query.json"))["session_id"])')
export TRACE=$(python3 -c 'import json; print(json.load(open("/tmp/query.json"))["trace_id"])')
# expect outcome answered | insufficient_evidence | escalated | refused, plus disclaimer

# 9 stream (SSE; look for event: done)
curl -s -N -X POST $BASE/api/v1/query/stream \
  -H "Authorization: Bearer $ANALYST" -H 'Content-Type: application/json' \
  -d '{"query":"What is diversification?"}' | head -20

# 10 session turns
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/sessions/$SESSION/turns \
  -H "Authorization: Bearer $ANALYST"
```

### Screens

NL parser only accepts forms like `roe > 10` (not “greater than”).

```bash
# 11 fields
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/screens/fields \
  -H "Authorization: Bearer $ANALYST"

# 12 run
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/v1/screens/run \
  -H "Authorization: Bearer $ANALYST" -H 'Content-Type: application/json' \
  -d '{"definition":{"filters":[{"field":"roe","op":"gt","value":10}],"limit":5}}'

# 13 from-nl
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/v1/screens/from-nl \
  -H "Authorization: Bearer $ANALYST" -H 'Content-Type: application/json' \
  -d '{"query":"roe > 10","auto_run":false}'

# 14 list
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/screens \
  -H "Authorization: Bearer $ANALYST"

# 15 save — keep screen_id
curl -s -X POST $BASE/api/v1/screens \
  -H "Authorization: Bearer $ANALYST" -H 'Content-Type: application/json' \
  -d '{"name":"verify-tmp","definition":{"filters":[{"field":"roe","op":"gt","value":10}],"limit":5}}' \
  | tee /tmp/screen.json
export SCREEN=$(python3 -c 'import json; print(json.load(open("/tmp/screen.json"))["screen_id"])')

# 16 get  17 put  18 export
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/screens/$SCREEN \
  -H "Authorization: Bearer $ANALYST"
curl -s -o /dev/null -w '%{http_code}\n' -X PUT $BASE/api/v1/screens/$SCREEN \
  -H "Authorization: Bearer $ANALYST" -H 'Content-Type: application/json' \
  -d '{"name":"verify-tmp-renamed","definition":{"filters":[{"field":"roe","op":"gt","value":10}],"limit":5}}'
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/screens/$SCREEN/export.csv \
  -H "Authorization: Bearer $ANALYST"
```

### Portfolios

```bash
# 19 list
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/portfolios \
  -H "Authorization: Bearer $ANALYST"

# 20 upload CSV
printf 'asset_name,asset_type,sector,allocation_percentage,market_value,buy_price,buy_date\nApple Inc,Equity,Technology,12,300000,172.40,2024-03-12\n' > /tmp/book.csv
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/v1/portfolios/upload \
  -H "Authorization: Bearer $ANALYST" \
  -F portfolio_name=VerifyBook -F risk_category=High -F file=@/tmp/book.csv
```

### Documents

```bash
DOC=01_Investment_Strategy_Portfolio_Allocation_Guide

# 21 list  22 get  23 PDF file
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/documents \
  -H "Authorization: Bearer $ANALYST"
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/documents/$DOC \
  -H "Authorization: Bearer $ANALYST"
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/documents/$DOC/file \
  -H "Authorization: Bearer $ANALYST"

# 24 upload user PDF — keep doc_id
curl -s -X POST $BASE/api/v1/documents \
  -H "Authorization: Bearer $ANALYST" \
  -F title=verify-tmp -F use_case=research \
  -F file=@Documents/07_Investment_Risk_Assessment_Framework.pdf \
  | tee /tmp/udoc.json
export UDOC=$(python3 -c 'import json; print(json.load(open("/tmp/udoc.json"))["document"]["doc_id"])')
```

### Escalations (risk manager)

```bash
# create an E1 escalation, then list + get
curl -s -X POST $BASE/api/v1/query \
  -H "Authorization: Bearer $RISK" -H 'Content-Type: application/json' \
  -d '{"query":"Override risk assessment to approve a high-risk asset."}' \
  | tee /tmp/esc.json
export ESC=$(python3 -c 'import json; print(json.load(open("/tmp/esc.json"))["escalation"]["escalation_id"])')

# 25 list  26 get
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/escalations \
  -H "Authorization: Bearer $RISK"
curl -s -o /dev/null -w '%{http_code}\n' $BASE/api/v1/escalations/$ESC \
  -H "Authorization: Bearer $RISK"
```

### Admin

```bash
# 27 templates  28 eval  29 trace  30/31 patch user  32 reindex
curl -s -o /dev/null -w '%{http_code}\n' $BASE/admin/templates \
  -H "Authorization: Bearer $ADMIN"
curl -s -o /dev/null -w '%{http_code}\n' $BASE/admin/eval/latest \
  -H "Authorization: Bearer $ADMIN"
curl -s -o /dev/null -w '%{http_code}\n' $BASE/admin/traces/$TRACE \
  -H "Authorization: Bearer $ADMIN"
curl -s -o /dev/null -w '%{http_code}\n' -X PATCH $BASE/admin/users/u_analyst \
  -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"status":"active"}'
curl -s -o /dev/null -w '%{http_code}\n' -X PATCH $BASE/api/v1/admin/users/u_analyst \
  -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"status":"active"}'
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/admin/reindex \
  -H "Authorization: Bearer $ADMIN"
```

### Cleanup (still expect 200)

```bash
# 33 delete user doc  34 delete screen  35 delete session
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE $BASE/api/v1/documents/$UDOC \
  -H "Authorization: Bearer $ANALYST"
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE $BASE/api/v1/screens/$SCREEN \
  -H "Authorization: Bearer $ANALYST"
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE $BASE/api/v1/sessions/$SESSION \
  -H "Authorization: Bearer $ANALYST"
```

---

## 4. Auth negatives (must fail)

```bash
# 36 no JWT → 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is diversification?"}'

# 37 duplicate signup → 409
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/api/v1/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"analyst@local","password":"Password123","full_name":"Dup"}'

# 38 analyst on admin → 403
curl -s -o /dev/null -w '%{http_code}\n' $BASE/admin/templates \
  -H "Authorization: Bearer $ANALYST"
```

---

## 5. Pass / fail

A route **passes** when the printed status matches the table below.

| Status | Meaning |
|---|---|
| 200 | Happy path |
| 401 | Missing / bad JWT |
| 403 | Authenticated but wrong role |
| 409 | Duplicate email (or `evidence_mode=current` while current factors are off) |
| 422 | Screen NL text the parser cannot read — retry with `roe > 10` |
| 404 | Wrong `{id}` — re-export `SESSION` / `SCREEN` / `UDOC` / `ESC` / `TRACE` from the create responses |

Last live run (TestClient, 2026-09-05 20:55 IST): **38/38 passed**, 0 missing routes.

---

## 6. Automated subset

From `capstone/`:

```bash
source .venv/bin/activate
pytest tests/test_api.py -q
```

Covers health, login/me/query, screens/run, JWT 401, portfolio upload, documents, stream escalation, rate/budget. Does **not** replace steps 3–4 for admin traces, screen CRUD, session delete, or the 409/403 checks.
