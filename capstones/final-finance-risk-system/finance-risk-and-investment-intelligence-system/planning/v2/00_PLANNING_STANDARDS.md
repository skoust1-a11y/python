# v2 Planning Standards

**Version:** 2.0 · **Status:** Canonical second draft · **Supersedes:** v1 loose doc set for *new* work

---

## 1. Purpose

This folder defines how we plan, build, and verify the **Finance Risk & Investment Intelligence System** capstone. v2 fixes v1 weaknesses: fragmentation, encoding noise, unclear ownership, and weak traceability.

---

## 2. Document conventions

### 2.1 Requirement keywords (RFC 2119)

| Term | Meaning |
|---|---|
| **MUST** | Mandatory for capstone acceptance |
| **SHOULD** | Strongly recommended; deviation needs ADR |
| **MAY** | Optional / post-capstone |

### 2.2 ID schemes

| Prefix | Example | Use |
|---|---|---|
| `FR-` | FR-012 | Functional requirement |
| `NFR-` | NFR-004 | Non-functional (latency, security) |
| `SR-` | SR-003 | Safety / regulatory behaviour |
| `UC-` | UC-07 | Use case |
| `SLO-` | SLO-10 | Service level objective |
| `ADR-` | ADR-007 | Architecture decision (see `../07_ADR.md`) |
| `GATE-` | GATE-4 | Quality gate |

### 2.3 Traceability rule

Every **FR** MUST map to at least one: use case, test level, and SLO or acceptance check. Matrix: [`11_TRACEABILITY_MATRIX.md`](11_TRACEABILITY_MATRIX.md).

### 2.4 Single sources of truth

| Topic | Canonical doc |
|---|---|
| Requirements | `02_REQUIREMENTS_CATALOG.md` |
| Architecture | `03_ARCHITECTURE.md` |
| Security | `04_SECURITY_AND_COMPLIANCE.md` |
| Data | `05_DATA_ARCHITECTURE.md` |
| API | `06_API_CONTRACT.md` |
| Delivery | `07_DELIVERY_PLAN.md` |
| Testing / eval | `08_TEST_AND_EVAL_STRATEGY.md` |
| Frontend | `09_FRONTEND_UX.md` |
| Operations | `10_OPERATIONS.md` |
| ADRs | `../07_ADR.md` + `ADR_INDEX.md` |
| Agent execution | `MASTER_PROMPT_v2.md` |

v1 files (`01`–`20` at parent) remain **reference archive**; do not extend them—extend v2.

### 2.5 Quality bar for v2 edits

- UTF-8 only; no replacement characters.
- Tables over prose walls where possible.
- Every section answers: *who*, *what*, *how verified*.
- No duplicate ADR text—link instead.
- Capstone vs production: capstone only in v2; production stays in `../production/`.

---

## 3. Definition of Ready (DoR) — Sprint N

- [ ] Prior gate passed with written evidence
- [ ] Requirements for sprint tagged in catalog
- [ ] API contract changes (if any) noted in `06`
- [ ] Eval pass criteria for sprint defined in `08`
- [ ] Risks for sprint reviewed in `07`

## 4. Definition of Done (DoD) — Sprint N

- [ ] All sprint FRs implemented or explicitly deferred with ADR
- [ ] `python -m eval.run --suite golden` (or sprint subset) executed; report in `eval/reports/`
- [ ] Hard SLOs (SLO-10–14) pass on committed report
- [ ] Refactors (prompts, routing, retrieval, SQL templates, guardrail rules) cite the failing SLO + query ids they move — no score, no refactor
- [ ] No secrets in repo; README/runbook updated if ops changed
- [ ] Tracker tasks marked with evidence links

---

## 5. Agent model (human + Cursor)

Planning and implementation in Cursor **MUST** use **Claude Opus 4.5** or **Codex High** (`../20_AI_Agent_Model_Policy.md`).

---

> Educational / synthetic data only. Not investment advice.
