"""Format, validate, and write beancount transactions."""

from pathlib import Path
from beancount import loader


def _escape_quotes(s: str) -> str:
    """Escape double quotes for beancount string fields."""
    return s.replace('"', "'") if s else s


def format_transaction(
    date: str,
    flag: str,
    payee: str | None,
    narration: str | None,
    postings: list[dict],
    metadata: dict | None = None,
) -> str:
    """Format a transaction as a beancount string.

    postings: list of {account, amount, currency}
    metadata: optional dict of key/value pairs
    """
    header = f"{date} {flag}"
    if payee:
        header += f' "{_escape_quotes(payee)}"'
    if narration:
        header += f' "{_escape_quotes(narration)}"'

    lines = [header]

    if metadata:
        for key, value in metadata.items():
            lines.append(f'  {key}: "{_escape_quotes(str(value))}"')

    has_expense = any(p["account"].startswith("Expenses:") for p in postings)
    has_income = any(p["account"].startswith("Income:") for p in postings)

    for posting in postings:
        account = posting["account"]
        amount = posting["amount"]
        currency = posting["currency"]

        # Determine sign
        if amount < 0:
            signed = amount
        elif account.startswith("Expenses:"):
            signed = abs(amount)
        elif account.startswith("Income:"):
            signed = -abs(amount)
        elif has_expense:
            signed = -abs(amount)
        elif has_income:
            signed = abs(amount)
        else:
            signed = amount

        lines.append(f"  {account:<40} {signed:>12.2f} {currency}")

    return "\n".join(lines) + "\n"


def calculate_balance(postings: list[dict]) -> dict[str, float]:
    """Calculate the balance per currency for a set of postings."""
    has_expense = any(p["account"].startswith("Expenses:") for p in postings)
    has_income = any(p["account"].startswith("Income:") for p in postings)

    balance: dict[str, float] = {}
    for posting in postings:
        account = posting["account"]
        amount = posting["amount"]
        currency = posting["currency"]

        if amount < 0:
            signed = amount
        elif account.startswith("Expenses:"):
            signed = amount
        elif account.startswith("Income:"):
            signed = -amount
        elif has_expense:
            signed = -amount
        elif has_income:
            signed = amount
        else:
            signed = amount

        balance[currency] = balance.get(currency, 0.0) + signed
    return balance


def validate_transaction(
    postings: list[dict], valid_accounts: list[str], valid_currencies: set[str]
) -> tuple[bool, str]:
    """Validate posting data before writing."""
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


def determine_target_file(ledger_dir: Path, accounts: list[str]) -> Path:
    """Determine which transaction file to write to based on account types."""
    tx_dir = ledger_dir / "transactions"

    for acc in accounts:
        lower = acc.lower()
        if "crypto" in lower:
            return tx_dir / "crypto.beancount"
        if "investment" in lower or "broker" in lower:
            return tx_dir / "investments.beancount"

    # Default: monthly bank file
    from datetime import date
    month = date.today().strftime("%Y-%m")
    banks_dir = tx_dir / "banks"
    banks_dir.mkdir(parents=True, exist_ok=True)
    return banks_dir / f"{month}.beancount"


def write_transaction(transaction_str: str, target_file: Path) -> tuple[bool, str]:
    """Append a transaction to the target file."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, "a") as f:
        f.write("\n")
        f.write(transaction_str)

    return True, f"Transaction written to {target_file.name}"


def verify_ledger(ledger_path: Path) -> tuple[bool, str]:
    """Verify ledger has no errors."""
    try:
        _, errors, _ = loader.load_file(str(ledger_path))
        if errors:
            return False, f"Ledger validation: {len(errors)} warning(s)"
        return True, "Ledger validation passed"
    except Exception as e:
        return False, f"Ledger parse error: {e}"


def find_transaction_file(ledger_dir: Path, date_str: str, payee: str | None, narration: str | None) -> Path | None:
    """Find which file contains a transaction matching date/payee/narration."""
    tx_dir = ledger_dir / "transactions"
    if not tx_dir.exists():
        return None

    # Try most specific pattern first across all files
    for pattern in _build_search_patterns(date_str, payee, narration):
        for beancount_file in tx_dir.rglob("*.beancount"):
            try:
                content = beancount_file.read_text()
                if pattern in content:
                    return beancount_file
            except Exception:
                continue

    return None


def add_document_to_transaction(
    target_file: Path, date_str: str, payee: str, narration: str, document_path: str
) -> tuple[bool, str]:
    """Add document metadata to an existing transaction."""
    if not target_file.exists():
        return False, f"File not found: {target_file}"

    lines = target_file.read_text().splitlines(keepends=True)
    match_line = _find_transaction_line(lines, date_str, payee, narration)
    if match_line is None:
        return False, f"Transaction not found: {date_str} {payee}"

    # Check if document already exists
    for j in range(match_line + 1, min(match_line + 5, len(lines))):
        if "document:" in lines[j]:
            return False, "Transaction already has a document"

    lines.insert(match_line + 1, f'  document: "{document_path}"\n')
    target_file.write_text("".join(lines))
    return True, f"Document added to transaction in {target_file.name}"


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
    """Find and replace a transaction in the ledger files."""
    target_file = find_transaction_file(ledger_dir, original_date, original_payee, original_narration)
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
    """Find and remove a transaction from the ledger files."""
    target_file = find_transaction_file(ledger_dir, date_str, payee, narration)
    if not target_file:
        return False, f"Transaction not found: {date_str} {payee}"

    lines = target_file.read_text().splitlines(keepends=True)
    tx_start = _find_transaction_line(lines, date_str, payee, narration)
    if tx_start is None:
        return False, f"Transaction not found in file: {date_str} {payee}"

    # Find end of transaction block
    tx_end = tx_start + 1
    while tx_end < len(lines):
        current = lines[tx_end]
        s = current.strip()
        if not current.startswith("  ") and s and (s[0].isdigit() or s.startswith(";")):
            break
        tx_end += 1

    # Also remove trailing blank lines
    while tx_start > 0 and lines[tx_start - 1].strip() == "":
        tx_start -= 1

    new_lines = lines[:tx_start] + lines[tx_end:]
    target_file.write_text("".join(new_lines))

    return True, f"Transaction deleted from {target_file.name}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_search_patterns(date_str: str, payee: str | None, narration: str | None) -> list[str]:
    """Build patterns from most specific to least specific, matching both * and ! flags."""
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


def _find_transaction_line(lines: list[str], date_str: str, payee: str | None, narration: str | None) -> int | None:
    """Find the line index of a transaction header. Returns None if not found.

    Tries the most specific pattern first (date+payee+narration),
    then falls back to less specific ones.
    """
    patterns = _build_search_patterns(date_str, payee, narration)
    for pattern in patterns:
        for i, line in enumerate(lines):
            if line.rstrip().startswith(pattern):
                return i
    return None


def _parse_transaction_block(
    lines: list[str], date_str: str, payee: str | None, narration: str | None
) -> tuple[int, int, dict, list[dict], list[str]]:
    """Parse a transaction block from file lines.

    Returns (tx_start, tx_end, metadata, postings, warnings).
    Returns (-1, -1, {}, [], []) if not found.
    """
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
                    postings.append({
                        "account": parts[0],
                        "amount": float(parts[1].replace(",", "")),
                        "currency": parts[2],
                    })
                except ValueError:
                    warnings.append(f"Could not parse posting: {s}")
        j += 1

    return tx_start, j, metadata, postings, warnings
