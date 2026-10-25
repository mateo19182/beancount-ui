"""Format, validate, and write beancount transactions."""

import re
from pathlib import Path

from beancount import loader

from app.services.posting_signs import balance_by_currency, is_balanced, signed_amount
from app.services.transaction_ids import parse_transaction_id

VALID_ACCOUNT_ROOTS = ("Assets", "Liabilities", "Equity", "Income", "Expenses")
_ACCOUNT_PART_RE = re.compile(r"^[A-Z][A-Za-z0-9\-_]*$")


def _escape_quotes(s: str) -> str:
    return s.replace('"', "'") if s else s


def format_transaction(
    date: str,
    flag: str,
    payee: str | None,
    narration: str | None,
    postings: list[dict],
    metadata: dict | None = None,
) -> str:
    header = f"{date} {flag}"
    if payee:
        header += f' "{_escape_quotes(payee)}"'
    if narration:
        header += f' "{_escape_quotes(narration)}"'

    lines = [header]
    if metadata:
        for key, value in metadata.items():
            lines.append(f'  {key}: "{_escape_quotes(str(value))}"')

    for posting in postings:
        signed = signed_amount(posting, postings)
        lines.append(
            f"  {posting['account']:<40} {signed:>12.2f} {posting['currency']}"
        )

    return "\n".join(lines) + "\n"


def calculate_balance(postings: list[dict]) -> dict[str, float]:
    return balance_by_currency(postings)


def validate_transaction(
    postings: list[dict], valid_accounts: list[str], valid_currencies: set[str]
) -> tuple[bool, str]:
    if len(postings) < 2:
        return False, "At least 2 postings required"
    for posting in postings:
        if not posting.get("account"):
            return False, "All accounts must be specified"
        if posting["account"] not in valid_accounts:
            return False, f"Invalid account: {posting['account']}"
        if posting["currency"] not in valid_currencies:
            return False, f"Invalid currency: {posting['currency']}"
        if posting["amount"] == 0:
            return False, "Amount cannot be zero"
    return True, "Valid"


def validate_transaction_balance(postings: list[dict]) -> tuple[bool, str]:
    return is_balanced(postings)


def determine_target_file(ledger_dir: Path, accounts: list[str]) -> Path:
    tx_dir = ledger_dir / "transactions"
    for acc in accounts:
        lower = acc.lower()
        if "crypto" in lower:
            return tx_dir / "crypto.beancount"
        if "investment" in lower or "broker" in lower:
            return tx_dir / "investments.beancount"
    from datetime import date

    month = date.today().strftime("%Y-%m")
    banks_dir = tx_dir / "banks"
    banks_dir.mkdir(parents=True, exist_ok=True)
    return banks_dir / f"{month}.beancount"


def write_transaction(transaction_str: str, target_file: Path) -> tuple[bool, str]:
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, "a") as f:
        f.write("\n")
        f.write(transaction_str)
    return True, f"Transaction written to {target_file.name}"


def is_valid_account_name(account: str) -> bool:
    if not account or ":" not in account:
        return False
    parts = account.split(":")
    if parts[0] not in VALID_ACCOUNT_ROOTS:
        return False
    return all(_ACCOUNT_PART_RE.match(p) for p in parts)


def format_open_directive(date: str, account: str, currencies: list[str] | None = None) -> str:
    line = f"{date} open {account}"
    if currencies:
        line += " " + ", ".join(f'"{c}"' for c in currencies)
    return line + "\n"


def write_open_directive(directive: str, ledger_path: Path) -> tuple[bool, str]:
    with open(ledger_path, "a") as f:
        f.write("\n")
        f.write(directive)
    return True, f"Account opened in {ledger_path.name}"


def verify_ledger(ledger_path: Path) -> tuple[bool, str]:
    try:
        _, errors, _ = loader.load_file(str(ledger_path))
        if errors:
            return False, f"Ledger validation: {len(errors)} warning(s)"
        return True, "Ledger validation passed"
    except Exception as e:
        return False, f"Ledger parse error: {e}"


def locate_transaction_by_id(
    ledger_dir: Path, txn_id: str
) -> tuple[Path, int, int] | None:
    """Return (file_path, tx_start_line_index, tx_end_line_index) for a transaction id."""
    try:
        target_file, lineno = parse_transaction_id(txn_id, ledger_dir)
    except (ValueError, OSError):
        return None
    if not target_file.exists():
        return None
    lines = target_file.read_text().splitlines(keepends=True)
    tx_start = lineno - 1
    if tx_start < 0 or tx_start >= len(lines):
        return None
    tx_end = tx_start + 1
    while tx_end < len(lines):
        current = lines[tx_end]
        s = current.strip()
        if not current.startswith("  ") and s and (s[0].isdigit() or s.startswith(";")):
            break
        tx_end += 1
    return target_file, tx_start, tx_end


