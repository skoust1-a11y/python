# Deploy (capstone)

Local run stays `uvicorn` + two Postgres DBs. Container cut uses the same app image; DBs stay external.

## Layout

```text
deploy/
  Dockerfile              # FastAPI API only (UI is on Vercel)
  compose.prod.yml        # app only; DB URLs from env
  k8s/                    # optional sketches
    deployment.yaml
    service.yaml
    configmap.yaml
    secret.example.yaml
```

## Build & dry-run

From repo root:

```bash
export GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo local)
docker build -f deploy/Dockerfile -t finance-risk-api:$GIT_SHA .
# point at your local/managed Postgres, then:
export JWT_SECRET=some-long-random-secret
export AUTH_DATABASE_URL=postgresql+psycopg://USER:PASS@host:5432/finance_auth_db
export DATABASE_URL=postgresql+psycopg://USER:PASS@host:5432/finance_risk_db
export STOCK_DATABASE_URL=postgresql+psycopg://USER:PASS@host:5432/finance_stock_db
docker compose -f deploy/compose.prod.yml up --build
curl -s localhost:8000/health
curl -s localhost:8000/health/ready
```

`APP_ENV=prod` refuses `AUTH_MODE=stub` and placeholder `JWT_SECRET`.

## Cloud: Render (API) + Supabase (Postgres) + Vercel (UI)

| Thing | Where |
|---|---|
| UI | https://frii-seven.vercel.app (Vercel team `skoust1-2033`, project `frii`, root `capstone/frontend`) |
| API | https://frii-api.onrender.com (health: `/health`) |
| Render service | https://dashboard.render.com/web/srv-dajg9cvqj5pc73dh1ak0 |
| DB | Supabase project (one Postgres, all three `*_DATABASE_URL` point at it; table names do not collide) |
| GitHub (Render + Vercel pull this, not the course GitLab) | https://github.com/skoust1-a11y/finance-risk-and-investment-intelligence-system |

Login: `admin@local` (admin), `analyst@local`, `risk@local`, `compliance@local`, all `Password123` (`SEED_PASSWORD`; demo logins are synced to it on every boot). The API creates tables, enables `pgvector` and seeds demo data on first boot, so an empty Supabase DB is fine. First hit after 15 min idle takes ~1 min (Render free spin-down). Supabase free pauses a project after 7 days without activity; resume it from the dashboard.

### 1. Supabase (DB)

1. [supabase.com](https://supabase.com) → New project. Save the DB password. Pick the same region as Render (Oregon → West US (Oregon) `us-west-2`).
2. Turn off the **Data API** (at create: "Only Connection String", or later Project Settings → Data API). The app talks to Postgres directly; leaving the Data API on exposes `public` tables (users, password hashes) through the anon key because they have no RLS.
3. **Connect** → **Session pooler** → copy the URI and put in the password:
   `postgresql://postgres.<ref>:<password>@aws-<n>-<region>.pooler.supabase.com:5432/postgres?sslmode=require`
   - Not the direct `db.<ref>.supabase.co` URL: that is IPv6-only on free, and Render has no outbound IPv6.
   - Not the transaction pooler (`:6543`): psycopg prepared statements break there.
   - `postgresql://` is rewritten to `postgresql+psycopg://` by `app.core.db.resolve_db_url`; paste as-is. Percent-encode `@ # ? & /` in the password.

Optional, carry old data over from the Render DB (otherwise the seed recreates demo data and embeddings are recomputed in the background):

```bash
pg_dump --no-owner --no-acl "<Render External Database URL>" | psql "<Supabase Session pooler URL>"
```

### 2. Render (API)

Existing service: Dashboard → `frii-api` → Environment, set the vars below, **Save, rebuild and deploy**. New workspace: **New → Blueprint** on this repo (`render.yaml`), fill the prompted vars.

```text
AUTH_DATABASE_URL=<Supabase Session pooler URL>
DATABASE_URL=<same>
STOCK_DATABASE_URL=<same>
GROQ_API_KEY / GEMINI_API_KEY / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY = <from local capstone/.env — never commit>
```

`APP_ENV=prod`, `AUTH_MODE=jwt`, `JWT_SECRET` (generated), `LLM_PROVIDER=groq`, `LLM_FALLBACK_PROVIDER=gemini` come from `render.yaml`. Root `Dockerfile` is a symlink to `deploy/Dockerfile` — Render's CLI looks for `./Dockerfile`. Do not delete it.

Check: `curl -sS https://frii-api.onrender.com/health` and the deploy log shows no DB errors. Then delete the old Render Postgres (`frii-db`).

### 3. Vercel (UI)

1. [vercel.com](https://vercel.com) → Add New → Project → import the GitHub repo.
2. **Root Directory:** `capstone/frontend`. Framework preset: Vite (build `npm run build`, output `dist`).
3. No environment variables. Deploy.

`capstone/frontend/vercel.json` proxies `/api/*` and `/admin/*` to `https://frii-api.onrender.com` (caching off), and sends every other path to `index.html` so deep links like `/login` survive a refresh. The browser only talks to the Vercel origin, so no CORS setup is needed on Render. If the Render URL changes, edit it in `vercel.json` and redeploy.

### Redeploy

`git push origin main` redeploys Render. Vercel is not Git-connected yet (the Vercel account needs a GitHub login connection first), so redeploy the UI from `capstone/frontend`: `npx vercel deploy --prod --scope skoust1-2033`. Manual API redeploy: `render deploys create srv-dajg9cvqj5pc73dh1ak0 --confirm`.

### Troubleshooting

- Login/API calls fail from Vercel but `curl https://frii-api.onrender.com/health` works → check the Render URL in `capstone/frontend/vercel.json`, redeploy Vercel. Do not set `VITE_API_BASE_URL` on Vercel (it bypasses the proxy and needs CORS).
- First request after idle is slow (~1 min) → Render free spin-down.
- `Tenant or user not found` → wrong pooler host or username (must be `postgres.<ref>`); copy the string from **Connect** again.
- `Network is unreachable` → you pasted the direct `db.<ref>.supabase.co` URL; use the Session pooler.
- `MaxClientsInSessionMode` → too many open connections for the free pooler; restart the Render service.

### Do not

- Use the course GitLab remote as the Render/Vercel git source.
- Commit `.env` or put secrets in `VITE_*` vars (they ship to the browser).
- Leave the Supabase Data API on without RLS.

## Cloud migration (other providers)

Follow `planning/16_Production_and_Cloud_Readiness.md` §7. GATE-6 signs the **capstone** go-live package, not a production VPC.

Runtime already in-app: `/health`, `/health/ready`, JSON logs, Prometheus `/metrics`, cost/rate caps.
