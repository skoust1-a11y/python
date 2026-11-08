# Requirements Catalog (v2)

MoSCoW: **M** = Must (capstone), **S** = Should, **C** = Could (post-capstone).

---

## 1. Functional requirements

| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| FR-001 | M | System SHALL accept natural-language financial queries via REST API | `POST /api/v1/query` returns valid envelope |
| FR-002 | M | System SHALL classify each query into exactly one category C1–C5 | Routing accuracy ≥95% on golden set |
| FR-003 | M | C1 answers SHALL be grounded in policy corpus with doc citations | SLO-10 = 100% |
| FR-004 | M | C2 answers SHALL use parameterized SQL templates only | SQL correctness ≥95%; no raw LLM SQL |
| FR-005 | M | C3/C4 SHALL combine RAG + SQL evidence in one response | Both citation types when category requires |
| FR-006 | M | C5 / override intent SHALL refuse and escalate | SLO-12, SLO-14 = 100% |
| FR-007 | M | System SHALL enforce E1–E8 escalation rules in code | Unit tests + attack suite |
| FR-008 | M | Synthesis SHALL not use tools; only compose from evidence bundle | Integration test per category |
| FR-009 | M | Users SHALL register via signup and authenticate via login | JWT after Sprint 8 |
| FR-010 | M | React UI SHALL show login/signup before any feature route | E2E: unauthenticated `/app` → `/login` |
| FR-011 | S | Stock screening SHALL run whitelist filters on synthetic equities | `POST /screens/run` + ADR-021 |
| FR-012 | S | Users MAY save named screen definitions | Auth DB `saved_screens` |
| FR-013 | M | Session memory SHALL retain last 5 turns per session | ADR-006 |
| FR-014 | M | Admin SHALL assign portfolio scope to new analysts | PATCH admin users |
| FR-015 | S | Streaming query endpoint for long answers | Sprint 9 SSE |
| FR-016 | C | Query page MAY switch evidence: documents only (`corpus`) vs documents + current market/news (`current`) | Default `corpus`; `current` requires providers; capstone stays `corpus` |

---

## 2. Non-functional requirements

| ID | Priority | Requirement | Target |
|---|---|---|---|
| NFR-001 | M | C1/C2 p95 latency | ≤2s |
| NFR-002 | S | C3 p95 latency | ≤4s |
| NFR-003 | S | C4 p95 latency | ≤6s |
| NFR-004 | M | C5 p95 latency | ≤1.5s |
| NFR-005 | M | Task success rate on golden set | ≥90% |
| NFR-006 | M | Availability (local/demo) | Single-instance; health/ready probes |
| NFR-007 | S | Horizontal scale readiness | Stateless app; DB externalized |
| NFR-008 | M | Structured JSON logs + trace per request | OTel spans per graph node |
| NFR-009 | M | Secrets never in git or logs | ADR-016 |
| NFR-010 | S | Dependency CVE gate in CI | pip-audit critical = block |

---

## 3. Safety requirements

| ID | Requirement | Verification |
|---|---|---|
| SR-001 | MUST NOT provide buy/sell/hold recommendations | Prompt + output validator tests |
| SR-002 | MUST NOT explain how to bypass risk controls | Guardrail attack suite |
| SR-003 | MUST NOT answer with zero citations when outcome=answered | SLO-10 |
| SR-004 | MUST escalate when `escalation_flag=TRUE` in scope | SLO-12 |
| SR-005 | MUST NOT return out-of-scope portfolio rows | RBAC executor tests; SLO-13 |
| SR-006 | MUST include educational disclaimer on every response | UI + API contract |

---

## 4. Data requirements

| ID | Requirement |
|---|---|
| DR-001 | Course 7 PDFs MUST be indexed with page/section metadata |
| DR-002 | Finance DB MUST contain 5 mandated tables + scaled seed counts |
| DR-003 | Auth DB MUST be separate from finance/vector DB (ADR-020) |
| DR-004 | Golden set MUST be 50 queries: 15/10/10/10/5 distribution |
| DR-005 | Risk semantics: Low <30, Medium 30–69, High ≥70; flag if >80 |

---

## 5. Personas

| Persona | Needs | RBAC |
|---|---|---|
| Analyst | Policy + portfolio Q&A | Assigned portfolios |
| Risk manager | Cross-portfolio risk | All portfolios |
| Compliance | Audit, traces | Read + traces |
| Admin | Users, reindex, eval | Admin endpoints |

---

> Full use-case narratives: v1 `../09_Detailed_Use_Case_and_SLO.md` (reference). v2 traceability: `11_TRACEABILITY_MATRIX.md`.
