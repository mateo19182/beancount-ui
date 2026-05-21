from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.deps import state
from app.services.calculations import get_assets_by_category

router = APIRouter(prefix="/api/banks", tags=["banks"])


@router.get("/balances")
def bank_balances():
    ledger = state.require_ledger()
    categories = get_assets_by_category(ledger)
    bank_data = categories.get("Bank", {"total": 0, "accounts": []})
    currency = ledger.base_currency

    aggregated: dict[str, float] = {}
    positions_by_account: dict[str, list] = {}
    for acc in bank_data.get("accounts", []):
        name = acc["account"]
        aggregated[name] = aggregated.get(name, 0.0) + float(acc["value"])
        positions_by_account.setdefault(name, []).append({
            "currency": acc["currency"],
            "amount": float(acc["amount"]),
            "value": float(acc["value"]),
        })

    accounts = [
        {
            "account": name,
            "value": value,
            "positions": positions_by_account.get(name, []),
        }
        for name, value in sorted(aggregated.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "total": float(bank_data["total"]),
        "currency": currency,
        "accounts": accounts,
    }


@router.get("")
def list_bank_files():
    ledger = state.require_ledger()
    banks_dir = ledger.ledger_path.parent / "transactions" / "banks"
    files = []
    if banks_dir.exists():
        for f in sorted(banks_dir.glob("*.beancount"), reverse=True):
            stat = f.stat()
            files.append({
                "name": f.name,
                "path": str(f.relative_to(ledger.ledger_path.parent)),
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
            })
    return {"files": files}


@router.get("/file")
def read_bank_file(path: str):
    ledger = state.require_ledger()
    ledger_root = ledger.ledger_path.parent.resolve()
    target = (ledger_root / path).resolve()
    if not str(target).startswith(str(ledger_root)):
        raise HTTPException(400, "Invalid path")
    if not target.exists() or "banks" not in str(target):
        raise HTTPException(404, "File not found")
    return {"path": path, "content": target.read_text()}
