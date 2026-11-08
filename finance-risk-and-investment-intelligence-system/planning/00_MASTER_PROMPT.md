# 00 — MASTER PROMPT (Reusable)

Paste this into Claude Opus / Cursor Agent to execute the **Finance Risk & Investment Intelligence System** capstone after Sprint 1—3 planning is signed off. It is deliberately self-contained: it names the planning docs, the non-negotiables, and the sprint order.

---

## THE PROMPT — copy from here

````
You are a senior AI systems engineer building the **Finance Risk & Investment Intelligence System**,
an Agentic AI capstone. You are implementing an already-approved design. Do not redesign;
read the planning docs and build what they specify.
## AI AGENT MODEL (mandatory)
Use **Claude Opus 4.5** (preferred) or **Codex High** in Cursor for this work.
See `planning/20_AI_Agent_Model_Policy.md`. Do not use fast/small models for architecture, safety, or multi-file implementation.
Confirm at start: "Using Opus 4.5 / Codex High per doc 20."

## PROJECT ROOT (capstone code only)
/Users/skoust/Documents/Python agentic ai/course 5/capstone project/Finance_Risk_&_Investment_Intelligence_System/capstone/

## BEFORE YOU WRITE ANY CODE — read these planning docs (in planning/)
| Read this | To learn |
|---|---|
| `planning/01_Project_Approach.md` | scope, phasing, sprint-to-task map, risks |
| `planning/02_Use_Case_and_Success_Definition.md` | personas, use cases, what "done" means |
| `planning/06_High_Level_Architecture.md` | layers, agent topology, mermaid diagrams |
| `planning/07_ADR.md` | **binding** technology decisions (ADR-001..ADR-012) |
| `planning/09_Detailed_Use_Case_and_SLO.md` | 16 SLOs + measurement methods |
| `planning/10_Detailed_Solution_Design.md` | agent contracts, state schema, routing logic, error handling |
| `planning/11_Query_Categories.md` | 5 query categories + routing rules + labels |
| `planning/12_Evaluation_Dataset_and_Test_Strategy.md` | golden set format, test levels, pass gates |
| `planning/13_Prompt_Engineering_Framework.md` | exact system prompts, citation format, refusal templates |
| `planning/14_FastAPI_Service_Setup_Plan.md` | API contract, schemas, folder layout |
| `planning/17_Stock_Screening_Feature.md` | Screener-like stock screens (ADR-021) |
| `planning/capstone/` | Capstone-only entrypoint |
| `planning/production/` | Separate production plan — do not mix |
| `planning/05_Project_Setup_Readiness.md` | repo layout, env vars, deps, DB/vector bootstrap |

If a planning doc conflicts with your instinct, the planning doc wins. If two planning docs
conflict, `07_ADR.md` wins and you must flag the conflict to the user.
Also read `planning/16_Production_and_Cloud_Readiness.md` and ADR-015—018: build **prod-grade and
cloud-portable from Sprint 4** (stateless, env config, one image, CorpusStore seam). Do not invent
a localhost-only design to "add cloud later".

## DOMAIN — do not substitute generic RAG boilerplate
- Unstructured corpus: **7 PDFs** in `Documents/`
  01 Investment Strategy & Portfolio Allocation Guide, 02 Risk Management & Exposure Policy,
  03 Regulatory Compliance & Financial Governance Policy, 04 Market Analysis & Investment Research Guide,
  05 Portfolio Monitoring & Performance Evaluation Guide, 06 Basel III Risk Management Summary,
  07 Investment Risk Assessment Framework.
- Auth store: PostgreSQL db **`finance_auth_db`** — `users`, `sessions`, `turns` (ADR-020; **no** vectors).
- Structured corpus: PostgreSQL db **`finance_risk_db`**, 5 tables + `policy_chunks` —
  `portfolios`, `portfolio_holdings`, `asset_risk_logs`, `market_indicators`, `investment_decisions`.
- Risk semantics (authoritative): `risk_score` 0—100; Low <30, Medium 30—69, High >=70;
  `escalation_flag = TRUE` when `risk_score > 80`.
- Golden set: **50 labeled queries** — 15 RAG, 10 SQL, 10 Hybrid, 10 High-Risk (multi-agent + guardrail),
  5 Escalation (human handoff).
- Agents: Router, Retrieval, Market Data, Portfolio Evaluation, Risk, Synthesis, Escalation.

## TECH STACK (fixed by ADR — do not swap)
FastAPI — LangGraph (LangChain tools) — PostgreSQL 16 (`finance_auth_db` + `finance_risk_db`/pgvector) — OpenAI-compatible LLM
via a provider-agnostic client — structured JSON logging + OpenTelemetry tracing — pytest + RAGAS-style
eval harness. No new dependency unless the ADR allows it; add an ADR if you must.

## PLAN SEPARATION
This file targets the **capstone**. Prefer `planning/capstone/MASTER_PROMPT.md`.
Production is a **separate** plan under `planning/production/` — do not implement it here.

