# Production — Product & Scope

## Vision
A production Finance Risk & Investment Intelligence platform where **the user (or their firm) owns**:
- Current portfolio and positions
- Investment strategy / IPS / risk policy documents
- Risk and valuation **metrics** at stock and portfolio level

The platform stores, versions, retrieves, and reasons over that data. Market data is **licensed real-time (or near-real-time)** enrichment — never scraped and never invented by the LLM.

## In scope
- User workspace (portfolios, positions, documents, metric definitions/values, watchlists, screens)
- Org tenancy and RBAC
- Real-time quote/fundamentals **and** licensed news providers (adapter pattern)
- Per-query switch: **Documents only** vs **Documents + current** (`evidence_mode`)
- Same safety posture: citations, escalation, no investment advice
- Cloud deployment, secret manager, observability

## Out of scope
- golden-set grading and course synthetic seed as the system of record
- Providing investment recommendations
- Using Screener.in or other vendors’ data without a contract

## Separation rule
No shared runtime flag with the capstone submission. Production is planned and shipped **separately**.
