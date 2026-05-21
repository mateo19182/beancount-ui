from fastapi import APIRouter, HTTPException, Query

from app.deps import state
from app.schemas.common import MessageResponse, TransactionCreate, TransactionDelete, TransactionUpdate
from app.services.analytics import get_all_transactions
from app.services.transaction_writer import (
    calculate_balance,
    delete_transaction_by_id,
    determine_target_file,
    edit_transaction_by_id,
    format_transaction,
    validate_transaction,
    validate_transaction_balance,
    write_transaction,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
):
    ledger = state.require_ledger()
    config = state.config
    transactions, all_accounts = get_all_transactions(
        ledger.entries, config.ledger_dir
    )

    result = []
    for tx in transactions:
        d = tx["date"].isoformat() if hasattr(tx["date"], "isoformat") else str(tx["date"])
        if date_from and d < date_from:
            continue
        if date_to and d > date_to:
            continue
        if search:
            haystack = f"{tx['payee']} {tx['narration']} {' '.join(tx['accounts'])}".lower()
            if search.lower() not in haystack:
                continue
        result.append({
            "id": tx["id"],
            "date": d,
            "flag": tx["flag"],
            "payee": tx["payee"],
            "narration": tx["narration"],
            "amount_str": tx["amount_str"],
            "accounts": tx["accounts"],
            "posting_amounts": tx["posting_amounts"],
            "has_document": tx["has_document"],
            "document_path": tx["document_path"],
        })

    return {"transactions": result, "accounts": all_accounts}


@router.post("/preview")
def preview_transaction(body: TransactionCreate):
    ledger = state.require_ledger()
    postings = [p.model_dump() for p in body.postings]
    valid, msg = validate_transaction(postings, ledger.accounts, ledger.currencies)
    if not valid:
        raise HTTPException(400, msg)
    balanced, balance_msg = validate_transaction_balance(postings)
    preview = format_transaction(
        body.date, body.flag, body.payee, body.narration, postings, body.metadata
    )
    return {
        "valid": balanced,
        "message": balance_msg,
        "balance": calculate_balance(postings),
        "preview": preview,
    }


@router.post("", response_model=MessageResponse)
def create_transaction(body: TransactionCreate):
    ledger = state.require_ledger()
    config = state.config
    postings = [p.model_dump() for p in body.postings]

    valid, msg = validate_transaction(postings, ledger.accounts, ledger.currencies)
    if not valid:
        raise HTTPException(400, msg)
    balanced, balance_msg = validate_transaction_balance(postings)
    if not balanced:
        raise HTTPException(400, balance_msg)

    tx_str = format_transaction(
        body.date, body.flag, body.payee, body.narration, postings, body.metadata
    )
    accounts = [p["account"] for p in postings]
    target = determine_target_file(config.ledger_dir, accounts)
    ok, message = write_transaction(tx_str, target)
    if ok:
        state.reload_ledger()
    return MessageResponse(success=ok, message=message)


@router.put("", response_model=MessageResponse)
def update_transaction(body: TransactionUpdate):
    config = state.config
    new_postings = [p.model_dump() for p in body.postings] if body.postings else None

    if new_postings:
        ledger = state.require_ledger()
        valid, msg = validate_transaction(new_postings, ledger.accounts, ledger.currencies)
        if not valid:
            raise HTTPException(400, msg)
        balanced, balance_msg = validate_transaction_balance(new_postings)
        if not balanced:
            raise HTTPException(400, balance_msg)

    ok, message = edit_transaction_by_id(
        config.ledger_dir,
        body.id,
        body.date,
        body.flag,
        body.payee,
        body.narration,
        new_postings,
    )
    if ok:
        state.reload_ledger()
    return MessageResponse(success=ok, message=message)


@router.delete("", response_model=MessageResponse)
def remove_transaction(body: TransactionDelete):
    config = state.config
    ok, message = delete_transaction_by_id(config.ledger_dir, body.id)
    if ok:
        state.reload_ledger()
    return MessageResponse(success=ok, message=message)