def find_transaction_file(
    ledger_dir: Path, date_str: str, payee: str | None, narration: str | None
) -> Path | None:
    tx_dir = ledger_dir / "transactions"
    if not tx_dir.exists():
        return None
    for pattern in _build_search_patterns(date_str, payee, narration):
        for beancount_file in tx_dir.rglob("*.beancount"):
            try:
                if pattern in beancount_file.read_text():
                    return beancount_file
            except Exception:
                continue
    return None


def add_document_to_transaction(
    target_file: Path, date_str: str, payee: str, narration: str, document_path: str
) -> tuple[bool, str]:
    if not target_file.exists():
        return False, f"File not found: {target_file}"
    lines = target_file.read_text().splitlines(keepends=True)
    match_line = _find_transaction_line(lines, date_str, payee, narration)
    if match_line is None:
        return False, f"Transaction not found: {date_str} {payee}"
    for j in range(match_line + 1, min(match_line + 5, len(lines))):
        if "document:" in lines[j]:
            return False, "Transaction already has a document"
    lines.insert(match_line + 1, f'  document: "{document_path}"\n')
    target_file.write_text("".join(lines))
    return True, f"Document added to transaction in {target_file.name}"


def _parse_block_at_line(lines: list[str], tx_start: int) -> tuple[dict, list[dict], list[str]]:
    metadata = {}
    postings = []
    warnings = []
    j = tx_start + 1
    while j < len(lines):
        current = lines[j]
        s = current.strip()
        if not current.startswith("  ") and s and (s[0].isdigit() or s.startswith(";")):
            break
        if ": " in s[:50] and not s.startswith(";"):
            parts = s.split(": ", 1)
            if len(parts) == 2:
                metadata[parts[0].strip()] = parts[1].strip().strip('"')
        elif s and not s.startswith(";"):
            parts = s.split()
            if len(parts) >= 3:
                try:
                    raw = float(parts[1].replace(",", ""))
                    postings.append({
                        "account": parts[0],
                        "amount": abs(raw),
                        "currency": parts[2],
                        "signed": raw,
                    })
                except ValueError:
                    warnings.append(f"Could not parse posting: {s}")
        j += 1
    return metadata, postings, warnings


def _parse_header_line(line: str) -> tuple[str, str, str, str]:
    """Parse date, flag, payee, narration from transaction header."""
    s = line.strip()
    parts = s.split('"')
    date_flag = parts[0].strip().split()
    date_str = date_flag[0] if date_flag else ""
    flag = date_flag[1] if len(date_flag) > 1 else "*"
    payee = parts[1] if len(parts) > 1 else ""
    narration = parts[3] if len(parts) > 3 else ""
    return date_str, flag, payee, narration


def edit_transaction_by_id(
    ledger_dir: Path,
    txn_id: str,
    new_date: str | None = None,
    new_flag: str | None = None,
    new_payee: str | None = None,
    new_narration: str | None = None,
    new_postings: list[dict] | None = None,
) -> tuple[bool, str]:
    located = locate_transaction_by_id(ledger_dir, txn_id)
    if not located:
        return False, f"Transaction not found: {txn_id}"
    target_file, tx_start, tx_end = located
    lines = target_file.read_text().splitlines(keepends=True)
    orig_date, orig_flag, orig_payee, orig_narration = _parse_header_line(lines[tx_start])
    metadata, original_postings, parse_warnings = _parse_block_at_line(lines, tx_start)
    final_postings = new_postings if new_postings is not None else original_postings
    new_tx = format_transaction(
        new_date or orig_date,
        new_flag or orig_flag,
        new_payee if new_payee is not None else orig_payee,
        new_narration if new_narration is not None else orig_narration,
        final_postings,
        metadata or None,
    )
    warning = ""
    if parse_warnings:
        warning = f" (warnings: {'; '.join(parse_warnings)})"
    new_lines = lines[:tx_start] + [new_tx + "\n"] + lines[tx_end:]
    target_file.write_text("".join(new_lines))
    return True, f"Transaction updated in {target_file.name}{warning}"


def delete_transaction_by_id(ledger_dir: Path, txn_id: str) -> tuple[bool, str]:
    located = locate_transaction_by_id(ledger_dir, txn_id)
    if not located:
        return False, f"Transaction not found: {txn_id}"
    target_file, tx_start, tx_end = located
    lines = target_file.read_text().splitlines(keepends=True)
    while tx_start > 0 and lines[tx_start - 1].strip() == "":
        tx_start -= 1
    new_lines = lines[:tx_start] + lines[tx_end:]
    target_file.write_text("".join(new_lines))
    return True, f"Transaction deleted from {target_file.name}"


