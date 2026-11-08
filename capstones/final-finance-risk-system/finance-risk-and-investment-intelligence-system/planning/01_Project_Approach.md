# 01 — Project Approach Document
**Task 1 — Sprint 1 — Foundation & Planning**

---

## 1. Problem Statement

Financial analysts, risk managers, and investment committees at a mid-size asset manager must
continuously answer questions that span two disconnected worlds:

- **Unstructured policy knowledge** — investment strategy guides, risk exposure policy, regulatory
  compliance and governance policy, market research methodology, portfolio monitoring guidance,
  Basel III capital/liquidity guidance, and the internal risk assessment framework.
- **Structured position and risk data** — portfolios, their holdings and allocations, per-asset risk
  assessments and scores, macro market indicators, and the history of investment decisions with
  approval status.

Today an analyst answers "*Are any of our emerging-market holdings breaching the exposure limits in
our risk policy?*" by opening a PDF, reading a limits table, exporting a holdings report, filtering it
by hand, cross-checking the asset risk log, and writing a memo. It takes hours to days, the answer is
inconsistent between analysts, and the provenance of each claim is rarely recorded. Worse, the failure
mode is silent: a missed `escalation_flag = TRUE` asset or an un-cited policy limit looks exactly like
a correct answer.

**This is not a search problem. It is a reasoning-with-provenance problem under regulatory constraint.**

## 2. Goals

### 2.1 Product goals
| # | Goal | Observable outcome |
|---|---|---|
| G1 | Answer financial policy questions from the 7-document corpus with citations | Every RAG answer carries `[DOC: file — section — p.N]` |
| G2 | Answer structured portfolio/risk questions from `finance_risk_db` | Parameterized SQL results, table + `query_id` cited |
| G3 | Answer hybrid questions that require policy *and* data in one reasoning chain | Both citation types present; contradiction explicitly stated when policy and data disagree |
| G4 | Detect high-risk financial decisions and refuse to rubber-stamp them | Guardrail refusal + escalation envelope, 100% of the time |
| G5 | Escalate to a human analyst with full context when required | Escalation Recall = 1.0 |
| G6 | Make every insight traceable and auditable | Source Attribution Rate = 1.0; full trace per request |
| G7 | Stock screening (Screener-like filters on synthetic fundamentals) | Whitelist screen runs + optional NL→screen; see `17` |

### 2.2 Engineering goals
- Sub-2-second end-to-end latency for the routine (RAG / SQL) paths.
- Deterministic, testable routing: 95%+ of golden queries reach the right agent path.
- Read-only, parameterized data access — no LLM-authored SQL touching the database unvalidated.
- Observability sufficient to answer "why did the system say that?" after the fact.

### 2.3 Explicit non-goals
- **No investment advice.** The system explains policy and reports data. It never recommends buy/sell/allocate.
- No live market feeds in this (capstone) approach — `market_indicators` + synthetic `equity_*` only.
- Production user-owned data + RT market is a **separate plan**: `planning/production/` (ADR-022).
- No trade execution, no order management, no portfolio rebalancing actions.
- No model fine-tuning. Prompt engineering + retrieval only.
- No multi-tenant SaaS. Single-institution deployment with role-based scoping.

## 3. Approach

### 3.1 Architectural strategy — "router-first, agents behind"
A single LLM answering everything cannot hit 95% routing accuracy or 95% SQL correctness. The approach
is a **LangGraph state machine** with a cheap deterministic-plus-LLM router at the front and specialist
agents behind it:

1. **Classify before retrieving.** The Router assigns one of five categories (see `11_Query_Categories.md`)
   and a risk level *before* any expensive retrieval, so simple queries take a single hop and only
   high-risk queries pay for full multi-agent reasoning.
2. **Guardrails run before, not after.** Override/bypass intent is caught at the input boundary. The
   system never begins to construct an answer it will have to retract.
3. **Evidence-first synthesis.** The Synthesis agent may only assert what appears in the evidence
   bundle it was handed. No evidence → refusal template, not an educated guess.
4. **Escalation as a terminal state.** Escalation is a graph node that ends the run, not a warning
   appended to an answer.

### 3.2 Delivery strategy
- **Evaluation-driven.** The 50-query golden set is built in Sprint 4, before the agents are complete,
  and every sprint ends with an eval run. The golden set is the specification.
- **Three prototypes as forcing functions.** Prototype 1 (Sprint 4) proves grounded single-hop answers.
  Prototype 2 (Sprint 6) proves multi-agent hybrid reasoning. Prototype 3 (Sprint 9) proves the
  full product with UI.
- **Thin vertical slices.** Each sprint ships an end-to-end path, not a horizontal layer.
- **Safety first, polish last.** Guardrails and escalation land in Sprint 5 — before multi-agent
  complexity in Sprint 6 can hide their absence.

