"""FastAPI dependencies and application state."""

from fastapi import HTTPException

from app.config import AppConfig, load_config
from app.services.ledger import Ledger
from app.services.bank_import import BankImportService


class AppState:
    def __init__(self):
        self.config: AppConfig = load_config()
        self.ledger: Ledger | None = None
        self.bank_import: BankImportService | None = None

        if self.config.ledger_path and self.config.ledger_path.exists():
            self.reload_ledger()

    def reload_ledger(self) -> None:
        if not self.config.ledger_path:
            self.ledger = None
            self.bank_import = None
            return
        if not self.config.ledger_path.exists():
            self.ledger = None
            self.bank_import = None
            return
        self.ledger = Ledger(self.config.ledger_path)
        self.bank_import = BankImportService(self.ledger, self.config)

    def open_ledger(self, path: str) -> None:
        from pathlib import Path

        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            raise HTTPException(404, f"Ledger file not found: {resolved}")
        self.config.ledger_path = resolved
        self.reload_ledger()

    def require_ledger(self) -> Ledger:
        if not self.ledger:
            raise HTTPException(
                503,
                "No ledger loaded. Set ledger_path in config.toml or POST /api/ledger/open.",
            )
        return self.ledger


state = AppState()
