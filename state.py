"""App-level shared state. Module-level globals, not JSON-serialized."""

from core.ledger import Ledger
from config import AppConfig

ledger: Ledger | None = None
config: AppConfig | None = None
