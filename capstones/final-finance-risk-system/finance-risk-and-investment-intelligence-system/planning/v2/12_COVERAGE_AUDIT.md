# Coverage Audit — v2 vs Provided Course Materials

**Question:** Is everything from the provided docs covered in v2?

**Answer:** **Mandatory course content — yes**, when v2 is read **together with** the v1 deep-reference files it points to. v2 alone is an **executive + requirements layer**, not a full duplicate of 20 v1 files.

---

## 1. Source documents checked

| Source | Location |
|---|---|
| Course README (core requirements, layers, deliverables) | Historical / `Project-3-…/README.md` (content preserved in v1 `01`, `03`) |
| Dataset & golden set spec | `capstone/capstone_finance_risk_and_investment_dataset.md` |
| Progress tracker (56 tasks, 16 SLOs) | `work tracker/FinalProgressTracker_revised.xlsx` |
| Policy PDFs (7) | `capstone/Documents/` |
| SQL generator | `capstone/generate_capstone_sql_data.sql` |

---

## 2. Course README — core requirements

| Provided requirement | v2 coverage | Where |
|---|---|---|
| Intelligent query handling | ✅ | FR-001, FR-002; `03` |
| Query routing to agents | ✅ | FR-002, SLO-15; `03` |
| Multi-agent orchestration | ✅ | `03` agent topology; v1 `10` |
| Source attribution & trust | ✅ | FR-003, SR-003, SLO-10; `04` |
| Human escalation | ✅ | FR-006, FR-007, SLO-12; `04` |
| 6 technical layers (interface → synthesis) | ✅ | `03` containers |
| High-risk scenario examples (5) | ✅ | `04` E1–E8; golden C4/C5 in `05`, `08` |
| Measurable success criteria | ✅ | `08` all 16 SLOs |
| Deliverables (system, agents, RAG, SQL, docs) | ✅ | `07` prototypes + gates |
| Evaluation criteria | ✅ | `08` test pyramid + eval |
| No real investment advice | ✅ | SR-001, SR-006 |

---

## 3. Dataset spec (`capstone_finance_risk_and_investment_dataset.md`)

| Mandate | v2 | Notes |
|---|---|---|
| 7 policy PDFs (RAG) | ✅ | `05` §4 |
| 5 SQL tables + schema | ✅ | `05` §2 |
| `finance_risk_db` | ✅ | `05` |
| Scaled synthetic data (generator script) | ✅ | `05` §7; script in `capstone/` |
| Golden **50** queries | ✅ | `05`, `08` |
| Distribution **15 / 10 / 10 / 10 / 5** | ✅ | `05`, `08` |
| Categories: RAG, SQL, Hybrid, High-Risk, Escalation | ✅ | Renamed C1–C5 in v1 `11`; counts unchanged |
| Golden labels: Query Type, Risk Level, Retrieval Mode, Escalation | ⚠️ Partial in v2 | Full schema in v1 `12` — **required at build time** |
| Example query types | ⚠️ Not duplicated | v1 `11` — linked from v2 README |
| Extend not replace core dataset | ✅ | `02` DR-*; `00` standards |

---

## 4. Progress tracker — 56 tasks

### Sprint 1–3 (planning tasks 1–14)

| Task | v2 | Detail location |
|---|---|---|
| 1 Project Approach | ✅ | `01`, `02` |
| 2 Use Case & Success | ✅ | `02`; narratives v1 `09` |
| 3 System Blueprint | ✅ | `03`, `05` |
| 4 Evaluation Plan | ✅ | `08` |
| 5 Setup Readiness | ✅ | `10`; env/repo v1 `05` |
| 6 Architecture diagram | ✅ | `03` mermaid |
| 7 ADR | ✅ | `ADR_INDEX` → v1 `07` |
| 8 **Project Dashboard (Miro/Trello)** | ✅ | `13_PROJECT_DASHBOARD.md` |
| 9 Detailed use cases & SLOs | ✅ | `08`; detail v1 `09` |
| 10 Solution design | ✅ | `03`, `04`; detail v1 `10` |
| 11 Query categories | ✅ | `05`, `08`; detail v1 `11` |
| 12 Eval dataset & test strategy | ✅ | `08`; procedure v1 `12` |
| 13 Prompt engineering | ⚠️ By reference | v1 `13` (required for build) |
| 14 FastAPI setup plan | ✅ | `06`; schemas v1 `14` |

