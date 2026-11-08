# Frontend UX (v2)

Stack: **React 18 + TypeScript + Vite + React Router** (ADR-023). Detail: `../19_React_Frontend_Plan.md`.

---

## 1. Principle: auth before features

Unauthenticated users **MUST** only see login and signup. All product capability lives under `/app/*` behind JWT.

---

## 2. Route map

| Route | Access | Purpose |
|---|---|---|
| `/` | Public | Redirect by session |
| `/login` | Public | Email + password |
| `/signup` | Public | Register → login |
| `/app` | Protected | Query workspace |
| `/app/screens` | Protected | Screen builder |
| `/app/screens/:id` | Protected | Saved screen |
| `/app/escalations` | Protected | Role-gated |
| `/app/admin/*` | Protected | Admin only |

---

## 3. UX requirements

| ID | Requirement |
|---|---|
| UX-001 | Login and signup on first visit; no feature chrome visible |
| UX-002 | 401 clears token and redirects to login |
| UX-003 | Every query response shows disclaimer footer |
| UX-004 | Citations clickable (doc title + section/page or SQL query id) |
| UX-005 | Escalated/refused outcomes hide action affordances |
| UX-006 | Routing panel shows category + agents used |
| UX-007 | Logout returns to login |
| UX-008 | Query page: toggle **Documents only** vs **Documents + current**; send `options.evidence_mode`; disable current when `features.current_factors` is false |

---

## 4. Sprint UX delivery

| Sprint | Deliverable |
|---|---|
| 5 | Auth pages + ProtectedRoute + `/app` placeholder |
| 7 | Query UI + citations + routing panel |
| 8 | Real JWT wiring; role-based nav |
| 9 | Streaming, screens, escalation banner, export CSV |

---

## 5. Component inventory

- `AuthLayout`, `AppLayout`
- `LoginPage`, `SignupPage`
- `QueryPage`, `CitationList`, `RoutingPanel`, `EscalationBanner`, `Disclaimer`
- `ScreensPage`, `ScreenBuilder`, `ResultsTable`
- `AuthContext`, `ProtectedRoute`, `api/client.ts`

---

## 6. E2E scenarios (minimum)

1. Visit `/app` logged out → `/login`
2. Signup → login → `/app` visible
3. Submit query → citations + disclaimer render
4. Logout → `/login`; `/app` blocked
