# 08 — Project Dashboard Structure (Miro / Trello)
**Task 8 — Sprint 2 — Foundation & Planning**

**Live board (GATE-1):** [`deliverables/dashboard/index.html`](deliverables/dashboard/index.html) — 56 task cards, 6 gates, SLO wall. Spec below is the source for that board.

A board specification that mirrors the progress tracker exactly: 10 sprints, 56 tasks, 16 SLOs, 6 gates.
Build it in Trello (Kanban execution) with an optional Miro companion (architecture + SLO wall).

---

## 1. Board Identity

| Field | Value |
|---|---|
| Board name | `Finance Risk & Investment Intelligence System — Capstone` |
| Timeline | Start 25 Aug 2026 — End 20 Sep 2026 — Batch end 26 Sep 2026 |
| Board type | Kanban with sprint labels + WIP limits |
| Source of truth | `work tracker/FinalProgressTracker_revised.xlsx` — the board mirrors it; the tracker wins on conflict |

---

## 2. Column (List) Structure

| # | Column | Entry criteria | Exit criteria | WIP limit |
|---|---|---|---|---|
| 1 | **Backlog — All Sprints** | Task exists in the tracker | Sprint is active and task is planned | none |
| 2 | **Sprint Ready** | Acceptance criteria written; dependencies met; owner named; planning doc referenced | Owner starts work | **10** |
| 3 | **In Progress** | Owner assigned, work started | Code/doc complete, self-reviewed | **3 per person / 6 board-wide** |
| 4 | **Blocked** | Explicit blocker card note + who can unblock | Blocker cleared | **3** (>3 = escalate to standup) |
| 5 | **In Review** | Peer review requested; PR open or doc submitted | Review approved | **4** |
| 6 | **Eval / SLO Check** | Reviewed, needs `python -m eval.run` evidence | Eval report attached; affected SLOs pass | **4** |
| 7 | **Done** | All exit criteria met, evidence attached | — | none |
| 8 | **Gate Review** *(swimlane, not a flow column)* | Sprint gate reached | Gate signed off | 1 gate at a time |

> **Why an Eval/SLO column?** In this project "code works" is not "done". Every functional task must
> show which of the 16 SLOs it touched and that they still pass. This column makes the eval step
> impossible to skip.

---

## 3. Labels

### Sprint labels
`S1` `S2` `S3` `S4` `S5` `S6` `S7` `S8` `S9` `S10`

### Track labels (from the tracker Summary sheet)
| Label | Colour | Track | Sprints |
|---|---|---|---|
| `TRACK:PLAN` | grey | Foundation & Planning | 1–3 |
| `TRACK:DATA` | blue | Database & Knowledge Layer | 4–7 |
| `TRACK:BACKEND` | yellow | Backend / Agent Layer | 4–8 |
| `TRACK:FRONTEND` | purple | Frontend Layer | 5–9 |
| `TRACK:RELEASE` | red | Release & Production | 10 |

### Type labels
`TYPE:DOC` `TYPE:CODE` `TYPE:DATA` `TYPE:EVAL` `TYPE:SECURITY` `TYPE:INFRA` `TYPE:PROTOTYPE`

### Risk / priority labels
`P0-SAFETY` (hard SLO at stake) — `P1` — `P2` — `RISK:R1`—`RISK:R12` (links to `01_Project_Approach.md` —5)

### SLO labels (attach to any card whose completion moves a metric)
`SLO:FAITHFULNESS` `SLO:RELEVANCE` `SLO:CTX-PRECISION` `SLO:LATENCY` `SLO:ACCURACY` `SLO:RECALL`
`SLO:JUDGE` `SLO:TSR` `SLO:SQL` `SLO:ATTRIBUTION` `SLO:CMR` `SLO:ESCALATION` `SLO:RBAC`
`SLO:GUARDRAIL` `SLO:ROUTING` `SLO:RISK-CLASS`

---

## 4. Card Template

Every card uses this description template:

```
### Task
Tracker: Sprint <n> — Task <m> — <tracker task name>

### Planning reference
Doc: planning/<file>.md  —<section>

### Acceptance criteria
- [ ] <criterion 1>
- [ ] <criterion 2>

### SLOs touched
<SLO labels> — expected effect: <e.g. Routing Accuracy 88% → >=95%>

### Evidence required in Done
- [ ] Eval report path: eval/reports/<sprint>/report.md
- [ ] Test(s) added: tests/<path>
- [ ] Reviewer: <name>

### Definition of Done
Runs from clean clone — eval executed — hard SLOs green — tracker row updated
```

