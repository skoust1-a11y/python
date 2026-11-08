# Backend endpoints vs `planning/v2/06_API_CONTRACT.md`

Base `/api/v1` except health/metrics/admin aliases. Auth: Bearer JWT unless Public.

| Contract | Implemented | Auth | Notes |
|---|---|---|---|
| POST `/auth/signup` | `/api/v1/auth/signup` | Public | 409 duplicate email |
| POST `/auth/login` | `/api/v1/auth/login` | Public | also `/auth/token` alias |
| GET `/auth/me` | `/api/v1/auth/me` | JWT | |
| POST `/query` | `/api/v1/query` | JWT | envelope; `current` → 409 |
| POST `/query/stream` | `/api/v1/query/stream` | JWT | SSE |
| GET `/sessions/{id}/turns` | `/api/v1/sessions/{id}/turns` | JWT | |
| DELETE `/sessions/{id}` | `/api/v1/sessions/{id}` | JWT | |
| GET `/screens/fields` | `/api/v1/screens/fields` | JWT | |
| POST `/screens/run` | `/api/v1/screens/run` | JWT | |
| POST `/screens/from-nl` | `/api/v1/screens/from-nl` | JWT | |
| GET/POST `/screens` | `/api/v1/screens` | JWT | + get/put/delete/export |
| GET `/health` | `/health` | Public | |
| GET `/health/ready` | `/health/ready` | Public | |
| GET `/metrics` | `/metrics` | Internal | Prometheus |
| POST `/admin/reindex` | `/admin/reindex` | admin | |
| GET `/admin/traces/{id}` | `/admin/traces/{id}` | admin/compliance | |
| PATCH `/admin/users/{id}` | `/admin/users/{id}` and `/api/v1/admin/users/{id}` | admin | |

Additive (allowed): documents list, escalations queue, templates catalog, eval latest.
Source: `capstone/app/api/routers.py` + `capstone/app/main.py`.
How to re-run: `ENDPOINT_VERIFICATION_PROCEDURE.md`.
