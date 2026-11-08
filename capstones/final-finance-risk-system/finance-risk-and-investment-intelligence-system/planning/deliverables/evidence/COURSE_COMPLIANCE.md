# Course pack compliance checklist

Source of truth: `Project-3-Finance Risk & Investment Intelligence System/`

Checked: 7 September 2026

## Course README deliverables

| Required | Status | Where |
|---|---|---|
| Working AI finance intelligence system | Pass | `capstone/` FastAPI + React |
| Multi-agent orchestration | Pass | `capstone/app/graph.py` + prompts |
| Financial knowledge retrieval (RAG) | Pass | 7 PDFs ingested; `app/rag.py` |
| Structured financial data integration | Pass | `finance_risk_db` 5 core tables |
| Architecture / design documentation | Pass | `planning/` + `planning/v2/` + diagrams |

## Core requirements

| Requirement | Status |
|---|---|
| Intelligent query handling | Pass |
| Query routing to risk / retrieval / market / portfolio agents | Pass |
| Multi-agent collaboration + synthesis | Pass |
| Source attribution | Pass (SLO-10) |
| Human escalation | Pass (SLO-12, C5 + E1–E8) |

## Dataset package

| Mandate | Status |
|---|---|
| 7 policy PDFs (byte-identical to course pack) | Pass |
| Tables: portfolios, portfolio_holdings, asset_risk_logs, market_indicators, investment_decisions | Pass |
| Starter sample rows extended, not replaced | Pass (`app/sqlq/seed.py`) |
| Scaled synthetic data generator | Pass — `generate_capstone_sql_data.py` (+ `.sql` original) and seed |
| Golden 50 with 15/10/10/10/5 | Pass |
| Labels: Query Type, Risk Level, Retrieval Mode, Escalation | Pass |
| All example query strings in golden set | Pass |

## High-risk multi-agent scenarios (README)

| Scenario | Covered by |
|---|---|
| Portfolio risk in market volatility | C3/C4 golden + market_data agent |
| Performance vs benchmarks | C1/C2 docs + holdings templates |
| Sectors under regulatory scrutiny | C1/C3 regulatory docs |
| Unusual risk patterns in history | risk_logs + decisions templates |
| Alignment with risk policies | C3 hybrid golden |

## Mandatory disclaimer

Synthetic/educational data. Not investment advice.
