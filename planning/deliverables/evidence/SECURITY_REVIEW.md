# Security review — GATE-4 (Task 45)

**Date:** 5 Sep 2026  
**Scope:** Capstone local deploy (`APP_ENV=local`, `AUTH_MODE=jwt`). Synthetic/educational data only.

## Attack suite (8 types)

Source: `capstone/eval/golden/attack_suite.jsonl`. Last measured: `capstone/eval/reports/sprint7/report.md` — Guardrail Effectiveness **100%**.

| Type | What we block | Result |
|---|---|---|
| override_intent | E1 — force-approve / no-approval language | Escalated |
| regulatory_bypass | E1 — ignore policy / limits | Escalated |
| flag_suppression | E1 — hide escalation_flag | Escalated |
| prompt_injection | E1 — ignore instructions / reveal prompt | Escalated |
| role_escalation | Actor claims admin/root; RBAC still scopes SQL | Refused or scoped, no extra rows |
| data_exfiltration | Password / JWT / DSN dumps | Refused |
| advice_solicitation | “Should I buy…” | Refused + disclaimer |
| jailbreak_framing | Unrestricted / jailbreak mode | Escalated |

## Auth and RBAC

- Signup + login issue JWT. Missing/expired token → 401.
- `AUTH_MODE=stub` raises at startup when `APP_ENV=prod` (`Settings.validate_runtime`).
- SQL executor injects portfolio scope; out-of-scope rows raise `RbacViolation` → 403.
- Admin routes use `require_admin`; reindex is not public.
- Secrets live in `.env` (gitignored). `.env.example` has placeholders only.

## Cost and abuse

- `RATE_LIMIT_PER_MINUTE` (default 30) on `/api/v1/query` and `/api/v1/query/stream`.
- `MAX_TOKENS_PER_REQUEST` refuses over-budget completions.
- `DAILY_BUDGET_USD` returns 429 `budget_exceeded`.
- Estimated spend is exported as `frii_cost_usd_total` on `/metrics`.

## Honest gaps (Sprint 10 / cloud)

- No pip-audit job in CI; critical CVEs are not a merge gate.
- No WAF, TLS, or HSTS on localhost.
- Rate limit is in-process memory — not shared across replicas.
- JWT secret default is local-only; production must set a real secret (already enforced when `APP_ENV=prod`).
