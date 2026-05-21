# CLAUDE.md

Guidance for working in the beancount-ui repository.

## Quick Commands

```bash
# Setup
cp config.toml.example config.toml    # edit ledger_path and banking settings
cd backend && uv sync
cd frontend && npm install

# Backend (development)
cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8742

# Frontend (development, requires backend)
cd frontend && npm run dev

# Desktop app
cd src-tauri && cargo tauri dev
```

## Project Overview

**beancount-ui** is a desktop app for managing Beancount ledgers:

- **Tauri 2** — native shell, ledger file picker, OAuth URL opening
- **FastAPI** — local sidecar on `127.0.0.1:8742`, all ledger logic
- **React + Vite** — SPA with TanStack Query

Python 3.12+ required. Single ledger per session.

## Architecture

```
src-tauri/          → spawns backend, pick_ledger_file command
frontend/src/       → React UI, calls /api/*
backend/app/        → FastAPI routers + services
```

### Backend (`backend/app/`)

- `main.py` — FastAPI app, CORS
- `deps.py` — `AppState` singleton, `require_ledger()` → HTTP 503
- `config.py` — `config.toml` (project) overrides `~/.config/beancount-ui/config.toml`
- `routers/` — HTTP layer
- `services/` — beancount logic (ledger, calculations, transactions, banking)
- `services/enable_banking/` — Enable Banking API integration

### Frontend (`frontend/src/`)

- `api/client.ts` — typed REST client
- `components/LedgerGate.tsx` — startup / open ledger
- `components/TransactionForm.tsx` — shared add/edit form
- `pages/` — one page per route

### Data flow

1. Tauri spawns uvicorn → `AppState` loads ledger from env/config
2. React polls `/health` and `/api/ledger/status`
3. User can `POST /api/ledger/open` or Tauri file picker
4. Writes go through API → file on disk → `state.reload_ledger()`

## Transaction IDs

Transactions are identified by `{relative_path}:{lineno}` from beancount entry metadata. Use `id` for edit/delete API calls, not date/payee tuples.

## Enable Banking

Configured in TOML under `[enable_banking]`. Staging cache: `{ledger_parent}/.import-cache/`. Import writes to `transactions/banks/{YYYY-MM}.beancount`.

## External tools

- `bean-price` / `bean-check` — invoked via subprocess from `services/price_fetcher.py`
- `yfinance` — fallback in `price_fetcher_alt.py`

## Design notes

- No in-memory ledger mutation without `reload_ledger()` after writes
- Balance tolerance: 0.005 on import validation; UI preview uses backend rules
- Production frontend must set `VITE_API_URL=http://127.0.0.1:8742` when built for Tauri
