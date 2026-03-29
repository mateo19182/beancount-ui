# beancount-ui

A desktop app for managing [Beancount](https://beancount.github.io/) ledgers. Built with [NiceGUI](https://nicegui.io/), runs as a native window or in the browser. Point it at your `main.beancount` and go.

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-user/beancount-ui.git
cd beancount-ui
uv sync

# Run (native desktop window)
uv run python main.py /path/to/main.beancount

# Or in browser mode
uv run python main.py /path/to/main.beancount --no-native
```

Requires Python 3.12+. If you don't pass a ledger path, the app shows a file picker on first launch.

## Features

**Overview** — Net worth, asset allocation pie chart, account breakdown by category.

**Investments** — Stock portfolio: holdings table, prices, allocation bar chart.

**Crypto** — Cryptocurrency holdings with the same layout.

**Transactions** — Browse, filter, and search all transactions. Edit inline via dialog. Attach documents (PDF, JPG, PNG) to any transaction.

**Add Transaction** — Create multi-posting transactions with real-time balance validation, beancount preview, and optional document upload.

**Import Review** *(optional, requires banking plugin)* — Fetch transactions from banks via [Enable Banking API](https://enablebanking.com/), auto-categorize from learned payee patterns, review in an editable grid with dropdown categories, import to ledger or discard.

## Configuration

### CLI args

```bash
uv run python main.py /path/to/main.beancount          # required: ledger path
                                           --port 8080  # default: 8080
                                           --no-native  # browser instead of desktop window
                                           --config /path/to/config.toml
```

### Config file

Optional. Defaults to `~/.config/beancount-ui/config.toml`.

```toml
ledger_path = "/home/user/finances/main.beancount"
port = 8080

[enable_banking]
enabled = true
app_id = "your-app-id"
key_path = "/path/to/private.pem"

[enable_banking.banks.revolut]
name = "Revolut"
country = "ES"

[enable_banking.banks.caixa_rural]
name = "Caixa Rural Galega"
country = "ES"
```

### Bank import setup

```bash
# Install optional dependencies
uv sync --extra banking

# Set enable_banking.enabled = true in config.toml
# Then authorize banks via the Enable Banking OAuth flow
```

## Project Structure

```
beancount-ui/
├── main.py              # Entry point
├── config.py            # CLI + TOML config
├── state.py             # Shared app state (Ledger instance)
├── core/                # Business logic (no UI imports)
│   ├── ledger.py        # Ledger class: load, query, convert currencies
│   ├── analytics.py     # Transaction extraction and filtering
│   ├── calculations.py  # Net worth, positions, asset categories
│   ├── categorizer.py   # Payee pattern learning, account suggestion
│   ├── transaction_writer.py  # Format, validate, write transactions
│   └── document_handler.py    # Document upload and naming
├── pages/               # One @ui.page per page
│   ├── overview.py
│   ├── investments.py
│   ├── crypto.py
│   ├── transactions.py
│   ├── add_transaction.py
│   └── import_review.py
├── components/          # Reusable UI pieces
│   ├── layout.py        # Header nav, reload button
│   ├── charts.py        # Plotly chart helpers
│   └── metric_card.py   # Styled metric display
└── plugins/             # Optional integrations
    └── enable_banking/  # Bank import via Enable Banking API
```

## How It Works

The app loads your beancount ledger once into a `Ledger` object that stays in memory. Pages read from it, write operations append to your `.beancount` files, then `ledger.reload()` re-parses from disk. No caching layer needed — beancount parses personal ledgers in under a second.

Stock and crypto positions are detected automatically by commodity type (non-fiat commodities with price entries), not by hardcoded account paths. Base currency is read from your beancount `operating_currency` option.

## License

MIT
