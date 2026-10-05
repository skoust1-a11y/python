# Delivery Plan (v2)

Aligned to `work tracker/FinalProgressTracker_revised.xlsx` (56 tasks, 10 sprints).

---

## 1. Sprint map

| Sprint | Theme | Key outcomes | Gate |
|---|---|---|---|
| 1–3 | Planning | v2 docs, ADRs, API contract | **GATE-1** |
| 4 | Data foundation | DBs, RAG, golden set, P1 C1/C2/C5 | **GATE-2** |
| 5 | Routing & safety | Router ≥95%, E1–E8, React auth shell | — |
| 6 | Multi-agent | C3/C4 paths, P2 | **GATE-3** |
| 7 | Integration | React query UI, complex golden | — |
| 8 | Hardening | JWT signup/login, RBAC, load | **GATE-4** |
| 9 | Product UX | Streaming, screens UI, P3 | **GATE-5** |
| 10 | Release | Final eval, deploy dry-run | **GATE-6** |

---

## 2. Prototypes

| # | Sprint | Proves |
|---|---|---|
| P1 | 4 | Grounded single-hop + refusal |
| P2 | 6 | Hybrid + high-risk multi-agent |
| P3 | 9 | Full React E2E with auth |

---

## 3. Sprint 4 checklist (critical path)

1. Create both DBs + extensions
2. Apply schema + seed + `golden_extensions.sql`
3. Ingest 7 PDFs; smoke 20 retrieval probes
4. Commit `golden_queries.jsonl` (50)
5. Implement 18 SQL templates + executor RBAC hooks — see [`14_TOOL_AND_MCP_INTEGRATION.md`](14_TOOL_AND_MCP_INTEGRATION.md)
6. LangGraph: C1, C2, C5 paths
7. Baseline eval → `eval/reports/sprint4_baseline/`

---

## 4. Quality gates (evidence required)

| Gate | Evidence artifact |
|---|---|
| GATE-1 | Signed [`GATE_1_SIGNOFF.md`](GATE_1_SIGNOFF.md) + frozen `06_API_CONTRACT.md` |
| GATE-2 | sprint4 eval report; P1 demo script |
| GATE-3 | sprint6 eval; routing + escalation green |
| GATE-4 | load test summary; security checklist `../16` §6 |
| GATE-5 | E2E test log; P3 screenshot or recording |
| GATE-6 | final SLO table; all hard SLOs pass |

---

## 5. Risk register (top 5)

| ID | Risk | Mitigation |
|---|---|---|
| R1 | Latency vs multi-agent depth | ADR-010 tiered budgets |
| R2 | PDF table extraction | Manual QA GATE-2 |
| R3 | Escalation miss | P0 runbook; deterministic E1–E8 |
| R4 | Timeline compression | Thin slices; defer non-MoSCoW |
| R5 | Contract churn | v2 API frozen; additive only |

---

## 6. MoSCoW deferral

**Could (post–Sprint 10):** WebSocket screens, broker sync, production plan P1+.

**Must not defer:** SLO-10–14, golden 50, signup/login, React auth gate.
