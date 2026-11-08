# Production readiness review — GATE-4 (Task 48)

Checklist against `planning/16_Production_and_Cloud_Readiness.md` §6. Capstone local bar, not a cloud go-live.

## Filled 5 Sep 2026

### Security

| Item | Capstone status |
|---|---|
| Secrets via env; `.env` gitignored | Pass |
| TLS / HSTS at edge | Not applicable on localhost |
| `AUTH_MODE=jwt` tested; stub blocked in prod | Pass |
| RBAC executor: 0 unauthorized rows | Pass (eval SLO-13 = 0) |
| Dependency scan in CI | Still missing — optional cloud CI; not a GATE-6 blocker |
| Admin routes require admin | Pass |
| Rate limit / body size on query | Rate limit Pass; body size uses FastAPI defaults |

### Safety / finance domain

| Item | Status |
|---|---|
| E1–E8 + attack suite; escalation recall 1.0 | Pass |
| Guardrail effectiveness 1.0 | Pass |
| Source attribution 1.0 | Pass |
| Disclaimer on answers and refusals | Pass |

### Observability & ops

| Item | Status |
|---|---|
| JSON logs with trace_id / category / latency / cost / escalated | Pass (structured logs present) |
| OTel spans per graph node | Still missing — designed, not wired; structlog + `/metrics` cover local ops |
| Prometheus `/metrics` | Pass (request counter + cost counter) |
| Runbooks without SSH | Local only — see `planning/v2/10_OPERATIONS.md` |
| `MAX_TOKENS_PER_REQUEST` + `DAILY_BUDGET_USD` | Pass |

### Performance

| Item | Status |
|---|---|
| Load test p95 vs ADR-010 (C1/C2 ≤ 2s) | Pass on sequential golden replay — see sprint8 report |
| 2-replica smoke, no sticky sessions | Not run (single local process); k8s sketch sets replicas: 2 |
| DB indexes / EXPLAIN | Seed schema only; no formal EXPLAIN pack |

### Release

| Item | Status |
|---|---|
| Idempotent migrations | SQL bootstrap/seed is rerunnable |
| `deploy/` stubs | Pass — `deploy/Dockerfile`, `compose.prod.yml`, `k8s/` sketches |
| This review signed | Yes — GATE-4 5 Sep 2026; deploy artifacts closed under GATE-6 7 Sep 2026 |

## Decision

**GATE-4** signed the capstone backend hardening. **GATE-6** closed the image/compose dry-run package. pip-audit CI, OTel exporter, and two-replica load smoke remain optional cloud follow-ups. Do not claim a production VPC deploy from this review.
