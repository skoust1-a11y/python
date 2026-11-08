# 19 — React Frontend Plan
**Task 30+ / Sprint 5–9 — binds ADR-011 (updated) and ADR-023**

Stack: **React 18 + TypeScript + Vite + React Router**. No Next.js for capstone (keep deploy simple behind FastAPI static or separate CDN).

---

## 1. Auth-first UX (mandatory)

**Rule:** The first thing a user sees is **Login** or **Sign up**. No query, screening, or dashboard until authenticated.

| Route | Auth | Purpose |
|---|---|---|
| `/` | Public | Redirect → `/login` if no token; → `/app` if token valid |
| `/login` | Public | Email + password → JWT |
| `/signup` | Public | Register → success → `/login` (or auto-login if backend returns token) |
| `/app` | **Protected** | Home / query workspace |
| `/app/screens` | **Protected** | Stock screen builder (`17`) |
| `/app/screens/:id` | **Protected** | Saved screen |
| `/app/escalations` | **Protected** | risk_manager / compliance |
| `/app/admin/*` | **Protected** | admin role only |

**ProtectedRoute:** if no valid JWT → `Navigate` to `/login` with `state.from` for post-login redirect.  
**PublicOnlyRoute:** if already logged in → redirect to `/app` (so `/login` and `/signup` are not shown when session exists).

All `/api/v1/*` calls (except auth signup/login) send `Authorization: Bearer <token>`. On **401** → clear token, redirect `/login`.

---

## 2. Landing / first page layout

Single **Auth layout** (no app chrome):

```
┌─────────────────────────────────────┐
│  Finance Risk & Investment Intel.   │
│                                     │
│   [ Log in ]    [ Sign up ]         │  ← tabs or toggle on one page
│                                     │
│   email                             │
│   password                          │
│   [ Submit ]                        │
│                                     │
│   Educational use disclaimer        │
└─────────────────────────────────────┘
```

- Default route `/` → `/login`.
- **Sign up** link on login page; **Log in** link on signup page.
- After successful login → `/app` (query UI).
- No sidebar, no query box, no nav to features until inside `/app/*`.

---

## 3. App shell (after login)

```
┌──────────┬──────────────────────────────────┐
│ Sidebar  │  Main content                    │
│ Query    │  (Query / Screens / Escalations) │
│ Screens  │                                  │
│ Escalat. │                                  │
│ Log out  │                                  │
└──────────┴──────────────────────────────────┘
```

Header shows: user email, role badge, logout.

**Query page toggle** (Sprint 7+; production-usable, capstone default locked):

```
Evidence:  ( • Documents only )  (   Documents + current   )
```

- Sends `options.evidence_mode`: `corpus` | `current`.
- Read `features.current_factors` from `GET /auth/me`. If false, disable **Documents + current** and tooltip: “Current market/news not configured.”
- After a response, show `evidence_mode_used` next to citations (`doc` / `sql` / `quote` / `news`).
- Capstone demo stays on **Documents only**. Golden-set clients never send `current`.

---

## 4. Repo layout

```text
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.tsx
    App.tsx                 # Router root
    api/
      client.ts               # fetch + auth header + 401 handler
      auth.ts                 # login, signup
      query.ts
      screens.ts
    auth/
      AuthContext.tsx
      AuthProvider.tsx
      useAuth.ts
      tokenStorage.ts         # localStorage key frii_token (capstone); httpOnly cookie in prod later
    routes/
      ProtectedRoute.tsx
      PublicOnlyRoute.tsx
    pages/
      LoginPage.tsx
      SignupPage.tsx
      QueryPage.tsx           # Sprint 5 skeleton → Sprint 9 full
      ScreensPage.tsx
      EscalationsPage.tsx
    components/
      CitationList.tsx
      RoutingPanel.tsx
      EscalationBanner.tsx
      Disclaimer.tsx
    layouts/
      AuthLayout.tsx
      AppLayout.tsx
```

Capstone: serve built static files from FastAPI (`StaticFiles` on `/`) or run Vite dev on `:5173` with CORS to API `:8000`.

---

## 5. Auth flow (client)

```typescript
// Signup
POST /api/v1/auth/signup  { email, password, full_name? }
→ 201 → navigate /login with toast "Account created"

// Login
POST /api/v1/auth/login   { email, password }
→ { access_token, user } → tokenStorage.set(token) → AuthContext.setUser(user) → navigate /app

// Logout
tokenStorage.clear(); navigate /login

// Bootstrap (App mount)
const token = tokenStorage.get()
if (token) GET /api/v1/auth/me → set user or clear token
```

Sprint 4–7: backend may use `AUTH_MODE=stub` + `X-Debug-Role` for API testing; **React still implements real login/signup UI** wired to stub endpoints or mock until Sprint 8 JWT lands.

---

## 6. Sprint delivery

| Sprint | Frontend work |
|---|---|
| **5 (T30)** | Vite+React scaffold; **Login + Signup pages only** as default routes; ProtectedRoute stub; minimal `/app` placeholder |
| **7 (T37)** | Query page calls `POST /query`; citations + routing panel |
| **8 (T43–44)** | Wire login/signup to real JWT; 401 handling; role-based nav (hide escalations for analyst) |
| **9 (T49–52)** | Streaming query, full citation UX, screening UI, escalation UX, disclaimer always visible |

---

## 7. Env

```bash
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

CORS on FastAPI: allow `http://localhost:5173` (dev) and production frontend origin only.

---

## 8. Definition of done (frontend)

- [ ] Unauthenticated user cannot reach `/app/*` (manual + e2e test)
- [ ] `/` always resolves to login or app based on session
- [ ] Login and signup are the only public product pages (plus static legal if added)
- [ ] Logout clears token and returns to login
- [ ] All protected API calls include Bearer token
- [ ] Disclaimer rendered on every query response view

---

> **Disclaimer.** Synthetic/educational data. Not investment advice.
