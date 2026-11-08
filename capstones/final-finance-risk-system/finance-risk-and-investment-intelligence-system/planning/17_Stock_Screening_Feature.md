# 17 — Stock Screening Feature
**Product add-on — inspired by [Screener.in](https://www.screener.in/) screen builder ([Create screen](https://www.screener.in/screen/new/))**

UX/capability reference only. **Do not scrape Screener data, copy their UI, or reuse their query language proprietary assets.** Capstone uses **synthetic** (or separately licensed) fundamentals.

---

## 1. Why this feature

Analysts already ask policy and portfolio questions. They also need to **filter a stock universe** by fundamentals (e.g. ROE > 15, debt/equity < 0.5, market cap band) the way Screener’s “Create a stock screen” does — run conditions on years of financial fields and get a ranked table.

This system adds that as a first-class module: **Screen Builder + Screen Runner + optional NL ? screen via the agent router**.

---

## 2. Product scope

### In scope
| Capability | Description |
|---|---|
| Equity universe | Synthetic Indian/global-style stock master + fundamentals (yearly/quarterly ratios) |
| Visual screen builder | Add filters (field, op, value), AND/OR groups, sort, limit |
| Saved screens | Per-user screens in **auth DB** (`saved_screens`) |
| Run screen | Execute against **finance DB** ? tabular results + export CSV |
| NL screen | “Show IT stocks with ROE > 20 and PE < 25” ? structured screen JSON ? same runner |
| Citations | Every agent-built screen cites `SQL: equity_* · query_id=screen.run` |
| Non-advice | Results are **filtered data**, never “buy/sell” recommendations |

### Out of scope (v1)
- Live exchange feeds / scraping Screener or Bhavcopy without a licensed source
- Backtest portfolio construction from a screen
- Social sharing of screens, paid premium tiers
- Copying Screener’s exact query dialect or UI chrome

---

## 3. Data (lives in `finance_risk_db`, not auth / not vectors)

New tables (synthetic seed; extend generator):

```sql
-- Master
CREATE TABLE equity_universe (
  symbol          TEXT PRIMARY KEY,
  company_name    TEXT NOT NULL,
  sector          TEXT,
  industry        TEXT,
  exchange        TEXT,              -- e.g. NSE, BSE, NYSE (synthetic)
  market_cap_cr   NUMERIC,           -- crores or millions — document unit in seed
  is_active       BOOLEAN DEFAULT TRUE
);

-- Point-in-time fundamentals (one row per symbol × period)
CREATE TABLE equity_fundamentals (
  id              SERIAL PRIMARY KEY,
  symbol          TEXT REFERENCES equity_universe(symbol),
  period_end      DATE NOT NULL,
  period_type     TEXT CHECK (period_type IN ('FY','Q')),
  pe              NUMERIC,
  pb              NUMERIC,
  roe             NUMERIC,           -- percent
  roce            NUMERIC,
  debt_to_equity  NUMERIC,
  current_ratio   NUMERIC,
  sales_growth_3y NUMERIC,
  profit_growth_3y NUMERIC,
  dividend_yield  NUMERIC,
  promoter_holding NUMERIC,
  UNIQUE (symbol, period_end, period_type)
);

CREATE INDEX ON equity_fundamentals (period_type, period_end);
CREATE INDEX ON equity_universe (sector, market_cap_cr);
```

**pgvector stays on `policy_chunks` only.** Screening is pure SQL (templated), not RAG.

Saved screens (user-owned) ? **`finance_auth_db`**:

```sql
CREATE TABLE saved_screens (
  screen_id     TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL REFERENCES users(user_id),
  name          TEXT NOT NULL,
  description   TEXT,
  definition    JSONB NOT NULL,      -- ScreenDefinition below
  is_public     BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);
```

---

## 4. Screen definition (JSON contract)

```jsonc
{
  "version": 1,
  "logic": "and",                    // and | or  (top-level)
  "filters": [
    { "field": "roe", "op": "gt", "value": 15 },
    { "field": "debt_to_equity", "op": "lt", "value": 0.5 },
    { "field": "sector", "op": "in", "value": ["Technology", "Healthcare"] },
    { "field": "market_cap_cr", "op": "between", "value": [500, 50000] }
  ],
  "sort": [{ "field": "roe", "dir": "desc" }],
  "limit": 50,
  "period": { "type": "FY", "as_of": "latest" }
}
```

**Allowed fields (whitelist):** `pe, pb, roe, roce, debt_to_equity, current_ratio, sales_growth_3y, profit_growth_3y, dividend_yield, promoter_holding, market_cap_cr, sector, industry, exchange, symbol`.

**Allowed ops:** `eq, ne, gt, gte, lt, lte, between, in, not_in, is_null, not_null`.

Runner builds **only** parameterized SQL from this whitelist (same discipline as ADR-005). No free-form SQL from the browser or the LLM.

---

## 5. API (`/api/v1/screens`)

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` | `/api/v1/screens/fields` | Field catalogue + types + ops (for builder UI) | required |
| `POST` | `/api/v1/screens/run` | Execute `ScreenDefinition` ? rows | required |
| `POST` | `/api/v1/screens/from-nl` | NL ? ScreenDefinition (agent) + optional auto-run | required |
| `GET` | `/api/v1/screens` | List my saved screens | required |
| `POST` | `/api/v1/screens` | Save screen | required |
| `GET` | `/api/v1/screens/{id}` | Get definition | owner/admin |
| `PUT` | `/api/v1/screens/{id}` | Update | owner |
| `DELETE` | `/api/v1/screens/{id}` | Delete | owner |
| `GET` | `/api/v1/screens/{id}/export.csv` | CSV of last-run or re-run | owner |

### `POST /screens/run` response (shape)
```jsonc
{
  "trace_id": "trc_...",
  "row_count": 23,
  "columns": ["symbol", "company_name", "sector", "roe", "pe", "debt_to_equity", "market_cap_cr"],
  "rows": [ { "symbol": "SYNTECH", "roe": 22.1, "pe": 18.4, ... } ],
  "definition_echo": { "...": "normalized screen" },
  "citations": [
    { "type": "sql", "tables": ["equity_universe", "equity_fundamentals"], "query_id": "screen.run", "rows": 23 }
  ],
  "disclaimer": "Educational/synthetic data. Not investment advice."
}
```

RBAC: any authenticated role can run screens on the **shared synthetic universe** (public market-style data). Saved screens are per-user. Portfolio holdings remain scoped via existing executor rules — screens do **not** bypass portfolio RBAC.

---

## 6. Agent integration

| Path | When |
|---|---|
| **UI builder** | User builds filters ? `POST /screens/run` (no LLM) |
| **C6 NL Screen** (extension category) | Router detects screening intent ? `ScreenAgent` emits ScreenDefinition JSON ? validate ? runner |

**Router signals:** “screen”, “filter stocks”, “stocks with”, “ROE”, “PE below”, “high promoter holding”, “screener”, “list companies where”.

**Guardrails:**
- Refuse buy/sell/allocate wording ? non-advice + optional escalation if override intent
- Reject unknown fields/ops at validation (before SQL)
- Cap `limit` (default 50, max 200)
- NL path still tool-less synthesis for explanation; numeric rows only from runner

Add optional golden probes (not part of the mandated 50): 10 NL?screen cases in `eval/golden/screen_queries.jsonl`.

---

## 7. Frontend (Sprint 9+ — React, auth-gated)

User must be logged in to reach `/app/screens` (`19_React_Frontend_Plan.md`).

Inspired by Screener’s create-screen flow ([screen/new](https://www.screener.in/screen/new/)):

1. **Screens** nav item  
2. **New screen** — field picker, operator, value; add/remove rows; AND/OR; sort; Run  
3. **Results table** — sortable columns, CSV download  
4. **Save / name screen**  
5. **Ask in natural language** tab ? calls `/screens/from-nl`  

Keep our own visual language (existing design system). Do not clone Screener’s branding.

---

## 8. Implementation sketch

```text
app/
  screens/
    fields.py          # whitelist catalogue
    validate.py        # ScreenDefinition ? ok / errors
    sql_builder.py     # definition ? parameterized SQL only
    runner.py          # execute on finance_engine
    nl_agent.py        # LLM ? JSON definition (Sprint 6+)
  api/routes_screens.py
```

Sprint suggestion:
| Sprint | Work |
|---|---|
| 4 | Tables + seed + `screen.run` template + `POST /screens/run` (no NL) |
| 5–6 | Field catalogue API, validation hardening, NL agent |
| 8 | `saved_screens` in auth DB |
| 9 | Builder UI + results + save |

---

## 9. Success criteria

- Run a multi-filter screen in ?2s p95 on synthetic universe (~500–2000 symbols)
- 100% of executed screens use whitelist SQL (zero string-concat field names from client)
- NL?screen field accuracy ?90% on screen golden probes
- Every response includes non-advice disclaimer + SQL citation
- No dependency on Screener.in APIs or HTML

---

## 10. Disclaimer

Synthetic/educational equity data. Screening output is **not** a recommendation to buy, sell, or hold any security. Inspired by the screening *workflow* popularized by tools such as [Screener.in](https://www.screener.in/); implementation and data are independent.
