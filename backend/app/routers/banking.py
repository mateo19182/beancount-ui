from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.deps import state
from app.services.enable_banking.auth import (
    complete_session,
    load_sessions,
    save_sessions,
    start_authorization,
)
from app.services.enable_banking.fetch import fetch_bank_transactions, get_available_banks
from app.services.categorizer import get_all_expense_income_accounts

router = APIRouter(prefix="/api/banking", tags=["banking"])


class AuthStartRequest(BaseModel):
    bank_key: str


class AuthCompleteRequest(BaseModel):
    bank_key: str
    code: str


class FetchRequest(BaseModel):
    date_from: str
    date_to: str
    banks: list[str]


class ImportRequest(BaseModel):
    indices: list[int]
    edits: dict[int, dict] = {}


class DiscardRequest(BaseModel):
    indices: list[int]


class StagedUpdateRequest(BaseModel):
    transactions: list[dict]


def _require_banking():
    cfg = state.config.banking
    if not cfg.enabled or not cfg.app_id:
        raise HTTPException(400, "Enable Banking not configured")
    return cfg


@router.get("/status")
def banking_status():
    cfg = state.config.banking
    cache_dir = state.config.cache_dir
    banks = []
    if cache_dir and cfg.banks:
        banks = get_available_banks(cache_dir, cfg.banks)
    return {
        "enabled": cfg.enabled,
        "configured": bool(cfg.app_id and cfg.key_path),
        "banks": banks,
    }


@router.post("/auth/start")
def auth_start(body: AuthStartRequest):
    cfg = _require_banking()
    bank_cfg = cfg.banks.get(body.bank_key)
    if not bank_cfg:
        raise HTTPException(404, f"Unknown bank: {body.bank_key}")
    result = start_authorization(
        cfg.app_id, cfg.key_path, bank_cfg.get("name", body.bank_key), bank_cfg.get("country", "ES")
    )
    return {"url": result.get("url"), "state": result.get("state")}


@router.post("/auth/complete")
def auth_complete(body: AuthCompleteRequest):
    cfg = _require_banking()
    cache_dir = state.config.cache_dir
    code = body.code.strip()
    if "code=" in code:
        code = code.split("code=")[1].split("&")[0]
    session = complete_session(cfg.app_id, cfg.key_path, code, body.bank_key, cache_dir)
    return {"success": True, "accounts": len(session.get("accounts", []))}


@router.delete("/auth/{bank_key}")
def auth_revoke(bank_key: str):
    cache_dir = state.config.cache_dir
    sessions = load_sessions(cache_dir)
    sessions.pop(bank_key, None)
    save_sessions(cache_dir, sessions)
    return {"success": True}


@router.post("/fetch")
def fetch_transactions(body: FetchRequest):
    cfg = _require_banking()
    cache_dir = state.config.cache_dir
    if not body.banks:
        raise HTTPException(400, "Select at least one bank")

    data = fetch_bank_transactions(
        cfg.app_id,
        cfg.key_path,
        cache_dir,
        cfg.banks,
        body.date_from,
        body.date_to,
        body.banks,
    )
    if "error" in data:
        raise HTTPException(400, data.get("message", data["error"]))

    svc = state.bank_import
    new_count = svc.stage_fetch(data)
    return {"total": data.get("total_transactions", 0), "new_count": new_count, "errors": data.get("errors", [])}


@router.get("/staged")
def get_staged():
    state.require_ledger()
    svc = state.bank_import
    if not svc:
        raise HTTPException(503, "Bank import service unavailable")
    staged = svc.get_staged()
    staged = svc.enrich_staged(staged)
    ledger = state.require_ledger()
    categories = get_all_expense_income_accounts(ledger.entries)
    active = [t for t in staged.get("transactions", []) if not t.get("imported") and not t.get("discarded")]
    return {
        "transactions": staged.get("transactions", []),
        "active_count": len(active),
        "categories": categories,
        "fetch_date": staged.get("fetch_date"),
    }


@router.put("/staged")
def update_staged(body: StagedUpdateRequest):
    svc = state.bank_import
    svc.save_staged({"transactions": body.transactions, "fetch_date": None})
    return {"success": True}


@router.post("/import")
def import_selected(body: ImportRequest):
    svc = state.bank_import
    result = svc.import_selected(body.indices, body.edits)
    return result


@router.post("/discard")
def discard_selected(body: DiscardRequest):
    svc = state.bank_import
    count = svc.discard_selected(body.indices)
    return {"discarded": count}
