# sprint9 — Prototype 3

Generated: 2026-09-05

Prototype 3 is the auth-first React app served from `capstone/frontend/dist` on the FastAPI process.

## Product path (Task 49–52)

1. Login at `/login` (`analyst@local` / `Password123`) → `/app`.
2. Query workspace uses `POST /api/v1/query/stream`.
3. Answered queries stream tokens, then show citations and the routing panel.
4. Escalated or refused outcomes emit `escalation` and **do not** emit `token`. The override sample chip is hidden (UX-005).
5. Disclaimer footer is on every envelope.

## Checks

| Check | Evidence |
|---|---|
| Stream skips tokens on escalate | `tests/test_api.py::test_stream_skips_tokens_on_escalation` |
| Citations + routing in UI | `QueryPage` + `CitationList` + `RoutingPanel` |
| Restricted actions | Action chips dropped when `outcome` is `escalated` or `refused` |
| Auth gate | Unauthenticated `/api/v1/query` is 401; UI routes under `/app` |

## SLOs

Same measured table as Sprint 8 (`eval/reports/sprint8/report.md`). Hard SLOs 10–14 still PASS. Load p95 on sequential golden replay: **18.2 ms** (target 2000 ms).

Playwright is not in this repo. GATE-5 is signed on the API tests + rebuilt `dist` + this note, not a recorded browser video.

> Synthetic/educational data. Not investment advice.
