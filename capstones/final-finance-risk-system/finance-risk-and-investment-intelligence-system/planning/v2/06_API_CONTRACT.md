# API Contract (v2)

**Frozen at GATE-1 (29 August 2026).** Additive changes only until `/api/v2`. Full schemas: `../14_FastAPI_Service_Setup_Plan.md`. Sign-off: [`GATE_1_SIGNOFF.md`](GATE_1_SIGNOFF.md).

Base: `/api/v1` · Auth: `Bearer JWT` (except public auth routes)

---

## 1. Endpoint map

| Method | Path | Auth | Sprint |
|---|---|---|---|
| POST | `/auth/signup` | Public | 8 |
| POST | `/auth/login` | Public | 8 |
| GET | `/auth/me` | JWT | 8 |
| POST | `/query` | JWT | 4 |
| POST | `/query/stream` | JWT | 9 |
| GET | `/sessions/{id}/turns` | JWT | 5 |
| DELETE | `/sessions/{id}` | JWT | 5 |
| GET | `/screens/fields` | JWT | 4 |
| POST | `/screens/run` | JWT | 4 |
| POST | `/screens/from-nl` | JWT | 6 |
| GET/POST | `/screens` | JWT | 8 |
| GET | `/health` | Public | 4 |
| GET | `/health/ready` | Public | 4 |
| GET | `/metrics` | Internal | 4 |
| POST | `/admin/reindex` | admin | 4 |
| GET | `/admin/traces/{trace_id}` | admin/compliance | 4 |
| PATCH | `/admin/users/{user_id}` | admin | 8 |

---

## 2. Response envelope (normative)

```json
{
  "trace_id": "string",
  "session_id": "string",
  "outcome": "answered | refused | escalated | insufficient_evidence",
  "answer": "markdown",
  "citations": [],
  "routing": { "category": "C1_RAG", "agents": [], "confidence": 0.0 },
  "risk": { "level": "Low|Medium|High", "any_escalation_flag": false },
  "escalation": { "required": false, "triggers": [], "escalation_id": null },
  "disclaimer": "string",
  "confidence": 0.0
}
```

**Client rules:** branch on `outcome`, not answer text; always render `disclaimer`; `answered` ⇒ `citations.length >= 1`.

**Additive (post GATE-1):** `POST /query` accepts `options.evidence_mode`: `corpus` (default) or `current`. Response echoes `evidence_mode_used`. Full rules: `../14_FastAPI_Service_Setup_Plan.md` §3.6.

---

## 3. Error model

| Code | Meaning |
|---|---|
| 400 | Validation |
| 401 | Missing/invalid JWT → client clears token, `/login` |
| 403 | RBAC scope violation |
| 409 | Signup duplicate email **or** `evidence_mode=current` while current factors are off |
| 422 | Screen definition invalid |
| 503 | `/health/ready` failed |

---

## 4. CORS

Dev: `http://localhost:5173`. Prod: explicit frontend origin — no `*`.

---

## 5. Contract tests

- [ ] OpenAPI generated from FastAPI matches this map
- [ ] Pydantic invariants from v1 `14` §3 enforced in unit tests
- [ ] Frontend types generated or hand-maintained to match envelope
