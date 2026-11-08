# Production — User-Owned Data Model

**Everything below is provided by the user (upload, UI, broker sync, or their risk engine).** The LLM never writes these rows.

## Auth (separate DB)
`finance_auth_db`: users, sessions, org membership, saved_screens metadata (or screens in workspace DB).

## Workspace DB (separate from vector index of firm policies as needed)
```
orgs, org_members
user_portfolios          # books the user maintains
user_positions           # symbol, qty, cost, as_of
user_lots                # optional
user_strategies          # links to uploaded docs
user_documents           # files → org-scoped embeddings
user_metric_definitions  # risk/valuation metric keys (stock | portfolio)
user_metric_values       # values + as_of + source=user|calc
user_watchlists
```

## What user supplies vs market
| User supplies | Provider may supply |
|---|---|
| Holdings, lots, cost basis | Last/bid/ask, volume |
| Strategy & risk PDFs | Published fundamentals snapshots |
| Custom risk scores, limits, VaR, valuation marks | — |
| Metric definitions | — |

If a metric is missing → **insufficient evidence** / prompt to upload — never hallucinate.
