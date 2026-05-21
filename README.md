# beancount-ui

Desktop app for managing [Beancount](https://beancount.github.io/) ledgers. Built with **Tauri 2**, **FastAPI** (local sidecar on `127.0.0.1:8742`), and **React + Vite + TypeScript**.

## Architecture

```
beancount-ui/
├── backend/app/       # FastAPI services and routers
├── frontend/src/      # React SPA (Vite, TanStack Query, Recharts)
├── src-tauri/         # Tauri 2 — spawns uvicorn sidecar, ledger file picker
└── scripts/           # Packaging helpers
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- [Node.js](https://nodejs.org/) 22+
- [Rust](https://rustup.rs/) (for Tauri desktop builds)
- Optional: `bean-price` and `bean-check` on PATH (via `uv tool install beancount` or project env)

## Configuration

Copy the example and edit **`config.toml`** in the project root (gitignored):

```bash
cp config.toml.example config.toml
```

```toml
ledger_path = "/path/to/main.beancount"
port = 8742

[enable_banking]
enabled = true
app_id = "your-app-id"
key_path = "/path/to/private.pem"

[enable_banking.banks.revolut]
name = "Revolut"
country = "ES"
```

Optional global defaults: `~/.config/beancount-ui/config.toml` — project `config.toml` overrides it.

No `.env` or shell `export` required.

## Development

### Backend only

```bash
cp config.toml.example config.toml   # once, then edit
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8742
```

### Frontend only (browser)

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` and `/health` to `http://127.0.0.1:8742`.

### Full desktop app

```bash
cp config.toml.example config.toml   # once, then edit
cd beancount-ui/src-tauri   # or repo root: cargo tauri dev --manifest-path src-tauri/Cargo.toml
cargo tauri dev
```

Tauri starts the Vite dev server and spawns `uv run uvicorn` in `backend/` on port **8742**. Use **Browse** on the startup screen to open a ledger without config.

## Production build

```bash
cd frontend && VITE_API_URL=http://127.0.0.1:8742 npm run build
cd src-tauri && cargo tauri build
```

Build outputs:

- **Binary** (fastest for daily use): `src-tauri/target/release/beancount-ui` — used by `beancount-ui-launch`
- **`.deb` / `.rpm`**: `src-tauri/target/release/bundle/deb/` and `bundle/rpm/`

AppImage is disabled in `tauri.conf.json` (linuxdeploy’s bundled `strip` is too old for Arch’s `.relr.dyn` libraries). Install on Arch with:

```bash
sudo pacman -U src-tauri/target/release/bundle/deb/beancount-ui_0.2.0_amd64.deb
```

The bundle includes the `backend/` directory as a resource. **uv** must be available on the target system to run the sidecar.

Optional: prepare a synced venv in resources before build:

```bash
./scripts/package-sidecar.sh
```

## Features

| Route | Description |
|-------|-------------|
| `/` | Overview — net worth, asset allocation (click to drill down) |
| `/charts` | Monthly income/expenses and category breakdowns |
| `/investments` | Stock holdings |
| `/crypto` | Crypto holdings |
| `/banks` | Bank balances and import file viewer |
| `/transactions` | Browse, filter, edit, delete, attach documents |
| `/add` | Create multi-posting transactions |
| `/import` | Enable Banking OAuth, fetch, review, import |

Header actions: **Update Prices** (bean-price + yfinance fallback), **Validate** (bean-check), **Reload**.

## API

REST API under `/api/*`. Key endpoints:

- `GET /health` — backend status
- `GET /api/ledger/status` — ledger loaded state
- `POST /api/ledger/open` — open ledger by path
- `GET /api/transactions` — list with stable transaction `id`
- `PUT /api/transactions` — edit by `id`
- `GET /api/banks/balances` — bank account balances

## License

MIT
