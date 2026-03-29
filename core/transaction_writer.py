"""Format, validate, and write beancount transactions."""

from pathlib import Path
from beancount import loader


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
        header += f' "{payee}"'
    if narration:
        header += f' "{narration}"'

    lines = [header]

    if metadata:
        for key, value in metadata.items():
            lines.append(f'  {key}: "{value}"')

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

    patterns = _build_search_patterns(date_str, payee, narration)

    for beancount_file in tx_dir.rglob("*.beancount"):
        try:
            content = beancount_file.read_text()
            for pattern in patterns:
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
    patterns = _build_search_patterns(date_str, payee, narration)

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if any(stripped.startswith(p) for p in patterns):
            # Check if document already exists
            for j in range(i + 1, min(i + 5, len(lines))):
                if "document:" in lines[j]:
                    return False, "Transaction already has a document"

            lines.insert(i + 1, f'  document: "{document_path}"\n')
            target_file.write_text("".join(lines))
            return True, f"Document added to transaction in {target_file.name}"

    return False, f"Transaction not found: {date_str} {payee}"


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
    patterns = _build_search_patterns(original_date, original_payee, original_narration)

    tx_start = -1
    tx_end = -1
    original_metadata = {}
    original_posting_data = []

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if not any(stripped.startswith(p) for p in patterns):
            continue

        tx_start = i
        j = i + 1
        while j < len(lines):
            current = lines[j]
            s = current.strip()

            if not current.startswith("  ") and s and (s[0].isdigit() or s.startswith(";")):
                break

            if ": " in s[:50] and not s.startswith(";"):
                parts = s.split(": ", 1)
                if len(parts) == 2:
                    original_metadata[parts[0].strip()] = parts[1].strip().strip('"')
            elif s and not s.startswith(";"):
                parts = s.split()
                if len(parts) >= 3:
                    try:
                        original_posting_data.append({
                            "account": parts[0],
                            "amount": float(parts[1].replace(",", "")),
                            "currency": parts[2],
                        })
                    except ValueError:
                        pass
            j += 1

        tx_end = j
        break

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

    new_lines = lines[:tx_start] + [new_tx + "\n"] + lines[tx_end:]
    target_file.write_text("".join(new_lines))

    return True, f"Transaction updated in {target_file.name}"


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
    patterns = _build_search_patterns(date_str, payee, narration)

    tx_start = -1
    tx_end = -1

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if not any(stripped.startswith(p) for p in patterns):
            continue

        tx_start = i
        j = i + 1
        while j < len(lines):
            current = lines[j]
            s = current.strip()
            if not current.startswith("  ") and s and (s[0].isdigit() or s.startswith(";")):
                break
            j += 1
        tx_end = j

        # Also remove any blank lines immediately before the transaction
        while tx_start > 0 and lines[tx_start - 1].strip() == "":
            tx_start -= 1

        break

    if tx_start < 0:
        return False, f"Transaction not found in file: {date_str} {payee}"

    new_lines = lines[:tx_start] + lines[tx_end:]
    target_file.write_text("".join(new_lines))

    return True, f"Transaction deleted from {target_file.name}"


def _build_search_patterns(date_str: str, payee: str | None, narration: str | None) -> list[str]:
    """Build patterns from most specific to least specific, matching both * and ! flags."""
    patterns = []
    if payee and narration:
        patterns.append(f'{date_str} * "{payee}" "{narration}"')
        patterns.append(f'{date_str} ! "{payee}" "{narration}"')
    if payee:
        patterns.append(f'{date_str} * "{payee}"')
        patterns.append(f'{date_str} ! "{payee}"')
    return patterns
