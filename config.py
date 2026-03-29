"""Configuration loading from CLI args and TOML config file."""

from dataclasses import dataclass, field
from pathlib import Path
import argparse
import sys

CONFIG_DIR = Path.home() / ".config" / "beancount-ui"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class BankingConfig:
    enabled: bool = False
    app_id: str = ""
    key_path: str = ""
    banks: dict = field(default_factory=dict)


@dataclass
class AppConfig:
    ledger_path: Path | None = None
    port: int = 8080
    native: bool = True
    banking: BankingConfig = field(default_factory=BankingConfig)

    @property
    def ledger_dir(self) -> Path | None:
        if self.ledger_path:
            return self.ledger_path.parent
        return None


def load_config() -> AppConfig:
    """Load config from CLI args, then TOML file, then defaults."""
    parser = argparse.ArgumentParser(description="Beancount Desktop UI")
    parser.add_argument("ledger", nargs="?", help="Path to main.beancount file")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-native", action="store_true", help="Run in browser instead of native window")
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    config = AppConfig()

    # Load TOML config file
    config_path = args.config or CONFIG_FILE
    if config_path.exists():
        config = _load_toml(config_path, config)

    # CLI args override config file
    if args.ledger:
        config.ledger_path = Path(args.ledger).resolve()
    if args.port is not None:
        config.port = args.port
    if args.no_native:
        config.native = False

    # Validate ledger path
    if config.ledger_path and not config.ledger_path.exists():
        print(f"Error: ledger file not found: {config.ledger_path}", file=sys.stderr)
        sys.exit(1)

    return config


def _load_toml(path: Path, config: AppConfig) -> AppConfig:
    """Apply TOML config file values to config."""
    import tomllib

    with open(path, "rb") as f:
        data = tomllib.load(f)

    if "ledger_path" in data:
        config.ledger_path = Path(data["ledger_path"]).expanduser().resolve()
    if "port" in data:
        config.port = data["port"]
    if "native" in data:
        config.native = data["native"]

    if "enable_banking" in data:
        eb = data["enable_banking"]
        config.banking.enabled = eb.get("enabled", False)
        config.banking.app_id = eb.get("app_id", "")
        config.banking.key_path = eb.get("key_path", "")
        if "banks" in eb:
            config.banking.banks = eb["banks"]

    return config
