"""Stable transaction identifiers from beancount entry metadata."""

from pathlib import Path

from beancount.core import data


def make_transaction_id(entry: data.Transaction, ledger_dir: Path) -> str:
    filename = entry.meta.get("filename", "")
    lineno = entry.meta.get("lineno", 0)
    if filename:
        try:
            rel = Path(filename).resolve().relative_to(ledger_dir.resolve())
            return f"{rel}:{lineno}"
        except ValueError:
            return f"{Path(filename).name}:{lineno}"
    return f":{lineno}"


def parse_transaction_id(txn_id: str, ledger_dir: Path) -> tuple[Path, int]:
    if ":" not in txn_id:
        raise ValueError(f"Invalid transaction id: {txn_id}")
    path_part, lineno_str = txn_id.rsplit(":", 1)
    lineno = int(lineno_str)
    target = ledger_dir / path_part
    if not target.exists():
        target = Path(path_part)
    if not target.is_absolute():
        target = ledger_dir / path_part
    return target.resolve(), lineno
