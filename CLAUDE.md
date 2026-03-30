# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

```bash
# Setup
uv sync

# Run the app (native desktop window)
uv run python main.py /path/to/main.beancount

# Run in browser mode
uv run python main.py /path/to/main.beancount --no-native

# Specify port
uv run python main.py /path/to/main.beancount --port 8080

# Use a custom config file
uv run python main.py --config /path/to/config.toml
```

## Project Overview

**beancount-ui** is a desktop application for managing Beancount ledgers. It's built with [NiceGUI](https://nicegui.io/) and runs as either a native window (via pywebview) or in a browser.

- **Framework**: NiceGUI 2.0+ (runs on FastAPI + Uvicorn under the hood)
- **Data Model**: Beancount ledger files (standard plaintext accounting format)
- **Python**: 3.12+ required
- **Deployment**: Native window or browser; single-instance per ledger file

## Architecture

The codebase has a **clear separation of concerns**: business logic lives in `core/`, UI pages in `pages/`, and reusable UI components in `components/`. This keeps the ledger logic independent of the UI framework.

### Core Layers

1. **state.py** (module-level globals)
   - Holds the singleton `Ledger` instance and `AppConfig`
   - Pages and components import from `state` to access ledger and config
   - No JSON serialization; these are Python objects

2. **config.py** (CLI + TOML)
   - Loads config from: CLI args → TOML file → defaults
   - CLI args override TOML settings
   - TOML file defaults to `~/.config/beancount-ui/config.toml`
   - See README for TOML schema (includes Enable Banking API config)

3. **core/ledger.py** (data access layer)
   - `Ledger` class loads a beancount file via `beancount.loader`
   - Provides typed access to entries, errors, options, price map, accounts, currencies
   - Caches computed properties (accounts, currencies, realized tree) until `reload()`
   - After write operations (e.g., adding transactions), call `ledger.reload()` to re-parse disk

4. **core/** (business logic, no UI imports)
   - `calculations.py`: Net worth, asset allocation, position aggregation
   - `analytics.py`: Transaction filtering, extraction, analysis
   - `categorizer.py`: Payee pattern learning, account suggestions
   - `transaction_writer.py`: Format, validate, write transactions to `.beancount` files
   - `document_handler.py`: Document (PDF, JPG, PNG) upload and naming

5. **pages/** (one NiceGUI page per file)
   - Each file defines a `@ui.page` route
   - Pages import from `state` to access ledger and config
   - Page UI calls `core/` functions for calculations and state updates

6. **components/** (reusable UI pieces)
   - `layout.py`: Header nav, reload button
   - `charts.py`: Plotly chart helpers
   - `metric_card.py`: Styled metric display cards
   - `date_input.py`: Date picker component

### Data Flow

1. App starts → `load_config()` parses CLI args and TOML → `Ledger` loads file once
2. Pages render with data from `state.ledger`
3. Write operation (e.g., add transaction) → write to `.beancount` file → `ledger.reload()` → UI re-renders
4. Bank import feature fetches transactions from Enable Banking API → categorizes → displays for review

## Key Design Patterns

**Lazy caching**: `Ledger` caches expensive computed properties (accounts, realized tree) and invalidates on `reload()`. This is safe because the app never modifies in-memory state without reloading.

**Module-level state**: `state.py` holds the `Ledger` and `AppConfig`. Pages import this module to access shared state. Keep state minimal and let pages compute derived data.

**NiceGUI event model**: NiceGUI uses a request-response model. UI callbacks run synchronously; blocking operations should be brief or pushed to background tasks.

**Commodity detection**: Stocks and crypto are detected by checking if a commodity has price entries. Base currency comes from beancount's `operating_currency` option.

## Important Details

- **Ledger instance is global**: Only one `Ledger` instance per app run. After writes, call `reload()` to refresh.
- **File picker on startup**: If no ledger path is provided, NiceGUI shows a file picker on first page load.
- **Dark mode not forced**: `ui.run()` sets `dark=None` so users' system preferences control the theme.
- **Storage secret**: `storage_secret="beancount-ui"` is used for NiceGUI session storage (client-side, browser sessions).
- **No reload on code change**: `reload=False` disables auto-reload on file changes (safer for ledger operations).

## Enable Banking API Integration

The `plugins/enable_banking/` directory contains bank import logic:
- Controlled by `config.banking.enabled`, `app_id`, and `key_path` in TOML
- Fetches transactions from configured banks
- Auto-categorizes via payee pattern learning (uses `core/categorizer.py`)
- Shows results in `pages/import_review.py` for user approval before importing

## File Structure (TL;DR)

```
beancount-ui/
├── main.py              # Entry point, registers pages
├── config.py            # CLI + TOML config loading
├── state.py             # Singleton Ledger + AppConfig
├── core/                # Business logic (no UI)
│   ├── ledger.py        # Ledger class (beancount access)
│   ├── calculations.py  # Net worth, allocations, positions
│   ├── analytics.py     # Transaction queries
│   ├── categorizer.py   # Payee patterns, suggestions
│   ├── transaction_writer.py  # Write txns to file
│   └── document_handler.py    # Document storage
├── pages/               # @ui.page routes
│   ├── overview.py      # Dashboard
│   ├── investments.py   # Stock portfolio
│   ├── crypto.py        # Crypto holdings
│   ├── transactions.py  # Browse/edit txns
│   ├── add_transaction.py  # Create txn
│   └── import_review.py # Bank import review
├── components/          # Reusable UI
│   ├── layout.py        # Nav, reload button
│   ├── charts.py        # Plotly wrappers
│   ├── metric_card.py   # Metric display
│   └── date_input.py    # Date picker
└── plugins/             # Optional integrations
    └── enable_banking/  # Bank import API
```
