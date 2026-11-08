# Security & Compliance (v2)

---

## 1. Threat summary

| Threat | Control | Req |
|---|---|---|
| Override / ignore regulatory intent | E1 input guard + refusal templates | SR-002, FR-006 |
| Hallucinated policy limits | Citation-or-refuse synthesis | SR-003 |
| SQL injection | Parameterized templates only | FR-004 |
| Cross-portfolio data leak | RBAC at SQL executor | SR-005, ADR-014 |
| Stub auth in production | Fail-fast config | ADR-016 |
| Credential exposure | Env + secret manager | NFR-009 |
| Prompt injection via user query | Input filters + no tool-less bypass | SR-002 |

---

## 2. Authentication

| Phase | Behaviour |
|---|---|
| Sprint 4–7 | `AUTH_MODE=stub` for API dev only; React UI still built |
| Sprint 8+ | Signup, login, JWT; prod refuses stub |

**Signup default:** `analyst`, empty `portfolio_ids` until admin assigns (ADR-019).

---

## 3. Authorization matrix

| Role | Query | Portfolios | Escalations | Admin | Evidence debug |
|---|---|---|---|---|---|
| analyst | Yes | assigned | own | No | No |
| risk_manager | Yes | all | all | No | No |
| compliance | Yes | all | all | traces | Yes |
| admin | Yes | all | all | Yes | No |

Enforcement: `app/sqlq/executor.py` — not prompts.

---

## 4. Escalation rules (E1–E8 summary)

| Rule | Trigger (deterministic) |
|---|---|
| E1 | Override/bypass regulatory or risk language (pre-router) |
| E2 | Any `escalation_flag=TRUE` in result set |
| E3 | `risk_score > 80` or stale high-risk assessment |
| E4 | Policy claim contradicts observed data |
| E5 | High-risk decision without required assessment |
| E6 | Regulatory limit breach vs holdings |
| E7 | Conflicting agent risk signals |
| E8 | Insufficient evidence for high-risk approval question |

Full spec: `../10_Detailed_Solution_Design.md` §4.

---

## 5. Compliance posture (capstone)

- Educational / synthetic data disclaimer on every response.
- Not a substitute for licensed investment advice.
- Audit: `trace_id` + structured logs; compliance role may fetch `/admin/traces/{id}`.

---

## 6. Security test obligations

- [ ] Attack suite 100% guardrail effectiveness
- [ ] Golden set RBAC run under 3 roles — diff must be scope-only
- [ ] Dependency scan in CI
- [ ] No secrets in `git grep` / eval reports
