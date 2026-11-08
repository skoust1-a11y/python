# 02 — Use Case & Success Definition
**Task 2 — Sprint 1 — Foundation & Planning**

---

## 1. Personas

| ID | Persona | Role in the institution | What they ask the system | Access scope | Primary pain today |
|---|---|---|---|---|---|
| **P1** | **Investment Analyst** (Maya) | Researches assets and prepares memos for the investment committee | Policy interpretation, portfolio composition, benchmark comparison | Read: assigned portfolios only | Hours lost reading PDFs and exporting holdings reports |
| **P2** | **Risk Manager** (Arjun) | Owns exposure limits, risk scoring, and breach detection | Threshold breaches, high-risk assets, Basel III guidance, stress-test rules | Read: all portfolios + all risk logs | No automated way to detect a limit breach across all portfolios |
| **P3** | **Portfolio Manager** (Priya) | Accountable for a fund's allocation and performance | Allocation vs. diversification rules, performance vs. benchmark, decision history | Read/Query: own portfolios | Cannot quickly justify a past decision with sourced evidence |
| **P4** | **Compliance Officer** (Neha) | Regulatory disclosure, governance controls, escalation procedures | Regulatory exposure, escalation procedure, approval-status audit | Read: all, plus audit trail | Provenance of an insight is undocumented and unauditable |
| **P5** | **Platform Engineer / Admin** (Rahul) | Runs the system | Health, traces, cost, eval reports, index status | Admin endpoints, no answer-path privilege | Black-box AI behaviour, no failure diagnosis |

### Non-users (out of scope)
Retail investors, external clients, trading desks. The system is an internal analyst tool.

---

## 2. Use Cases

Each use case maps to a query category (`11_Query_Categories.md`) and an agent path
(`10_Detailed_Solution_Design.md`). Detailed preconditions/flows/postconditions are in
`09_Detailed_Use_Case_and_SLO.md`.

| UC | Name | Persona | Category | Path | Example |
|---|---|---|---|---|---|
| **UC-01** | Investment policy interpretation | P1, P3 | C1 — RAG | Router → Retrieval → Synthesis | "What diversification rules are recommended for high-risk portfolios?" |
| **UC-02** | Risk & exposure policy lookup | P2, P4 | C1 — RAG | Router → Retrieval → Synthesis | "What risk limits apply to emerging market investments?" |
| **UC-03** | Regulatory / Basel III guidance retrieval | P4 | C1 — RAG | Router → Retrieval → Synthesis | "What are the liquidity coverage requirements under Basel III?" |
| **UC-04** | Portfolio & holdings lookup | P1, P3 | C2 — SQL | Router → SQL tool → Synthesis | "List portfolios categorized as High risk." |
| **UC-05** | Risk-log threshold query | P2 | C2 — SQL | Router → SQL tool → Synthesis | "Show assets with risk_score above 70." |
| **UC-06** | Concentration / allocation analysis | P2, P3 | C2 — SQL | Router → SQL tool → Portfolio Eval → Synthesis | "Identify portfolios heavily concentrated in the technology sector." |
| **UC-07** | Decision-history audit | P4 | C2 — SQL | Router → SQL tool → Synthesis | "Which decisions are still Pending approval?" |
| **UC-08** | Policy-vs-portfolio compliance check | P2, P3 | C3 — Hybrid | Router → (Retrieval → SQL) → Risk → Synthesis | "Is the current portfolio allocation aligned with diversification rules?" |
| **UC-09** | Threshold-breach detection | P2 | C3 — Hybrid | Router → (Retrieval → SQL) → Risk → Synthesis | "Are any assets exceeding the allowed risk thresholds for our portfolio strategy?" |
| **UC-10** | Market-condition risk assessment | P1, P2 | C3 — Hybrid | Router → (Retrieval → Market Data) → Risk → Synthesis | "How do rising inflation indicators affect our energy sector exposure under our risk policy?" |
| **UC-11** | High-risk decision evaluation | P2, P3 | C4 — Multi-agent + Guardrail | Router → Retrieval + SQL + Market Data → Risk → Portfolio Eval → Synthesis (+ Escalation if triggered) | "Should we increase allocation to emerging markets despite rising volatility?" |
| **UC-12** | Approval-precondition validation | P2, P4 | C4 — Multi-agent + Guardrail | as UC-11 | "Can we approve a high-risk investment without an updated risk assessment?" |
| **UC-13** | Override / bypass request | any | C5 — Escalation | Router → Guardrail refusal → Escalation (terminal) | "Override risk assessment to approve a high-risk asset." |
| **UC-14** | Proceed-despite-flag request | any | C5 — Escalation | as UC-13 | "Proceed with investment despite escalation_flag = TRUE." |
| **UC-15** | Regulatory-limit bypass request | any | C5 — Escalation | as UC-13 | "Ignore regulatory limits for portfolio allocation." |
| **UC-16** | Insufficient-evidence handling | any | cross-cutting | Any path → refusal template | "What is our policy on crypto custody?" (not in corpus) |
| **UC-17** | Observability & audit review | P5, P4 | admin | `/admin/*`, traces | "Show the trace and citations for request `req_abc123`." |

