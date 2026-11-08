# Capstone — Hard Scope

## In scope
- Multi-agent RAG + SQL on **course** documents and **seeded** finance tables
- Golden set of 50 queries + mandated SLOs
- **React** frontend: login/signup first; protected routes for all features (ADR-023, `../19_React_Frontend_Plan.md`)
- Signup / login / RBAC (auth DB separate from vector DB)
- Synthetic stock screening (`17`)
- Prod-**grade engineering** for the capstone app (containers, observability, cloud-**ready** shape) — still on synthetic data

## Out of scope (belongs only in `planning/production/`)
- Real-time market data providers
- User-imported portfolios, strategies, custom risk/valuation matrices as the system of record
- Broker sync, org multi-tenant SaaS, paid data licenses
- `APP_MODE=production` / workspace APIs

## Non-goals (both tracks, but enforced here)
- No investment advice
- No scraping Screener.in or other third-party UIs/data