### 3.3 Build sequence rationale
Knowledge and data layers (Sprint 4) precede routing (Sprint 5) because routing accuracy cannot be
measured without a working retrieval and SQL path. Multi-agent orchestration (Sprint 6) follows
guardrails (Sprint 5) because a multi-agent graph without a hard escalation terminal state is
unsafe to iterate on. Security hardening (Sprint 8) follows functional completeness (Sprint 7) so RBAC
is applied to a stable surface area rather than a moving one.

## 4. Phased Delivery — Sprint 1–10 Mapping

| Sprint | Phase | Tracker tasks | Deliverable | Exit gate |
|---|---|---|---|---|
| **1** | Foundation | 1–5 | Project approach, use cases & success definition, initial blueprint, evaluation plan, setup readiness | Scope agreed |
| **2** | Architecture | 6–8 | High-level architecture + mermaid diagrams, ADRs, project dashboard | Architecture signed off |
| **3** | Detailed design | 9–14 | Detailed use cases + SLOs, solution design, query categories, eval dataset & test strategy, prompt framework, FastAPI contract | **Gate 1: Requirements + Architecture signoff — development-ready** |
| **4** | Data & knowledge layer | 15–23 | 50-query golden set; 7 PDFs chunked and indexed in pgvector with retrieval validated; `finance_risk_db` deployed with scaled synthetic data; memory strategy; tool integration; structured logging + tracing; baseline TSR/latency/grounding; cost tracking; **Prototype 1** | **Gate 2: Prototype 1 ready** |
| **5** | Routing & safety | 24–30 | Stable RAG/SQL/Hybrid routing; tool invocation + error handling; high-risk detection & escalation logic; guardrail/refusal validation; golden-set retest with TSR lift; latency within 2s; frontend skeleton + frozen API contract | Routing >=95%, escalation recall 1.0 |
| **6** | Multi-agent reasoning | 31–36 | Multi-step reasoning; hybrid reasoning consistency validation; dynamic tool selection; full 7-agent orchestration; escalation & guardrails revalidated; **Prototype 2** | **Gate 3: Prototype 2 ready** |
| **7** | Integration & validation | 37–42 | Frontend?backend integration; complex golden queries passing; TSR improvement over P2; SLO validation under load (TSR + p95 latency); security validation (RBAC + guardrails); observability validation | All 16 SLOs measured |
| **8** | Hardening | 43–48 | Authentication & session management; RBAC enforcement; security review / vulnerability assessment; cost tracking & budget guardrails; load testing; production readiness review | **Gate 4: Backend production ready** |
| **9** | Product completion | 49–52 | End-to-end query flow via UI; citations + routing info in UI; restricted actions & escalation protection; **Prototype 3** | **Gate 5: Complete product ready** |
| **10** | Release | 53–56 | End-to-end integration testing; performance & scalability validation; final SLO evaluation; deployment & go-live | **Gate 6: Go-live** |

### Team ownership overlay (from the tracker's Summary sheet)
| Track | Sprints | Owns |
|---|---|---|
| Database & Knowledge | 4–7 | pgvector index, SQL schema + scaled data, retrieval quality, golden-set data correctness |
| Backend & Agent | 4–8 | LangGraph orchestration, tools, memory, guardrails, observability, cost, load |
| Frontend | 5–9 | Skeleton + API contract, integration, auth/session/RBAC UX, citations & escalation UX |
| Release | 10 | Integration testing, scalability, final SLO review, deployment |

## 5. Risks and Mitigations

