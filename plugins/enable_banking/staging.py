"""JSON staging file management for bank import workflow."""

import json
from datetime import datetime
from pathlib import Path
from beancount.core import data


def get_staging_file(cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "staging.json"


def load_staged(cache_dir: Path) -> dict:
    f = get_staging_file(cache_dir)
    if f.exists():
        try:
            content = f.read_text().strip()
            if content:
                return json.loads(content)
        except (json.JSONDecodeError, IOError):
            pass
    return {"transactions": [], "fetch_date": None}


def save_staged(cache_dir: Path, staged: dict):
    f = get_staging_file(cache_dir)
    f.write_text(json.dumps(staged, indent=2))


def stage_transactions(cache_dir: Path, fetch_data: dict) -> int:
    """Convert fetched API transactions to staged format. Returns count of new transactions."""
    existing = load_staged(cache_dir)
    existing_ids = {t["id"] for t in existing.get("transactions", [])}

    new_txns = []
    for bank_key, bank_data in fetch_data.get("banks", {}).items():
        bank_name = bank_data.get("bank_name", bank_key)
        for acc_data in bank_data.get("accounts", []):
            uid = acc_data.get("account_uid", "")
            acc_name = acc_data.get("account_name", uid[:8])
            raw_txns = (acc_data.get("transactions") or {}).get("transactions", [])
            for txn in raw_txns:
                staged = _convert_api_txn(txn, uid, acc_name, bank_key, bank_name)
                if staged and staged["id"] not in existing_ids:
                    new_txns.append(staged)
                    existing_ids.add(staged["id"])

    all_txns = existing.get("transactions", []) + new_txns
    all_txns.sort(key=lambda x: x["date"])

    existing["transactions"] = all_txns
    existing["fetch_date"] = datetime.now().isoformat()
    save_staged(cache_dir, existing)

    return len(new_txns)


def check_duplicate(txn: dict, entries) -> str | None:
    """Check if a staged transaction is a duplicate of an existing ledger entry."""
    txn_id = txn.get("id", "")
    txn_date = txn.get("date", "")
    txn_amount = txn.get("amount", 0)
    txn_payee = (txn.get("payee") or "").lower()

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue

        if entry.meta.get("transaction_id") == txn_id and txn_id:
            return f"Transaction ID match: {txn_id[:20]}"

        entry_date = entry.date.strftime("%Y-%m-%d")
        entry_payee = (entry.payee or "").lower()
        entry_amount = float(entry.postings[0].units.number) if entry.postings else 0

        if entry_date == txn_date:
            amount_match = abs(abs(entry_amount) - abs(txn_amount)) < 0.01
            payee_match = txn_payee and entry_payee and (txn_payee in entry_payee or entry_payee in txn_payee)
            if amount_match and payee_match:
                return f"Similar transaction on {entry_date}"

    return None


def get_bank_account(txn: dict, all_accounts: list[str]) -> str:
    """Determine which ledger account corresponds to a bank transaction."""
    bank_key = txn.get("bank_key", "")
    for account in all_accounts:
        lower = account.lower()
        if bank_key in lower or bank_key.replace("_", "") in lower:
            if "bank" in lower or "checking" in lower or "asset" in lower:
                return account
    return "Assets:Bank:Unknown"


def _convert_api_txn(txn: dict, account_uid: str, account_name: str, bank_key: str, bank_name: str) -> dict | None:
    txn_id = (
        txn.get("entryReference") or txn.get("entry_reference")
        or txn.get("transactionId") or txn.get("transaction_id", "")
    )

    date_str = txn.get("bookingDate") or txn.get("booking_date") or txn.get("valueDate") or txn.get("value_date")
    if not date_str:
        return None
    date_str = date_str[:10]

    txn_amount = txn.get("transactionAmount") or txn.get("transaction_amount", {})
    amount_str = txn_amount.get("amount", "0") if isinstance(txn_amount, dict) else "0"
    currency = txn_amount.get("currency", "EUR") if isinstance(txn_amount, dict) else "EUR"
    try:
        amount = float(amount_str)
    except (ValueError, TypeError):
        amount = 0.0

    payee = (
        txn.get("creditorName") or (txn.get("creditor") or {}).get("name", "")
        or txn.get("debtorName") or (txn.get("debtor") or {}).get("name", "")
    )
    if not payee:
        remit = txn.get("remittanceInformationUnstructured") or txn.get("remittance_information", "")
        if isinstance(remit, list):
            remit = remit[0] if remit else ""
        payee = remit[:50] if remit else f"{bank_name} Transaction"

    narration = txn.get("remittanceInformationUnstructured") or txn.get("remittance_information", "")
    if isinstance(narration, list):
        narration = narration[0] if narration else ""
    if not narration:
        narration = txn.get("additionalInformation", "")

    status = (txn.get("status") or "BOOKED").upper()
    is_pending = status in ("PDNG", "PENDING")

    return {
        "id": txn_id,
        "date": date_str,
        "payee": payee[:100],
        "narration": narration[:200],
        "amount": amount,
        "currency": currency,
        "status": "Pending" if is_pending else "Booked",
        "bank": bank_name,
        "bank_key": bank_key,
        "account_uid": account_uid,
        "account_name": account_name,
        "selected": True,
        "category": None,
    }
