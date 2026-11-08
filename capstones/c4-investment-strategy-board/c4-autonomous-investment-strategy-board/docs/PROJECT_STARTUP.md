# Project Startup Guide

This guide covers only what is required to start the application locally after cloning the repository.

---

## 1. Prerequisites

| Tool | Version | Why it is required |
| --- | --- | --- |
| Git | Not specified in the repository | Clone the project |
| Python | 3.11 or later (`requires-python = ">=3.11"` in `pyproject.toml`) | Backend runtime |
| pip | Bundled with Python | Install backend dependencies from `requirements.txt` |
| Node.js | 18, 20, or 22+ (required by Vite 6 in `frontend/package-lock.json`) | Frontend runtime |
| npm | Not specified in the repository; used by `frontend/package-lock.json` and the documented scripts | Install frontend dependencies and start the Vite dev server |

No database, Docker, Docker Compose, Redis, or other local infrastructure is used by the current implementation. Persistence is in-memory.

---

## 2. Clone & Enter Project

Origin URL from this repository:

```bash
git clone https://github.com/skoust1-a11y/python.git
cd python/capstones/c4-investment-strategy-board/c4-autonomous-investment-strategy-board
```

If you already have a local copy, enter that directory instead.

---

## 3. Environment Configuration

Two environment templates exist:

| File | Copy to | Required to start? |
| --- | --- | --- |
| `.env.example` (repository root) | `.env` (repository root) | Documented as the backend configuration step. Settings also have in-code defaults if `.env` is missing. |
| `frontend/.env.example` | `frontend/.env` | No. The frontend starts without it. |

### Backend (`.env`)

From the repository root:

**Windows**

```bat
copy .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

With `.env.example` copied as-is, the backend starts without filling any secrets.

| Variable | Role for startup | Action |
| --- | --- | --- |
| `APP_NAME`, `APP_ENV`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL` | Process name, environment, bind address, log level | Can remain at defaults. Default bind is `127.0.0.1:8000`. |
| `LLM_PROVIDER` | LLM adapter selected at process start | Can remain `stub`. Values: `stub`, `openai`, `groq`, `google`, `azure`. |
| `FALLBACK_LLM_PROVIDER` | Optional second LLM adapter | Can remain empty. |
| `LLM_TIMEOUT_SECONDS` | LLM client timeout | Can remain at default (`30`). |
| `MARKET_DATA_PROVIDER` | Market-data adapter selected at process start | Can remain `yahoo` (as in `.env.example`). Values: `stub`, `yahoo` (`yfinance` is an alias). |
| `FUNDAMENTAL_DATA_PROVIDER` | Fundamental-data adapter | Must remain `stub` (only registered adapter). |
| `NEWS_PROVIDER` | News adapter | Must remain `stub` (only registered adapter). |
| `MARKET_DATA_API_KEY`, `MARKET_DATA_BASE_URL` | Unused by the Yahoo adapter at construction | Can remain empty. |
| `FUNDAMENTAL_DATA_API_KEY`, `FUNDAMENTAL_DATA_BASE_URL`, `NEWS_API_KEY`, `NEWS_BASE_URL` | Unused by stub adapters | Can remain empty. |
| `PORTFOLIO_MAX_UPLOAD_BYTES`, `PORTFOLIO_UPLOAD_TTL_SECONDS` | Upload limits | Can remain at defaults. |
| `OPENAI_LLM_MODEL`, `GROQ_LLM_MODEL`, `GOOGLE_LLM_MODEL`, `AZURE_LLM_API_VERSION` | Vendor model / API version | Can remain at defaults unless you change `LLM_PROVIDER` / `FALLBACK_LLM_PROVIDER`. |
| `OPENAI_LLM_API_KEY`, `OPENAI_LLM_BASE_URL`, `GROQ_LLM_API_KEY`, `GOOGLE_LLM_API_KEY`, `AZURE_LLM_API_KEY`, `AZURE_LLM_ENDPOINT`, `AZURE_LLM_MODEL`, `AZURE_LLM_DEPLOYMENT` | Vendor credentials | Leave empty when `LLM_PROVIDER=stub` and `FALLBACK_LLM_PROVIDER` is empty. |

