# ADR Index (v2)

Full text: [`../07_ADR.md`](../07_ADR.md). Do not duplicate — link only.

| ADR | Decision | v2 relevance |
|---|---|---|
| 001 | LangGraph orchestration | `03_ARCHITECTURE` |
| 002 | pgvector in finance DB | `05_DATA_ARCHITECTURE` |
| 003 | Postgres read-only query role | `04_SECURITY`, `05` |
| 004 | OpenAI-compatible tiered LLM | Runtime only |
| 005 | Named SQL templates | FR-004 |
| 006 | Session memory in auth DB | FR-013 |
| 007 | Deterministic guardrails | `04_SECURITY` |
| 008 | Typed citations | SLO-10 |
| 009 | structlog + OTel + Prometheus | `10_OPERATIONS` |
| 010 | Tiered latency budgets | `08_TEST`, NFR-001–004 |
| 011 | React frontend Sprint 5+ | `09_FRONTEND` |
| 012 | In-repo eval harness | `08_TEST` |
| 013 | Hybrid retrieval | FR-003 |
| 014 | RBAC at SQL executor | SR-005 |
| 015–018 | Cloud-portable runtime | `10_OPERATIONS` |
| 019 | Signup/login | FR-009 |
| 020 | Auth DB ≠ finance DB | `05_DATA` |
| 021 | Stock screening | FR-011 |
| 022 | Capstone ≠ production plans | `01_EXECUTIVE` |
| 023 | Auth-first React routes | FR-010 |
| 024 | Opus 4.5 / Codex High for agent work | `00_STANDARDS` |

New decisions: add ADR in `07`, then one row here.
