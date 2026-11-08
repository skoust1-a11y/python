# Project Dashboard (v2) — Task 8

Trello/Kanban board mirroring `work tracker/FinalProgressTracker_revised.xlsx` (56 tasks, 16 SLOs, 6 gates).

---

## 1. Board setup

| Field | Value |
|---|---|
| Name | `Finance Risk & Investment Intelligence — Capstone` |
| Timeline | 25 Aug 2026 – 20 Sep 2026 (batch end 26 Sep 2026) |
| Source of truth | Excel tracker wins on conflict |
| Live board | [`../deliverables/dashboard/index.html`](../deliverables/dashboard/index.html) |

---

## 2. Columns & WIP

| Column | WIP | Exit criteria |
|---|---|---|
| Backlog — All Sprints | — | Sprint active + planned |
| Sprint Ready | 10 | Owner, AC, v2 doc ref |
| In Progress | 6 board / 3 per person | Work started |
| Blocked | 3 | Blocker note + owner |
| In Review | 4 | PR or doc review |
| **Eval / SLO Check** | 4 | Eval report attached; SLOs pass |
| Done | — | Evidence linked |
| Gate Review (swimlane) | 1 | Gate signed |

> Functional work is not Done until eval evidence exists.

---

## 3. Labels

**Sprints:** `S1` … `S10`

**Tracks:** `TRACK:PLAN` (1–3) · `TRACK:DATA` (4–7) · `TRACK:BACKEND` (4–8) · `TRACK:FRONTEND` (5–9) · `TRACK:RELEASE` (10)

**Type:** `TYPE:DOC` `TYPE:CODE` `TYPE:DATA` `TYPE:EVAL` `TYPE:SECURITY` `TYPE:INFRA` `TYPE:PROTOTYPE`

**Priority:** `P0-SAFETY` (hard SLO) · `P1` · `P2`

**SLO:** `SLO:TSR` `SLO:ATTRIBUTION` `SLO:ESCALATION` `SLO:GUARDRAIL` `SLO:RBAC` `SLO:ROUTING` `SLO:SQL` `SLO:LATENCY` (+ others from `08_TEST`)

---

## 4. Card template

```markdown
### Task
Sprint N — Task M — <name>

### Planning reference
v2/<doc>.md §<section>  OR  v1 ../10|13|14 for deep detail

### Acceptance criteria
- [ ] ...

### SLOs touched
...

### Evidence in Done
- [ ] eval/reports/sprintN/report.md
- [ ] tests/...
- [ ] Reviewer: ...

### DoD
Clean clone runs · eval executed · hard SLOs green · tracker updated
```

**Code card checklist:** Tests · span/log · citations (if answer path) · escalation unaffected · cost logged.

---

## 5. All 56 cards (summary)

### S1 — Planning (`TRACK:PLAN`)
| T | Task | v2 / evidence |
|---|---|---|
| 1 | Project Approach | `01`, `02` |
| 2 | Use Case & Success | `02`, v1 `09` |
| 3 | System Blueprint | `03`, `05` |
| 4 | Evaluation Plan | `08` |
| 5 | Setup Readiness | `10`, v1 `05` |

### S2 — Architecture
| T | Task | v2 / evidence |
|---|---|---|
| 6 | Architecture diagram | `03` mermaid |
| 7 | ADR | `ADR_INDEX`, v1 `07` |
| 8 | **This dashboard** | Board live, 56 cards |

### S3 — Detailed design
| T | Task | v2 / evidence |
|---|---|---|
| 9 | Use cases & SLOs | `08`, v1 `09` |
| 10 | Solution design | v1 `10`, `03` |
| 11 | Query categories | v1 `11`, `05` |
| 12 | Eval dataset strategy | `08`, v1 `12` |
| 13 | Prompt framework | v1 `13` |
| 14 | FastAPI plan | `06`, v1 `14` |
| — | **GATE-1** | v2 signed + API frozen |

### S4 — Data & knowledge
| T | Task | SLO labels |
|---|---|---|
| 15 | Golden dataset | TSR |
| 16 | Vector index + retrieval | CTX-PRECISION, RECALL |
| 17 | SQL schema + scaled data | SQL |
| 18 | Memory strategy | — |
| 19 | **Tool integration** | SQL — see `14_TOOL_AND_MCP_INTEGRATION.md` |
| 20 | Logging & tracing | — |
| 21 | Baseline metrics | TSR, LATENCY, ATTRIBUTION |
| 22 | Cost tracking | — |
| 23 | Prototype 1 | ATTRIBUTION |
| — | **GATE-2** | sprint4 baseline report |

### S5 — Routing & safety
| T | Task | SLO labels |
|---|---|---|
| 24 | RAG/SQL/Hybrid routing | ROUTING |
| 25 | Tool errors & retries | TSR |
| 26 | Escalation E1–E8 | ESCALATION, CMR, P0 |
| 27 | Guardrails | GUARDRAIL, P0 |
| 28 | Golden retest | TSR, ACCURACY |
| 29 | Latency optimization | LATENCY |
| 30 | React auth skeleton | — (`09`) |

### S6 — Multi-agent
| T | Task | SLO labels |
|---|---|---|
| 31 | Multi-step reasoning | TSR |
| 32 | Hybrid consistency | FAITHFULNESS |
| 33 | Dynamic tool selection | SQL |
| 34 | 7-agent orchestration | TSR |
| 35 | Escalation revalidation | ESCALATION, GUARDRAIL |
| 36 | Prototype 2 | — |
| — | **GATE-3** | sprint6 eval |

### S7 — Integration
T37 Frontend integration · T38 Complex golden · T39 TSR lift · T40 Load SLO · T41 Security · T42 Observability

### S8 — Hardening
T43 Auth/session · T44 RBAC · T45 Security review · T46 Cost guardrails · T47 Load test · T48 Prod readiness · **GATE-4**

### S9 — Product
T49 E2E UI · T50 Citations/routing UI · T51 Restricted actions UX · T52 Prototype 3 · **GATE-5**

### S10 — Release
T53 E2E integration · T54 Performance · T55 Final SLO · T56 Go-live · **GATE-6**

---

## 6. SLO wall (Miro frame or Trello list)

Track all 16 SLOs after each eval: target vs S4→S10 measured values. Hard SLOs (10–14) highlighted red if fail.

---

## 7. Rituals

| Ritual | When | Output |
|---|---|---|
| Standup | Daily | Blocked cards ≤3 |
| Sprint planning | Sprint start | Cards → Sprint Ready |
| Eval review | Sprint end | SLO wall update |
| Gate review | Gate column | Sign-off note on gate card |

---

## 8. Task 8 done criteria

- [x] Board created with 8 columns + labels — [`../deliverables/dashboard/index.html`](../deliverables/dashboard/index.html)
- [x] All 56 task cards + 6 gate cards
- [x] SLO wall template
- [x] Eval/SLO column is a required step before Done (board + this spec)
