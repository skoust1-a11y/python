# Planning v2 — Finance Risk & Investment Intelligence System

**Canonical for capstone delivery · GATE-6 signed 7 Sep 2026** — [`GATE_6_SIGNOFF.md`](GATE_6_SIGNOFF.md)

---

## What this is

A consolidated, standards-based plan for the capstone: multi-agent RAG + SQL, guardrails, React auth-first UI, synthetic data, separate auth/finance databases, optional stock screening.

**Production** (user-owned data + real-time market) remains separate: [`../production/`](../production/).

---

## Quick start

1. **Human:** Set Cursor to **Claude Opus 4.5** or **Codex High** ([`../20_AI_Agent_Model_Policy.md`](../20_AI_Agent_Model_Policy.md)).
2. **Review:** Read [`01_EXECUTIVE_SUMMARY.md`](01_EXECUTIVE_SUMMARY.md) → [`02_REQUIREMENTS_CATALOG.md`](02_REQUIREMENTS_CATALOG.md).
3. **Build:** Paste [`MASTER_PROMPT_v2.md`](MASTER_PROMPT_v2.md).

---

## Document map

| # | Document | Purpose |
|---|---|---|
| 00 | [Planning standards](00_PLANNING_STANDARDS.md) | RFC 2119, IDs, DoR/DoD |
| 01 | [Executive summary](01_EXECUTIVE_SUMMARY.md) | Vision, gates, stack |
| 02 | [Requirements catalog](02_REQUIREMENTS_CATALOG.md) | FR / NFR / SR |
| 03 | [Architecture](03_ARCHITECTURE.md) | C4, agents, invariants |
| 04 | [Security & compliance](04_SECURITY_AND_COMPLIANCE.md) | RBAC, E1–E8, threats |
| 05 | [Data architecture](05_DATA_ARCHITECTURE.md) | Two DBs, golden set |
| 06 | [API contract](06_API_CONTRACT.md) | Endpoints, envelope — **frozen GATE-1** |
| 07 | [Delivery plan](07_DELIVERY_PLAN.md) | Sprints, gates, risks |
| 08 | [Test & eval](08_TEST_AND_EVAL_STRATEGY.md) | Pyramid, 16 SLOs |
| 09 | [Frontend UX](09_FRONTEND_UX.md) | React auth-first |
| 10 | [Operations](10_OPERATIONS.md) | Obs, runbooks, deploy |
| 11 | [Traceability matrix](11_TRACEABILITY_MATRIX.md) | Req → test → SLO |
| 12 | [Coverage audit](12_COVERAGE_AUDIT.md) | v2 vs course docs & tracker |
| 13 | [Project dashboard](13_PROJECT_DASHBOARD.md) | Task 8 — Trello/Miro, 56 cards, gates |
| 14 | [Tool & MCP integration](14_TOOL_AND_MCP_INTEGRATION.md) | Task 19 — SQL registry, retrieval tools |
| — | [ADR index](ADR_INDEX.md) | Links to `../07_ADR.md` |
| — | [Master prompt v2](MASTER_PROMPT_v2.md) | Agent execution |
| — | [Changelog v1→v2](CHANGELOG_v1_to_v2.md) | What improved |
| — | [GATE-1 sign-off](GATE_1_SIGNOFF.md) | Sprint 1–3 closed; API frozen |
| — | [GATE-2 … GATE-6](GATE_6_SIGNOFF.md) | Prototype → go-live; see also GATE_2…5 |

---

## Deep reference (v1 archive)

Use when v2 points you here — do not duplicate:

| Topic | v1 file |
|---|---|
| GraphState, E1–E8 detail, SQL templates | `../10_Detailed_Solution_Design.md` |
| Agent prompts | `../13_Prompt_Engineering_Framework.md` |
| OpenAPI field-level schemas | `../14_FastAPI_Service_Setup_Plan.md` |
| Use case narratives | `../09_Detailed_Use_Case_and_SLO.md` |
| Golden set procedure | `../12_Evaluation_Dataset_and_Test_Strategy.md` |
| Sprint prompts | `../15_COMPLETION_PROMPTS.md` |
| Screening feature | `../17_Stock_Screening_Feature.md` |

---

## Gates

| Gate | Sign-off criteria |
|---|---|
| GATE-1 | **SIGNED 29 Aug 2026** — v2 + frozen API ([`GATE_1_SIGNOFF.md`](GATE_1_SIGNOFF.md)) |
| GATE-2 | **SIGNED** — Prototype 1 ([`GATE_2_SIGNOFF.md`](GATE_2_SIGNOFF.md)) |
| GATE-3 | **SIGNED** — Prototype 2 ([`GATE_3_SIGNOFF.md`](GATE_3_SIGNOFF.md)) |
| GATE-4 | **SIGNED 5 Sep 2026** — Auth, load, security ([`GATE_4_SIGNOFF.md`](GATE_4_SIGNOFF.md)) |
| GATE-5 | **SIGNED 5 Sep 2026** — React Prototype 3 ([`GATE_5_SIGNOFF.md`](GATE_5_SIGNOFF.md)) |
| GATE-6 | **SIGNED 7 Sep 2026** — Final SLO + deploy dry-run ([`GATE_6_SIGNOFF.md`](GATE_6_SIGNOFF.md)) |

---

## Hard SLOs (zero tolerance)

Source attribution **100%** · Escalation recall **100%** · Guardrails **100%** · RBAC violations **0**

---

> Synthetic/educational data. Not investment advice.
