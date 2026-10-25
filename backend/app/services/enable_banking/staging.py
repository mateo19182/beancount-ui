"""JSON staging file management for bank import workflow."""

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from beancount.core import data

from app.services.flow import ensure_flow, infer_flow


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
    existing_txns = existing.get("transactions", [])
    existing_ids = {
        _canonical_id(t.get("id")) for t in existing_txns
    }
    existing_ids.discard("")
    existing_signatures = {
        signature: t
        for t in existing_txns
        if (signature := _staged_signature(t))
    }

    new_txns = []
    for bank_key, bank_data in fetch_data.get("banks", {}).items():
        bank_name = bank_data.get("bank_name", bank_key)
        for acc_data in bank_data.get("accounts", []):
            uid = acc_data.get("account_uid", "")
            acc_name = acc_data.get("account_name", uid[:8])
            raw_txns = (acc_data.get("transactions") or {}).get("transactions", [])
            for txn in raw_txns:
                staged = _convert_api_txn(txn, uid, acc_name, bank_key, bank_name)
                if not staged:
                    continue

                if staged.get("amount", 0) == 0:
                    staged["discarded"] = True

                txn_id = _canonical_id(staged.get("id"))
                signature = _staged_signature(staged)
                if txn_id and txn_id in existing_ids:
                    continue
                if signature and signature in existing_signatures:
                    existing_txn = existing_signatures[signature]
                    if txn_id and not _canonical_id(existing_txn.get("id")):
                        existing_txn["id"] = txn_id
                        existing_ids.add(txn_id)
                    continue

                new_txns.append(staged)
                if txn_id:
                    existing_ids.add(txn_id)
                if signature:
                    existing_signatures[signature] = staged

    all_txns = existing_txns + new_txns
    all_txns.sort(key=lambda x: x["date"])

    existing["transactions"] = all_txns
    existing["fetch_date"] = datetime.now().isoformat()
    save_staged(cache_dir, existing)

    return len(new_txns)


def check_duplicate(txn: dict, entries) -> str | None:
    """Check if a staged transaction is a duplicate of an existing ledger entry."""
    txn_id = _canonical_id(txn.get("id"))
    txn_date = txn.get("date", "")
    txn_amount = _money(txn.get("amount", 0))
    txn_currency = txn.get("currency", "EUR")
    txn_payee = _normalize_text(txn.get("payee") or "")
    txn_bank = txn.get("bank_key", "")

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue

        if _canonical_id(entry.meta.get("transaction_id")) == txn_id and txn_id:
            return f"Transaction ID match: {txn_id[:20]}"

        entry_date = entry.date.strftime("%Y-%m-%d")
        if entry_date != txn_date:
            continue

        bank_posting = _bank_posting(entry)
        if not bank_posting:
            continue
        entry_account, entry_amount, entry_currency = bank_posting
        if entry_currency != txn_currency:
            continue
        if abs(abs(entry_amount) - abs(txn_amount)) >= Decimal("0.01"):
            continue

        if txn_bank and not _account_matches_bank(entry_account, txn_bank):
            continue

        entry_payee = _normalize_text(entry.payee or "")
        payee_match = txn_payee and entry_payee and (
            txn_payee in entry_payee or entry_payee in txn_payee
        )
        if payee_match:
            return f"Similar transaction on {entry_date}"

        if not entry.meta.get("transaction_id"):
            return f"Same bank/date/amount on {entry_date}"

    return None