def edit_transaction(
    ledger_dir: Path,
    original_date: str,
    original_payee: str | None,
    original_narration: str | None,
    new_date: str | None = None,
    new_flag: str | None = None,
    new_payee: str | None = None,
    new_narration: str | None = None,
    new_postings: list[dict] | None = None,
) -> tuple[bool, str]:
    target_file = find_transaction_file(
        ledger_dir, original_date, original_payee, original_narration
    )
    if not target_file:
        return False, f"Transaction not found: {original_date} {original_payee}"

    lines = target_file.read_text().splitlines(keepends=True)
    tx_start, tx_end, original_metadata, original_posting_data, parse_warnings = (
        _parse_transaction_block(lines, original_date, original_payee, original_narration)
    )
    if tx_start < 0:
        return False, f"Transaction not found in file: {original_date} {original_payee}"

    final_postings = new_postings if new_postings is not None else original_posting_data
    new_tx = format_transaction(
        new_date or original_date,
        new_flag or "*",
        new_payee if new_payee is not None else original_payee,
        new_narration if new_narration is not None else original_narration,
        final_postings,
        original_metadata or None,
    )
    warning = ""
    if parse_warnings:
        warning = f" (warnings: {'; '.join(parse_warnings)})"
    new_lines = lines[:tx_start] + [new_tx + "\n"] + lines[tx_end:]
    target_file.write_text("".join(new_lines))
    return True, f"Transaction updated in {target_file.name}{warning}"


def delete_transaction(
    ledger_dir: Path,
    date_str: str,
    payee: str | None,
    narration: str | None,
) -> tuple[bool, str]:
    target_file = find_transaction_file(ledger_dir, date_str, payee, narration)
    if not target_file:
        return False, f"Transaction not found: {date_str} {payee}"
    lines = target_file.read_text().splitlines(keepends=True)
    tx_start = _find_transaction_line(lines, date_str, payee, narration)
    if tx_start is None:
        return False, f"Transaction not found in file: {date_str} {payee}"
    tx_end = tx_start + 1
    while tx_end < len(lines):
        current = lines[tx_end]
        s = current.strip()
        if not current.startswith("  ") and s and (s[0].isdigit() or s.startswith(";")):
            break
        tx_end += 1
    while tx_start > 0 and lines[tx_start - 1].strip() == "":
        tx_start -= 1
    new_lines = lines[:tx_start] + lines[tx_end:]
    target_file.write_text("".join(new_lines))
    return True, f"Transaction deleted from {target_file.name}"


def add_document_to_transaction_by_id(
    ledger_dir: Path, txn_id: str, document_path: str
) -> tuple[bool, str]:
    located = locate_transaction_by_id(ledger_dir, txn_id)
    if not located:
        return False, f"Transaction not found: {txn_id}"
    target_file, tx_start, _ = located
    lines = target_file.read_text().splitlines(keepends=True)
    for j in range(tx_start + 1, min(tx_start + 5, len(lines))):
        if "document:" in lines[j]:
            return False, "Transaction already has a document"
    lines.insert(tx_start + 1, f'  document: "{document_path}"\n')
    target_file.write_text("".join(lines))
    return True, f"Document added to transaction in {target_file.name}"


def _build_search_patterns(
    date_str: str, payee: str | None, narration: str | None
) -> list[str]:
    escaped_payee = _escape_quotes(payee) if payee else None
    escaped_narration = _escape_quotes(narration) if narration else None
    patterns = []
    for flag in ("*", "!"):
        if escaped_payee and escaped_narration:
            patterns.append(f'{date_str} {flag} "{escaped_payee}" "{escaped_narration}"')
    for flag in ("*", "!"):
        if escaped_payee:
            patterns.append(f'{date_str} {flag} "{escaped_payee}"')
    return patterns


def _find_transaction_line(
    lines: list[str], date_str: str, payee: str | None, narration: str | None
) -> int | None:
    for pattern in _build_search_patterns(date_str, payee, narration):
        for i, line in enumerate(lines):
            if line.rstrip().startswith(pattern):
                return i
    return None


def _parse_transaction_block(
    lines: list[str], date_str: str, payee: str | None, narration: str | None
) -> tuple[int, int, dict, list[dict], list[str]]:
    tx_start = _find_transaction_line(lines, date_str, payee, narration)
    if tx_start is None:
        return -1, -1, {}, [], []
    metadata = {}
    postings = []
    warnings = []
    j = tx_start + 1
    while j < len(lines):
        current = lines[j]
        s = current.strip()
        if not current.startswith("  ") and s and (s[0].isdigit() or s.startswith(";")):
            break
        if ": " in s[:50] and not s.startswith(";"):
            parts = s.split(": ", 1)
            if len(parts) == 2:
                metadata[parts[0].strip()] = parts[1].strip().strip('"')
        elif s and not s.startswith(";"):
            parts = s.split()
            if len(parts) >= 3:
                try:
                    raw = float(parts[1].replace(",", ""))
                    postings.append({
                        "account": parts[0],
                        "amount": abs(raw),
                        "currency": parts[2],
                        "signed": raw,
                    })
                except ValueError:
                    warnings.append(f"Could not parse posting: {s}")
        j += 1
    return tx_start, j, metadata, postings, warnings
