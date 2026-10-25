"""Bank import commit logic extracted from import review page."""

from pathlib import Path

from app.services.categorizer import learn_from_ledger, suggest_account
from app.services.enable_banking.staging import (
    check_duplicate,
    find_staged_duplicates,
    get_bank_account,
    load_staged,
    save_staged,
    stage_transactions,
)
from app.services.flow import build_import_postings, ensure_flow
from app.services.transaction_writer import (
    format_transaction,
    validate_transaction_balance,
    verify_ledger,
    write_transaction,
)


class BankImportService:
    def __init__(self, ledger, config):
        self.ledger = ledger
        self.config = config
        self.cache_dir = config.cache_dir

    def get_staged(self) -> dict:
        return load_staged(self.cache_dir)

    def save_staged(self, data: dict) -> None:
        save_staged(self.cache_dir, data)

    def enrich_staged(self, staged: dict) -> dict:
        learned = learn_from_ledger(self.ledger.entries)
        transactions = staged.get("transactions", [])
        staging_duplicates = find_staged_duplicates(transactions)
        for idx, txn in enumerate(transactions):
            if not txn.get("imported") and not txn.get("discarded") and txn.get("amount", 0) == 0:
                txn["discarded"] = True
            if not txn.get("category"):
                txn["category"] = suggest_account(
                    txn.get("payee", ""),
                    txn.get("narration", ""),
                    learned,
                    txn.get("amount", 0),
                )
            ensure_flow(txn)
            txn["duplicate"] = staging_duplicates.get(idx) or check_duplicate(
                txn, self.ledger.entries
            )
        return staged

    def stage_fetch(self, fetch_data: dict) -> int:
        return stage_transactions(self.cache_dir, fetch_data)

    def import_selected(self, indices: list[int], edits: dict[int, dict]) -> dict:
        staged = load_staged(self.cache_dir)
        all_txns = staged.get("transactions", [])
        success_count = 0
        error_count = 0
        balance_errors: list[str] = []
        staging_duplicates = find_staged_duplicates(all_txns)

        for idx in indices:
            if idx >= len(all_txns):
                error_count += 1
                continue
            txn = all_txns[idx]
            edited = edits.get(idx, {})

            if idx in staging_duplicates:
                txn["duplicate"] = staging_duplicates[idx]
                txn["selected"] = False
                error_count += 1
                continue

            payee = edited.get("payee") or txn.get("payee", "")
            narration = edited.get("narration") or txn.get("narration", "")
            category = edited.get("category") or txn.get("category")
            flow = edited.get("flow") or txn.get("flow", "out")

            duplicate = check_duplicate(txn, self.ledger.entries)
            if duplicate:
                txn["duplicate"] = duplicate
                txn["selected"] = False
                error_count += 1
                continue

            if txn.get("amount", 0) == 0:
                txn["discarded"] = True
                txn["selected"] = False
                continue

            if not category:
                error_count += 1
                continue

            txn.update({
                "payee": payee,
                "narration": narration,
                "category": category,
                "flow": flow,
            })
            if edited.get("flow"):
                txn["flow_manual"] = True

            flag = "!" if txn.get("status") == "Pending" else "*"
            bank_account = get_bank_account(txn, self.ledger.accounts)
            amount = txn.get("amount", 0)
            currency = txn.get("currency", "EUR")

            metadata = {
                "transaction_id": txn.get("id", ""),
                "source": txn.get("bank_key", ""),
            }
            if txn.get("document_path"):
                metadata["document"] = txn["document_path"]

            postings = build_import_postings(
                category, bank_account, amount, currency, flow
            )

            is_valid, validation_msg = validate_transaction_balance(postings)
            if not is_valid:
                balance_errors.append(f"{txn.get('date', '')} {payee}: {validation_msg}")
                error_count += 1
                continue

            tx_str = format_transaction(
                txn["date"], flag, payee, narration, postings, metadata
            )
            month_key = txn["date"][:7]
            target = (
                self.ledger.ledger_path.parent
                / "transactions"
                / "banks"
                / f"{month_key}.beancount"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            ok, _ = write_transaction(tx_str, target)
            if ok:
                success_count += 1
                txn["imported"] = True
                txn["selected"] = False
            else:
                error_count += 1

        save_staged(self.cache_dir, {"transactions": all_txns})
        valid, validation_msg = verify_ledger(self.ledger.ledger_path)
        if success_count:
            self.ledger.reload()

        return {
            "success_count": success_count,
            "error_count": error_count,
            "balance_errors": balance_errors,
            "ledger_valid": valid,
            "validation_message": validation_msg,
        }

    def discard_selected(self, indices: list[int]) -> int:
        staged = load_staged(self.cache_dir)
        all_txns = staged.get("transactions", [])
        count = 0
        for idx in indices:
            if idx < len(all_txns):
                all_txns[idx]["discarded"] = True
                all_txns[idx]["selected"] = False
                count += 1
        save_staged(self.cache_dir, {"transactions": all_txns})
        return count