def find_staged_duplicates(transactions: list[dict]) -> dict[int, str]:
    """Return duplicate reasons for staged transactions that collide with each other."""
    seen_ids: dict[str, int] = {}
    seen_signatures: dict[tuple, int] = {}
    duplicates: dict[int, str] = {}

    for idx, txn in enumerate(transactions):
        txn_id = _canonical_id(txn.get("id"))
        if txn_id:
            if txn_id in seen_ids:
                duplicates[idx] = f"Staging duplicate ID: {txn_id[:20]}"
                duplicates.setdefault(
                    seen_ids[txn_id],
                    f"Staging duplicate ID: {txn_id[:20]}",
                )
            else:
                seen_ids[txn_id] = idx

        signature = _staged_signature(txn)
        if not signature:
            continue
        if signature in seen_signatures:
            duplicates[idx] = "Staging duplicate date/amount/payee"
            duplicates.setdefault(
                seen_signatures[signature], "Staging duplicate date/amount/payee"
            )
        else:
            seen_signatures[signature] = idx

    return duplicates


def get_bank_account(txn: dict, all_accounts: list[str]) -> str:
    """Determine which ledger account corresponds to a bank transaction."""
    bank_key = txn.get("bank_key", "")
    for account in all_accounts:
        lower = account.lower()
        if bank_key in lower or bank_key.replace("_", "") in lower:
            if "bank" in lower or "checking" in lower or "asset" in lower:
                return account
    return "Assets:Bank:Unknown"


def _convert_api_txn(
    txn: dict,
    account_uid: str,
    account_name: str,
    bank_key: str,
    bank_name: str,
) -> dict | None:
    txn_id = (
        txn.get("entryReference") or txn.get("entry_reference")
        or txn.get("transactionId") or txn.get("transaction_id", "")
    )

    date_str = (
        txn.get("bookingDate")
        or txn.get("booking_date")
        or txn.get("valueDate")
        or txn.get("value_date")
    )
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
    creditor = txn.get("creditorName") or (txn.get("creditor") or {}).get("name", "")
    debtor = txn.get("debtorName") or (txn.get("debtor") or {}).get("name", "")
    if creditor and not debtor:
        payee_source = "creditor"
    elif debtor and not creditor:
        payee_source = "debtor"
    elif creditor:
        payee_source = "creditor"
    else:
        payee_source = None
    if not payee:
        remit = txn.get("remittanceInformationUnstructured") or txn.get(
            "remittance_information", ""
        )
        if isinstance(remit, list):
            remit = remit[0] if remit else ""
        payee = remit[:50] if remit else f"{bank_name} Transaction"

    narration = txn.get("remittanceInformationUnstructured") or txn.get(
        "remittance_information", ""
    )
    if isinstance(narration, list):
        narration = narration[0] if narration else ""
    if not narration:
        narration = txn.get("additionalInformation", "")

    status = (txn.get("status") or "BOOKED").upper()
    is_pending = status in ("PDNG", "PENDING")

    credit_debit = txn.get("creditDebitIndicator") or txn.get("credit_debit_indicator")

    staged = {
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
        "payee_source": payee_source,
        "credit_debit": credit_debit,
        "flow_manual": False,
    }
    inferred = infer_flow(staged)
    staged["flow"] = inferred["flow"]
    staged["flow_conflict"] = inferred["flow_conflict"]
    return staged


def _canonical_id(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _money(value) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _staged_signature(txn: dict) -> tuple | None:
    date_str = txn.get("date")
    currency = txn.get("currency")
    payee = _normalize_text(txn.get("payee") or "")
    narration = _normalize_text(txn.get("narration") or "")
    amount = _money(txn.get("amount", 0))
    if not date_str or not currency or not payee:
        return None
    return (
        txn.get("bank_key") or "",
        txn.get("account_uid") or "",
        date_str,
        str(abs(amount)),
        currency,
        payee,
        narration,
    )


def _bank_posting(entry: data.Transaction) -> tuple[str, Decimal, str] | None:
    for posting in entry.postings:
        account = posting.account
        if not account.startswith("Assets:Bank:") or posting.units is None:
            continue
        return account, Decimal(posting.units.number), posting.units.currency
    return None


def _account_matches_bank(account: str, bank_key: str) -> bool:
    compact_account = account.casefold().replace("_", "")
    compact_bank = bank_key.casefold().replace("_", "")
    return compact_bank in compact_account