**Checklists on every code card:** `Tests added` — `Logging/tracing span added` —
`Citations enforced (if answer path)` — `Escalation checks unaffected or extended` —
`Cost impact measured`.

---

## 5. Cards — All 56 Tracker Tasks

### Sprint 1 — Foundation *(`S1` `TRACK:PLAN` `TYPE:DOC`)*
| Card | Tracker | Planning doc | Done evidence |
|---|---|---|---|
| Project Approach Document | T1 | `01_Project_Approach.md` | Doc reviewed; risks + assumptions listed |
| Use Case & Success Definition | T2 | `02_Use_Case_and_Success_Definition.md` | 5 personas, 17 use cases, SLO mapping |
| Initial System Blueprint | T3 | `03_Initial_System_Blueprint.md` | 8 layers, 7 agents, data flows |
| Evaluation & Measurement Plan | T4 | `04_Evaluation_and_Measurement_Plan.md` | All 16 metrics have a measurement method |
| Project Setup Readiness | T5 | `05_Project_Setup_Readiness.md` | Repo layout, env vars, deps, checklists, runbooks |

### Sprint 2 — Architecture *(`S2` `TRACK:PLAN`)*
| Card | Tracker | Planning doc | Done evidence |
|---|---|---|---|
| High Level Architecture Diagram | T6 | `06_High_Level_Architecture.md` | 5 mermaid diagrams render; invariants listed |
| ADR (Architecture Decision Record) | T7 | `07_ADR.md` | 14 ADRs with alternatives + consequences |
| Project Dashboard Creation | T8 | `08_Project_Dashboard.md` | Board live with all 56 cards + WIP limits |

### Sprint 3 — Detailed Design *(`S3` `TRACK:PLAN`)*
| Card | Tracker | Planning doc | Done evidence |
|---|---|---|---|
| Detailed Use Case Spec & SLO Definition | T9 | `09_Detailed_Use_Case_and_SLO.md` | Pre/flow/post per UC; 16-SLO table |
| Detailed Solution Design | T10 | `10_Detailed_Solution_Design.md` | Agent contracts, state, E1—E8, error handling |
| Query Categories Definition | T11 | `11_Query_Categories.md` | 5 categories, routing rules, labels |
| Evaluation Dataset & Test Strategy | T12 | `12_Evaluation_Dataset_and_Test_Strategy.md` | Golden schema, 4 test levels, pass gates |
| Prompt Engineering Framework | T13 | `13_Prompt_Engineering_Framework.md` | 7 agent prompts + refusal templates |
| FastAPI Service Setup | T14 | `14_FastAPI_Service_Setup_Plan.md` | Endpoints, schemas, auth stub, folder layout |
| **?? GATE 1 — Requirements + Architecture Signoff** | — | all `planning/` | Sprint 1–3 docs approved; development-ready |

### Sprint 4 — Data & Knowledge Layer *(`S4` `TRACK:DATA` + `TRACK:BACKEND`)*
| Card | Tracker | Key SLO labels | Done evidence |
|---|---|---|---|
| Golden Dataset Ready | T15 | `SLO:TSR` | 50 labeled queries in `eval/golden/golden_queries.jsonl` (15/10/10/10/5) |
| Vector DB Indexed & Retrieval Validated | T16 | `SLO:CTX-PRECISION` `SLO:RECALL` | 7 PDFs chunked + embedded; 20-probe smoke test passes |
| SQL Schema Deployed with Scaled Data | T17 | `SLO:SQL` | 5 tables + indexes + read-only role; 20/120/150/80/100 rows; seed recorded |
| Memory Management Strategy Finalized | T18 | — | `sessions`/`turns`, 5-turn window per ADR-006 |
| MCP / Tool Integration Configured | T19 | `SLO:SQL` | ~18 SQL templates registered + retrieval tool; slot validation tests |
| Logging & Tracing Operational | T20 | — | JSON logs + span per node; `trace_id` in response |
| Baseline Metrics Captured | T21 | `SLO:TSR` `SLO:LATENCY` `SLO:ATTRIBUTION` | `eval/reports/sprint4_baseline/report.md` committed |
| Cost Tracking / Observability Enabled | T22 | — | token + cost per request/agent in logs and `/metrics` |
| **Prototype 1** `TYPE:PROTOTYPE` | T23 | `SLO:ATTRIBUTION` | C1 + C2 answered end-to-end with valid citations |
| **?? GATE 2 — Prototype 1 Ready** | — | — | Baseline SLO table published |

