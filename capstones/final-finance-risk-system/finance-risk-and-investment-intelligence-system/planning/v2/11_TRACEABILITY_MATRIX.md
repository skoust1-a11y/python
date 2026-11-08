# Traceability Matrix (v2)

Maps requirements → use cases → tests → SLOs.

| Req ID | Use case / flow | Test | SLO |
|---|---|---|---|
| FR-001 | UC query submit | API integration | SLO-08 |
| FR-002 | Router classification | Golden routing labels | SLO-15 |
| FR-003 | C1 policy Q | Golden C1 + faithfulness | SLO-01,10 |
| FR-004 | C2 SQL lookup | Template unit + golden C2 | SLO-09 |
| FR-005 | C3 hybrid | Golden C3 | SLO-08,10 |
| FR-006 | C5 escalation | Attack suite | SLO-12,14 |
| FR-007 | E1–E8 | `test_escalation_rules.py` | SLO-12 |
| FR-008 | Synthesis tool-less | Node integration | SLO-10 |
| FR-009 | Signup/login | API + E2E | — |
| FR-010 | Auth-first UI | Playwright E2E | — |
| FR-011 | Screen run | screen_queries.jsonl | SLO-09 |
| FR-012 | Saved screens | Auth DB + API | — |
| FR-013 | Session memory | Integration turns | — |
| FR-014 | Admin scope assign | RBAC integration | SLO-13 |
| FR-015 | Streaming query | SSE contract + UI | — |
| FR-016 | Evidence mode toggle | Contract 409 + UI disable when off | — (post-capstone) |
| NFR-001–004 | Latency | load_runner | SLO-04 |
| NFR-008 | Observability | Manual trace review | — |
| SR-001 | Non-advice | output validator | SLO-14 |
| SR-003 | Citation or refuse | golden + validator | SLO-10 |
| SR-005 | Portfolio scope | RBAC golden × roles | SLO-13 |
| DR-004 | Golden 50 | eval.run | SLO-08 |

**Coverage rule:** Every **M** priority FR MUST appear above. Gap = planning defect.

Use case detail: v1 `../09_Detailed_Use_Case_and_SLO.md`.
