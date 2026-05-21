"""Transaction queries and filtering."""

from pathlib import Path

from beancount.core import data

from app.services.transaction_ids import make_transaction_id


def get_all_transactions(
    entries, ledger_dir: Path | None = None
) -> tuple[list[dict], list[str]]:
    """Extract all transactions with posting details.

    Returns (transactions, all_accounts) where transactions are sorted
    newest-first and all_accounts is a sorted list of every account seen.
    """
    transactions = []
    accounts = set()

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue

        accounts_list = []
        posting_amounts = []

        for posting in entry.postings:
            if posting.account:
                accounts.add(posting.account)
                accounts_list.append(posting.account)

            if posting.units and posting.units.number is not None and posting.units.number != 0:
                amount = posting.units.number
                posting_amounts.append({
                    "amount": abs(amount),
                    "currency": posting.units.currency,
                    "direction": "+" if amount > 0 else "-",
                })

        amount_strs = [
            f"{p['direction']}{p['amount']:,.2f} {p['currency']}"
            for p in posting_amounts
        ]

        has_document = "document" in (entry.meta or {})

        txn: dict = {
            "date": entry.date,
            "flag": entry.flag,
            "payee": entry.payee or "",
            "narration": entry.narration or "",
            "amount_str": ", ".join(amount_strs),
            "accounts": accounts_list,
            "posting_amounts": posting_amounts,
            "has_document": has_document,
            "document_path": entry.meta.get("document") if has_document else None,
        }
        if ledger_dir is not None:
            txn["id"] = make_transaction_id(entry, ledger_dir)
        transactions.append(txn)

    transactions.sort(key=lambda x: x["date"], reverse=True)
    return transactions, sorted(accounts)