### Sprint 5 — Routing, Safety, Latency *(`S5` `TRACK:BACKEND` + `TRACK:FRONTEND`)*
| Card | Tracker | Key SLO labels | Done evidence |
|---|---|---|---|
| RAG + SQL + Hybrid Routing Stable | T24 | `SLO:ROUTING` | >=95% on golden `expected_category`; 5–5 confusion matrix |
| Tool Invocation & Error Handling | T25 | `SLO:TSR` | retry/timeout/fallback per `10` —7; failure-injection tests |
| High-Risk Detection & Escalation Logic | T26 | `SLO:ESCALATION` `SLO:CMR` `P0-SAFETY` | E1—E8 implemented; escalation recall = 1.0 |
| Guardrails / Refusal Behaviour Validation | T27 | `SLO:GUARDRAIL` `P0-SAFETY` | attack suite 100% blocked; no method leakage |
| Golden Dataset Retest & TSR Improvement | T28 | `SLO:TSR` `SLO:ACCURACY` | TSR delta vs. Sprint 4 baseline documented |
| Latency Optimization within Target | T29 | `SLO:LATENCY` | C1/C2 p95 <=2s; C3 <=4s; C4 <=6s (ADR-010) |
| Frontend Skeleton & API Contract Definition | T30 | — | contract frozen per `14`; skeleton calls `/api/v1/query` |

### Sprint 6 — Multi-Agent Reasoning *(`S6` `TRACK:BACKEND`)*
| Card | Tracker | Key SLO labels | Done evidence |
|---|---|---|---|
| Multi-Step Reasoning Operational | T31 | `SLO:TSR` | C4 queries use >=2 agents and >=2 evidence types |
| Hybrid Reasoning Consistency Validation | T32 | `SLO:FAITHFULNESS` | contradiction handling verified on hybrid conflict cases |
| Dynamic Tool Selection Stable | T33 | `SLO:SQL` | correct `query_id` chosen >=95% vs. `expected_query_id` |
| Multi-Agent / Role Orchestration Working | T34 | `SLO:TSR` | all 7 agents wired; parallel fan-out verified in traces |
| Escalation & Guardrails Revalidated | T35 | `SLO:ESCALATION` `SLO:GUARDRAIL` `P0-SAFETY` | both still 1.0 after multi-agent changes |
| **Prototype 2** `TYPE:PROTOTYPE` | T36 | — | full hybrid + high-risk demo |
| **?? GATE 3 — Prototype 2 Ready** | — | — | full eval report; TSR trend |

### Sprint 7 — Integration & Validation *(`S7` `TRACK:FRONTEND` + `TRACK:DATA` + `TRACK:BACKEND`)*
| Card | Tracker | Key SLO labels |
|---|---|---|
| Frontend Integration with Backend | T37 | — |
| Complex Golden Queries Passing | T38 | `SLO:TSR` `SLO:ACCURACY` |
| TSR Improvement over Prototype 2 | T39 | `SLO:TSR` |
| SLO Validation Under Load (TSR & P95 Latency) | T40 | `SLO:LATENCY` `SLO:TSR` |
| Security Validation (RBAC + Guardrails) | T41 | `SLO:RBAC` `SLO:GUARDRAIL` `P0-SAFETY` |
| Observability Validation (Logs, Metrics, Traces) | T42 | — |

### Sprint 8 — Hardening *(`S8` `TRACK:BACKEND` `TYPE:SECURITY`)*
| Card | Tracker | Key SLO labels |
|---|---|---|
| Authentication & Session Management | T43 | — |
| Role-Based Access Control Enforcement | T44 | `SLO:RBAC` `P0-SAFETY` |
| Security Review / Vulnerability Assessment | T45 | `SLO:GUARDRAIL` `SLO:RBAC` |
| Cost Tracking & Budget Guardrails | T46 | — |
| Load Testing Completed & Stable | T47 | `SLO:LATENCY` |
| Production Readiness Review | T48 | all |
| **?? GATE 4 — Backend Production Ready** | — | most critical checkpoint |

### Sprint 9 — Product Completion *(`S9` `TRACK:FRONTEND`)*
| Card | Tracker | Key SLO labels |
|---|---|---|
| End-to-End Query Flow via UI | T49 | `SLO:TSR` |
| Frontend Citations & Routing Information | T50 | `SLO:ATTRIBUTION` |
| Restricted Actions & Escalation Protection | T51 | `SLO:ESCALATION` `SLO:GUARDRAIL` `P0-SAFETY` |
| **Prototype 3** `TYPE:PROTOTYPE` | T52 | — |
| **?? GATE 5 — Complete Product Ready** | — | — |