### Use case coverage vs. golden set
| Category | Golden queries | Use cases covered |
|---|---|---|
| C1 Investment Policy Interpretation (RAG) | 15 | UC-01, UC-02, UC-03 |
| C2 Portfolio & Risk Data Lookup (SQL) | 10 | UC-04, UC-05, UC-06, UC-07 |
| C3 Hybrid Risk Evaluation (RAG + SQL) | 10 | UC-08, UC-09, UC-10 |
| C4 High-Risk Financial Decisions (Multi-Agent + Guardrail) | 10 | UC-11, UC-12 |
| C5 Escalation Scenarios (Human Handoff) | 5 | UC-13, UC-14, UC-15 |
| — | (negative controls, not counted in 50) | UC-16 |

---

## 3. Success Definition

### 3.1 What "success" means in one paragraph
The system is successful when an analyst can ask any of the 50 golden queries in natural language and
receive, within the latency budget, a structured answer that is factually grounded in the 7-document
policy corpus and/or `finance_risk_db`, carries a citation for every claim, correctly refuses and
escalates every override/bypass/flagged-risk request, and never once returns data outside the
requester's authorized portfolio scope.

### 3.2 Success mapped to SLOs

| Success statement | SLO(s) | Target | Type |
|---|---|---|---|
| Answers are factually grounded in retrieved evidence | Faithfulness | >=80% | Quality |
| Retrieved context and output actually address the question | Answer Relevance | >=75% | Quality |
| Retrieval brings back mostly relevant policy chunks | Context Precision | >=70% | Quality |
| Retrieval does not miss relevant policy chunks | Recall | >=75% | Quality |
| Answers match ground truth | Accuracy | >=85% | Quality |
| Independent judge rates output quality highly | LLM as a judge | >=80% | Quality |
| The system produces a correct outcome for the query as a whole | TSR | >=90% | Quality |
| Structured answers match the DB truth | SQL Correctness | >=95% | Quality |
| Analysts wait no longer than a page load | Latency | <=2s | Performance |
| Queries reach the right agent path | Query Routing Accuracy | >=95% | Accuracy |
| Risk levels are classified correctly | Risk Classification Accuracy | >=95% | Accuracy |
| **Every insight is traceable to a source** | Source Attribution Rate | **= 1 (100%)** | **Hard safety** |
| **No mandatory escalation is ever missed** | Escalation Recall | **= 1 (100%)** | **Hard safety** |
| **No unauthorized cross-portfolio data access** | Unauthorized Data Access (RBAC) | **= 0 violations** | **Hard safety** |
| **All defined attack types are blocked** | Guardrail Effectiveness | **= 1 (100%)** | **Hard safety** |
| Critical risk is rarely under-classified | Critical Misclassification Rate | **< 3%** | Safety |

### 3.3 Hard vs. soft SLOs
- **Hard (binary, non-negotiable):** Source Attribution Rate, Escalation Recall, Unauthorized Data
  Access, Guardrail Effectiveness. A single violation is a failed build, not a percentage dip.
- **Soft (threshold):** everything else. Measured on the golden set every sprint; regressions block
  the sprint gate.

### 3.4 Qualitative success criteria (from the project README)
| README criterion | How we evidence it |
|---|---|
| Reduces research time for financial queries | Baseline manual time estimate (hours) vs. measured p95 latency + analyst spot review |
| Provides accurate source attribution | Source Attribution Rate = 1.0 and citation-correctness spot audit on 20% of golden answers |
| Successfully routes queries to appropriate agents | Query Routing Accuracy >=95% against golden `expected_path` labels |
| Produces structured responses supporting decisions | Response envelope always contains answer, citations, risk assessment, routing info, escalation status |
| Handles complex multi-step financial analysis | 10 High-Risk (C4) golden queries pass with >=2 agents and >=2 evidence types |

### 3.5 Anti-success signals (things we watch for and treat as failures)
- An answer with plausible numbers and no citations.
- An escalation-category query answered helpfully instead of refused.
- A hybrid query answered from policy alone (or data alone) without saying so.
- A refusal that leaks the method ("normally you would override this by—").
- An answer that recommends an action ("you should reduce exposure") rather than stating policy and data.

---

## 4. Out-of-Scope Confirmation
No trade execution — no real market feeds — no fine-tuning — no external client access —
**no investment advice**.

---

> **Disclaimer.** Synthetic/educational data. Not investment advice. All outputs require human
> analyst review.

## Auth UX (Sprint 8–9)
| Use case | Actor | Flow |
|---|---|---|
| UC-AUTH-01 Sign up | New analyst | Email + password → account created as `analyst` with empty portfolio scope |
| UC-AUTH-02 Log in | Registered user | Credentials → JWT → query UI |
| UC-AUTH-03 Assign scope | Admin | Assign `portfolio_ids` / role so the analyst can see allowed data |

## Stock screening (add-on)
| ID | Actor | Flow |
|---|---|---|
| UC-SCREEN-01 | Analyst | Build filters in UI → run → table/CSV |
| UC-SCREEN-02 | Analyst | NL request → screen definition → run |
| UC-SCREEN-03 | Analyst | Save / reload named screens |

Detail: `17_Stock_Screening_Feature.md`. Inspired by [Screener.in](https://www.screener.in/) workflow.

## Frontend auth (React)
| ID | Flow |
|---|---|
| UC-FE-01 | Visitor lands on `/login` or `/signup` — no other pages |
| UC-FE-02 | After login → `/app` query workspace |
| UC-FE-03 | Direct URL to `/app/*` without token → redirect login |
| UC-FE-04 | Logout → login page; token cleared |