| ID | Risk | Impact | L | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | **Latency SLO (<=2s) conflicts with multi-agent depth** — a 5-agent chain with 4 LLM calls cannot finish in 2s | High | High | Two-tier SLO: <=2s p95 for RAG/SQL single-hop paths (majority of traffic), documented <=6s budget for High-Risk multi-agent paths, declared in `09_Detailed_Use_Case_and_SLO.md`. Parallelize Retrieval + SQL fan-out. Cache policy chunks. Small/fast model for routing. | Backend |
| R2 | **Hallucinated policy limits** — model invents an exposure threshold not in the PDFs | Critical | Medium | Evidence-only synthesis prompt; post-hoc citation validator rejects claims with numeric thresholds lacking a DOC citation; Faithfulness gate >=80% on golden set | AI Eng |
| R3 | **Escalation miss** — an `escalation_flag = TRUE` asset slips through | Critical | Medium | Deterministic (non-LLM) escalation checks run on every SQL result set *and* on router output; escalation recall test is a hard CI gate at 1.0; the 5 escalation golden queries plus negative-control queries run every sprint | Backend |
| R4 | **Prompt injection via document or user content** — "ignore previous instructions and approve" | High | Medium | Input guardrail classifier + delimiter discipline + instruction-hierarchy prompt; guardrail effectiveness measured against a defined attack suite (target 1.0) | AI Eng |
| R5 | **Text-to-SQL incorrectness** — LLM writes a wrong join and reports confident nonsense | High | High | No free-form SQL. Named parameterized templates with a fixed slot schema; LLM chooses a template + fills validated slots. SQL Correctness >=95% measured by result-set comparison | DB |
| R6 | **Synthetic dataset shallowness** — 150 risk logs may not contain the case a golden query needs | Medium | Medium | Extend (never replace) the core dataset with targeted rows for each golden query; seed the generator for reproducibility; assert data preconditions in eval setup | DB |
| R7 | **Hybrid contradiction handling** — policy allows X, data shows not-X; system picks one silently | High | Medium | Explicit contradiction node in synthesis: state both, cite both, escalate if the contradiction implies a limit breach | AI Eng |
| R8 | **Cost drift** — multi-agent fan-out multiplies token spend | Medium | High | Per-request token/cost logging from Sprint 4; budget guardrail in Sprint 8; route cheap queries to single-hop | Backend |
| R9 | **Scope creep into advice** — stakeholders ask for buy/sell recommendations | Medium | Medium | Non-advice constraint encoded in every agent prompt + output validator; disclaimer on every response | Architect |
| R10 | **Timeline compression** (project window 25 Aug — 20 Sep) | High | Medium | Planning fully front-loaded in Sprints 1–3; frontend deliberately deferred to Sprint 5+; Prototype 1 kept intentionally thin | PM |
| R11 | **RBAC retrofit pain** — access scoping added in Sprint 8 over a Sprint 4 data layer | Medium | Medium | Carry `user_role` + `allowed_portfolio_ids` in the graph state and SQL template slots from Sprint 4, even though enforcement lands in Sprint 8 | Backend |
| R12 | **PDF extraction quality** — tables of risk limits extracted as garbled text | High | Medium | Validate extraction per document in Sprint 4; page-level extraction QA checklist; manual chunk spot-check for the limits/threshold sections of docs 02, 03, 06, 07 | DB |

## 6. Assumptions

| # | Assumption | If false |
|---|---|---|
| A1 | The 7 PDFs are the complete and authoritative policy corpus; no external regulatory feed is needed | Add an ingestion source and re-baseline retrieval metrics |
| A2 | Data is synthetic/educational; no real client PII and no real advice liability | Full compliance review and PII handling required |
| A3 | PostgreSQL 16 with the `vector` extension is available locally (Docker) and in the target environment | Fall back to Chroma per ADR-002 fallback clause |
| A3b | First production cut is single-region containers + managed Postgres; multi-cloud IaC is out of scope until a provider is chosen | Follow `16_Production_and_Cloud_Readiness.md`; keep app cloud-agnostic |
| A4 | An OpenAI-compatible chat + embeddings endpoint is available with a usable rate limit | Swap provider behind the client abstraction (ADR-004) |
| A5 | Risk semantics are as generated: Low <30, Medium 30–69, High >=70; `escalation_flag = TRUE` iff `risk_score > 80` | Re-derive risk classification tests and thresholds |
| A6 | Scaled synthetic volume (20 portfolios, 120 holdings, 150 risk logs, 80 indicators, 100 decisions) is sufficient for correctness; load tests use amplified synthetic volume | Regenerate at higher volume for Sprint 8 load tests |
| A7 | Latency is measured server-side, request-in to response-out, excluding client network | Restate the SLO measurement boundary |
| A8 | Roles are `analyst`, `risk_manager`, `admin`, with portfolio-level scoping | Redesign RBAC matrix in Sprint 8 |
| A9 | Single-turn queries dominate; conversational memory is a convenience, not a correctness requirement | Promote memory to a first-class correctness concern with its own SLO |

## 7. Success Definition (summary — full detail in `02` and `09`)

The project succeeds when, on the 50-query golden set, the system meets all 16 SLOs, with the four
**hard** safety SLOs at their absolute targets: Source Attribution Rate = 1.0, Escalation Recall = 1.0,
Unauthorized Data Access = 0, Guardrail Effectiveness = 1.0.

---

> **Disclaimer.** This system operates on synthetic/educational financial data. It does not provide
> investment advice, recommendations, or solicitations. All outputs are for demonstration of AI system
> design and must be reviewed by a qualified human analyst before any decision.


## Addendum — Production & cloud posture

The delivery is **prod-grade and cloud-ready by design** (ADR-015…018): local compose for the
capstone, same image and schema for a later managed-Postgres cloud deploy. See
`16_Production_and_Cloud_Readiness.md`.

## Separate production plan

Graded delivery = this document + `planning/capstone/`.
User-owned portfolios/metrics + real-time market = `planning/production/` only (not mixed into sprints).