### Sprint 4–10 (implementation tasks 15–56)

| Area | v2 | Detail |
|---|---|---|
| Tasks 15–23 (data, P1, baseline) | ✅ | `07` Sprint 4 checklist |
| Tasks 24–30 (routing, guardrails, React skeleton) | ✅ | `07`, `09` |
| Tasks 31–36 (multi-agent, P2) | ✅ | `07` GATE-3 |
| Tasks 37–42 (frontend integration, load, security) | ✅ | `07`, `09`, `08` |
| Tasks 43–44 (auth, RBAC) | ✅ | `04`, `06`, `09` |
| Tasks 45–48 (security review, cost, load, prod readiness) | ✅ | `10`; checklist v1 `16` |
| Tasks 49–52 (E2E UI, P3) | ✅ | `09` UX requirements |
| Tasks 53–56 (integration, final SLO, go-live) | ✅ | `07` GATE-6, `08` |

### Task-level gaps in v2 body

| Task | Gap | Severity |
|---|---|---|
| **8** Dashboard board structure | ✅ | `13_PROJECT_DASHBOARD.md` |
| **19** MCP / Tool Integration | ✅ | `14_TOOL_AND_MCP_INTEGRATION.md` |
| **13** Full agent prompts | Not inlined in v2 | Low — v1 `13` is canonical |

---

## 5. Sixteen SLOs (tracker sheet 2)

| # | SLO | v2 |
|---|---|---|
| 1–16 | All targets | ✅ `08_TEST_AND_EVAL_STRATEGY.md` |
| 4 | Latency ≤2s | ✅ + ADR-010 tiered budgets (C3/C4/C5) in v1 |

**Hard SLOs (10–14):** explicitly called out in v2 README and `08`.

---

## 6. Add-ons (your requests — not in original course PDF)

| Feature | In v2? |
|---|---|
| Signup / login | ✅ FR-009, `06`, `09` |
| Auth DB separate from vector DB | ✅ `05` ADR-020 |
| React auth-first UI | ✅ `09` ADR-023 |
| Stock screening (Screener-like) | ⚠️ FR-011; detail v1 `17` |
| Production plan separate | ✅ Out of scope; `../production/` |
| Cloud / prod-grade engineering | ✅ `10`; detail v1 `16` |
| Opus 4.5 / Codex for agent work | ✅ v1 `20`, ADR-024 |

---

## 7. Summary scorecard

| Layer | Covered in v2 alone? | Covered with v2 + v1 refs? |
|---|---|---|
| Course core requirements | ✅ | ✅ |
| Dataset & golden set rules | ✅ (summary) | ✅ |
| 16 SLOs | ✅ | ✅ |
| Sprint 4–10 delivery | ✅ (summary) | ✅ |
| Sprint 1–3 planning tasks | ✅ 14/14 in v2 | ✅ |
| Implementation depth (prompts, GraphState, OpenAPI fields) | ⚠️ By reference | ✅ v1 `10`, `13`, `14` appendices |
| PM dashboard (Task 8) | ✅ | `13` |

---

## 8. Recommendation

**For grading / GATE-1:** v2 is sufficient **if** you declare v1 `08–14` as bound appendices (listed in v2 README).

**For implementation:** Use **v2 MASTER_PROMPT** + mandatory v1 deep refs:
- `10`, `13`, `14`, `12`, `11`, `15`

**Optional fix:** Remaining deep build specs stay in v1 `10`, `13`, `14` as appendices (linked from v2 README).

---

> Synthetic/educational data. Not investment advice.
