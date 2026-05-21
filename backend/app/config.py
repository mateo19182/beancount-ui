"""Configuration from TOML files (no .env or shell exports)."""

from dataclasses import dataclass, field
from pathlib import Path
import sys

CONFIG_DIR = Path.home() / ".config" / "beancount-ui"
GLOBAL_CONFIG = CONFIG_DIR / "config.toml"

_REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_CONFIG = _REPO_ROOT / "config.toml"


@dataclass
class BankingConfig:
    enabled: bool = False
    app_id: str = ""
    key_path: str = ""
    banks: dict = field(default_factory=dict)


@dataclass
class AppConfig:
    ledger_path: Path | None = None
    config_path: Path = PROJECT_CONFIG
    port: int = 8742
    banking: BankingConfig = field(default_factory=BankingConfig)

    @property
    def ledger_dir(self) -> Path | None:
        if self.ledger_path:
            return self.ledger_path.parent
        return None

    @property
    def cache_dir(self) -> Path | None:
        if self.ledger_dir:
            return self.ledger_dir / ".import-cache"
        return None

    @property
    def documents_dir(self) -> Path | None:
        if self.ledger_dir:
            return self.ledger_dir / "documents"
        return None


def _load_toml(path: Path, config: AppConfig) -> AppConfig:
    import tomllib

    with open(path, "rb") as f:
        data = tomllib.load(f)

    if "ledger_path" in data:
        config.ledger_path = Path(data["ledger_path"]).expanduser().resolve()

    if port := data.get("port"):
        config.port = int(port)

    if "enable_banking" in data:
        eb = data["enable_banking"]
        config.banking.enabled = eb.get("enabled", config.banking.enabled)
        config.banking.app_id = eb.get("app_id", config.banking.app_id)
        config.banking.key_path = eb.get("key_path", config.banking.key_path)
        if "banks" in eb:
            config.banking.banks = eb["banks"]

    return config


def load_config() -> AppConfig:
    """Load config.toml: ~/.config/.../config.toml then project config.toml (overrides)."""
    config = AppConfig()

    if GLOBAL_CONFIG.exists():
        config.config_path = GLOBAL_CONFIG
        config = _load_toml(GLOBAL_CONFIG, config)

    if PROJECT_CONFIG.exists():
        config.config_path = PROJECT_CONFIG
        config = _load_toml(PROJECT_CONFIG, config)

    if not GLOBAL_CONFIG.exists() and not PROJECT_CONFIG.exists():
        config.config_path = PROJECT_CONFIG

    if config.ledger_path and not config.ledger_path.exists():
        print(
            f"Warning: ledger file not found: {config.ledger_path}",
            file=sys.stderr,
        )
        config.ledger_path = None

    return config