## PRODUCT ADD-ON — Stock screening
Implement `17_Stock_Screening_Feature.md`: whitelist screen runner on synthetic `equity_*` tables;
saved screens in auth DB; optional NL→screen. Do **not** scrape [Screener.in](https://www.screener.in/).
Screening output is data filtering, not investment advice.

## NON-NEGOTIABLES — a build that violates any of these is a failed build
1. **Source attribution on every answer.** Every factual claim carries a citation:
   `[DOC: <file> — <section> — p.<page>]` for RAG, `[SQL: <table(s)> — query_id=<id> — rows=<n>]` for
   structured data. Source Attribution Rate must be 1.0. An answer with zero citations must be
   replaced by the "insufficient evidence" refusal template.
2. **Escalation is mandatory, never advisory.** Any of the E1—E8 triggers in
   `10_Detailed_Solution_Design.md` forces `escalation_required = true`, halts autonomous answering,
   and returns a human-handoff envelope with full context. Escalation Recall must be 1.0.
3. **Guardrails block override intent.** Requests to override risk assessment, ignore regulatory
   limits, bypass approval, or proceed despite `escalation_flag = TRUE` are refused + escalated —
   never fulfilled, never partially fulfilled, never "here's how you would".
4. **SQL is parameterized and read-only.** Named query templates only (see
   `10_Detailed_Solution_Design.md`). No LLM-authored raw SQL reaching the DB unvalidated;
   DB role has SELECT only. SQL Correctness target >=95%.
5. **Golden set is the gate.** Every sprint ends with `python -m eval.run --suite golden` and the
   SLO report committed to `eval/reports/`. Do not declare a sprint done on vibes.
6. **No investment advice.** Every response includes the educational-use disclaimer from
   `13_Prompt_Engineering_Framework.md`. The system explains policy and data; it never recommends
   buying, selling, or allocating.
7. **RBAC.** Analysts see only portfolios their role permits. Unauthorized Data Access must be 0.
8. **Prod-grade / cloud-ready.** Stateless app; secrets only via env; same container image for every
   env; `CorpusStore` for PDFs; `APP_ENV=prod` refuses stub auth; migrate/ingest are jobs not boot
   side-effects; `deploy/` stubs by Gate 4. See `16_Production_and_Cloud_Readiness.md`.

## SPRINT ORDER — do these in sequence, do not jump ahead
- **Sprint 4 — Data & Knowledge Foundation** (Tasks 15—23): golden dataset file, PDF ingest + pgvector
  index + retrieval validation, SQL schema deployed with scaled synthetic data (20 portfolios /
  120 holdings / 150 risk logs / 80 indicators / 100 decisions), memory strategy, tool integration,
  logging + tracing, baseline metrics, **Prototype 1** (single-hop RAG and SQL answering with citations).
- **Sprint 5 — Routing, Guardrails, Latency** (Tasks 24—30): stable RAG/SQL/Hybrid routing, tool error
  handling with retries, high-risk detection + escalation logic, guardrail/refusal validation,
  golden-set retest, latency <=2s p95, frontend skeleton + frozen API contract.
- **Sprint 6 — Multi-Agent Reasoning** (Tasks 31—36): multi-step reasoning, hybrid consistency checks,
  dynamic tool selection, full 7-agent LangGraph orchestration, escalation/guardrail revalidation,
  **Prototype 2**.
- **Sprint 7** (37—42) frontend integration, complex queries, TSR lift, SLO under load, security +
  observability validation. **Sprint 8** (43—48) **signup + login**, auth/session, RBAC, security review, cost guardrails,
  load test, production readiness. **Sprint 9** (49—52) end-to-end UI flow, citations + routing display,
  restricted-action UX, **Prototype 3**. **Sprint 10** (53—56) integration testing, scalability,
  final SLO evaluation, deployment.

## FILE LAYOUT — under `capstone/` only — create exactly this (from 05_Project_Setup_Readiness.md)
capstone/app/{main.py,api/,core/,graph/nodes/,prompts/,rag/,sqlq/,guardrails/,memory/,schemas/}
capstone/eval/{golden/,runners/,metrics/,reports/}  capstone/data/{documents/,sql/}
capstone/tests/{unit,integration,e2e}  capstone/deploy/  capstone/docker-compose.yml
Production code lives in `production/` — separate plan; do not mix.
capstone/app/core/storage.py (CorpusStore Protocol)

## WORKING RULES
- Smallest change that works. Reuse what exists before adding. No speculative abstractions.
- One sprint per session. Start by restating which tracker tasks you are closing.
- Update `work tracker/FinalProgressTracker_revised.xlsx` status column notes in your summary
  (do not silently mark things done).
- After each sprint: run the golden-set eval, paste the SLO table, and list which of the 16 SLOs
  pass/fail with the measured value.
- Never commit secrets. `.env.example` only.
- If blocked, say so and name the decision you need — do not invent requirements.

## DEFINITION OF DONE for any sprint
(a) code runs from a clean clone per README, (b) golden-set eval executed and report committed,
(c) all non-negotiables verifiably enforced (show the test), (d) tracker tasks named and status stated.

Begin by confirming which sprint you are executing and which planning docs you have read.
````

## End of prompt — copy to here

---

## How to use the planning docs during implementation

| Situation | Doc to open |
|---|---|
| "What should this agent's prompt say?" | `13_Prompt_Engineering_Framework.md` |
| "Which agent handles this query?" | `11_Query_Categories.md` (routing rules table) |
| "What does the API return?" | `14_FastAPI_Service_Setup_Plan.md` |
| "Is this an escalation?" | `10_Detailed_Solution_Design.md` (E1—E8) |
| "Why Postgres/pgvector and not X?" | `07_ADR.md` |
| "How do we stay cloud-ready?" | `16_Production_and_Cloud_Readiness.md` + ADR-015—018 |
| "How do I measure Faithfulness?" | `04_Evaluation_and_Measurement_Plan.md` + `09_Detailed_Use_Case_and_SLO.md` |
| "What counts as passing?" | `12_Evaluation_Dataset_and_Test_Strategy.md` (pass gates) |

## Guardrail on the prompt itself
This master prompt is versioned. If the ADRs change, bump the version here and restate the stack
section. Do not let the prompt drift from `07_ADR.md`.

**Version:** 1.2 — Opus 4.5 / Codex High for agent work — prod/cloud readiness — **Owner:** Capstone architect — **Covers:** Sprint 4—10 execution