### Sprint 10 — Release *(`S10` `TRACK:RELEASE`)*
| Card | Tracker | Key SLO labels |
|---|---|---|
| End-to-End Integration Testing | T53 | `SLO:TSR` |
| Performance & Scalability Validation | T54 | `SLO:LATENCY` |
| Final SLO Evaluation | T55 | all 16 |
| Deployment & Go-Live | T56 | — |
| **?? GATE 6 — Go-Live** | — | — |

---

## 6. SLO Wall (dedicated board section / Miro frame)

One card per SLO, updated after every eval run. Card front shows target; back holds the sprint-by-sprint
measured history.

| # | SLO | Target | S4 | S5 | S6 | S7 | S8 | S10 final |
|---|---|---|---|---|---|---|---|---|
| 1 | Faithfulness | >=80% | | | | | | |
| 2 | Answer Relevance | >=75% | | | | | | |
| 3 | Context Precision | >=70% | | | | | | |
| 4 | Latency (C1/C2 p95) | <=2s | | | | | | |
| 5 | Accuracy | >=85% | | | | | | |
| 6 | Recall | >=75% | | | | | | |
| 7 | LLM as a judge | >=80% | | | | | | |
| 8 | TSR | >=90% | | | | | | |
| 9 | SQL Correctness | >=95% | | | | | | |
| 10 | **Source Attribution Rate** | **1.0** | | | | | | |
| 11 | Critical Misclassification Rate | <3% | | | | | | |
| 12 | **Escalation Recall** | **1.0** | | | | | | |
| 13 | **Unauthorized Data Access (RBAC)** | **0** | | | | | | |
| 14 | **Guardrail Effectiveness** | **1.0** | | | | | | |
| 15 | Query Routing Accuracy | >=95% | | | | | | |
| 16 | Risk Classification Accuracy | >=95% | | | | | | |

Bold rows are **hard gates**: any red cell blocks the sprint gate, no exceptions.

---

## 7. Miro Companion Board (optional, for reviews)

| Frame | Contents |
|---|---|
| **F1 — Problem & Personas** | Manual-process pain flow, 5 persona cards with their top questions |
| **F2 — System Context** | The C4 L1 diagram from `06` —2 |
| **F3 — Agent Orchestration** | The LangGraph state diagram from `06` —4, with per-node latency budgets annotated |
| **F4 — Hybrid Flow Walkthrough** | The `06` —5 sequence, annotated with the worked example and its citations |
| **F5 — Guardrail & Escalation Map** | E1—E8 decision map from `06` —6, colour-coded by severity |
| **F6 — SLO Wall** | The 16-SLO grid as a live traffic-light board |
| **F7 — Sprint Timeline** | 10-sprint Gantt with the 6 gates and the four team tracks as swimlanes |
| **F8 — Risk Register** | R1—R12 on an impact — likelihood grid, linked to owning cards |
| **F9 — Query Category Map** | 5 categories → agent paths → golden-set counts (15/10/10/10/5) |
| **F10 — Decision Log** | ADR-001—ADR-014 as sticky notes with status |

---

## 8. Board Rituals

| Ritual | Cadence | Output |
|---|---|---|
| Daily standup | daily, 10 min | Blocked column reviewed first; WIP violations named |
| Sprint planning | start of sprint | Cards moved Backlog → Sprint Ready with acceptance criteria filled |
| Eval review | end of sprint | `python -m eval.run --suite all --slo-table`; SLO Wall updated; regressions become new cards |
| Gate review | at each of the 6 gates | Gate card checklist signed; screenshot of the SLO Wall attached |
| Risk review | weekly | R1—R12 statuses updated; new risks added with owners |
| Retro | end of sprint | Up to 3 improvement cards into the next sprint |

## 9. Board Automation (Trello Butler rules)
1. Card enters **In Progress** without an owner → comment "assign an owner" and move back to Sprint Ready.
2. Card enters **Done** without an attached eval report and a `TYPE:CODE` label → move to **Eval / SLO Check**.
3. Card labeled `P0-SAFETY` sits in **Blocked** > 24h → notify the board and post to the standup channel.
4. All cards of a sprint in **Done** → create that sprint's Gate Review card automatically.
5. Card enters **In Review** → checklist "peer reviewer assigned" added.

## 10. WIP Limit Rationale
`In Progress` is capped at 3 per person because the highest-risk sprints (4–6) require deep focus on
safety-critical logic where context switching produces exactly the class of silent bug (a missed
escalation trigger) that the project cannot tolerate. `Blocked` is capped at 3 to force resolution
rather than accumulation.

---

> **Disclaimer.** Synthetic/educational data. Not investment advice.
