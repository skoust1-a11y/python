# Executive Summary (v2)

## Problem

Financial teams answer policy-and-data questions by manually cross-reading **7 policy PDFs** and **5 SQL datasets**. Answers are slow, inconsistent, and rarely cite sources. High-risk cases (`escalation_flag`, override requests) are easy to miss.

## Solution

An **AI-assisted intelligence platform** (capstone scope):

- **Understands** query intent (5 categories)
- **Retrieves** policy text (hybrid RAG) and portfolio/risk data (parameterized SQL)
- **Reasons** via a **LangGraph** multi-agent workflow
- **Responds** with mandatory citations, disclaimers, and deterministic escalation
- **Authenticates** users (signup/login); **React** UI gates all features behind login

## Out of scope (capstone)

- Live market feeds, user-imported production portfolios → `../production/`
- Investment advice, trade execution, fine-tuning

## Success (capstone)

| Gate | When | Criterion |
|---|---|---|
| GATE-1 | End Sprint 3 | **SIGNED 29 Aug 2026** — v2 plan + frozen API (`GATE_1_SIGNOFF.md`) |
| GATE-2 | Sprint 4 | Prototype 1: C1/C2 + C5 refusal; baseline eval |
| GATE-3 | Sprint 6 | Prototype 2: full multi-agent C3/C4 |
| GATE-4 | Sprint 8 | Auth, RBAC, load, prod engineering checklist |
| GATE-5 | Sprint 9 | Prototype 3: React E2E |
| GATE-6 | Sprint 10 | Final SLO report; go-live dry-run |

**Hard SLOs (zero tolerance):** Source attribution 100%, Escalation recall 100%, Guardrail effectiveness 100%, RBAC violations 0.

## Stack (fixed)

FastAPI · LangGraph · PostgreSQL 16 (`finance_auth_db` + `finance_risk_db` + pgvector) · OpenAI-compatible LLM · React (Vite) · structlog + OTel · in-repo eval harness.

## Documents to read first

1. `02_REQUIREMENTS_CATALOG.md`
2. `03_ARCHITECTURE.md`
3. `07_DELIVERY_PLAN.md`
4. `MASTER_PROMPT_v2.md`