If you change `LLM_PROVIDER` (or set `FALLBACK_LLM_PROVIDER`) away from `stub`, the matching values **must** be set before the backend process starts, or adapter construction fails:

| Selected provider | Mandatory at startup |
| --- | --- |
| `openai` | `OPENAI_LLM_API_KEY`, `OPENAI_LLM_MODEL` (`OPENAI_LLM_BASE_URL` optional) |
| `groq` | `GROQ_LLM_API_KEY`, `GROQ_LLM_MODEL` |
| `google` | `GOOGLE_LLM_API_KEY`, `GOOGLE_LLM_MODEL` |
| `azure` | `AZURE_LLM_API_KEY`, `AZURE_LLM_MODEL`, `AZURE_LLM_ENDPOINT`, `AZURE_LLM_API_VERSION` (`AZURE_LLM_DEPLOYMENT` optional; falls back to the model name) |

Do not commit `.env`. Do not put real secrets in documentation.

### Frontend (`frontend/.env`)

`VITE_API_BASE_URL` can remain empty (or the file can be omitted). Empty means the Vite dev-server proxy is used, which is the documented local setup.

Copy only if you need a local frontend env file:

**Windows**

```bat
copy frontend\.env.example frontend\.env
```

**macOS / Linux**

```bash
cp frontend/.env.example frontend/.env
```

---

## 4. Start Required Services

No local services, containers, or databases need to be started before the application.

The backend uses in-memory stores. There is no Docker Compose file and no database migration step.

---

## 5. Start Backend

Run these commands from the repository root. Use one terminal and leave it running.

**Windows** (commands from `README.md`)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app
```

On PowerShell, if `activate` does not work, use:

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app
```

There is no database initialization or migration step.

The API listens on `APP_HOST` / `APP_PORT` from `.env` (default `http://127.0.0.1:8000`).

---

## 6. Start Frontend

Use a second terminal. Run these commands from the repository root:

```bash
cd frontend
npm install
npm run dev
```

No frontend environment file is required for the default proxy setup.

The UI listens on `http://127.0.0.1:5173` and proxies API calls to `http://127.0.0.1:8000`.

---

## 7. Startup Order

```text
1. Clone the repository and enter the project directory
2. Copy `.env.example` to `.env` (fill LLM keys only if you change LLM_PROVIDER)
3. Start the backend (`python -m app`)
4. Start the frontend (`npm run dev` in frontend/)
5. Open the application
```

No infrastructure services are started in this project.

---

## 8. Verify Application Started

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000
API Docs: http://127.0.0.1:8000/docs
Health:   http://127.0.0.1:8000/health
```

`GET /health` should return HTTP 200 with `"status": "ok"`. With `.env.example` copied unchanged, the payload looks like:

```json
{
  "status": "ok",
  "name": "Autonomous Investment Strategy Board",
  "environment": "development",
  "providers": {
    "llm": "stub",
    "market_data": "yahoo",
    "fundamental_data": "stub",
    "news": "stub"
  }
}
```

`GET http://127.0.0.1:8000/` should return HTTP 200 with `"health": "/health"` and `"docs": "/docs"`.

---

## 9. Quick Start

Prerequisites already installed. Run the backend and frontend in two terminals.

**Windows**

```bat
git clone https://github.com/skoust1-a11y/python.git
cd python/capstones/c4-investment-strategy-board/c4-autonomous-investment-strategy-board

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app

cd frontend
npm install
npm run dev
```

**macOS / Linux**

```bash
git clone https://github.com/skoust1-a11y/python.git
cd python/capstones/c4-investment-strategy-board/c4-autonomous-investment-strategy-board

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app

cd frontend
npm install
npm run dev
```

```text
Application: http://127.0.0.1:5173
Backend:     http://127.0.0.1:8000
API Docs:    http://127.0.0.1:8000/docs
```
