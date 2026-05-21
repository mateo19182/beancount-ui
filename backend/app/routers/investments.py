from fastapi import APIRouter

from app.deps import state
from app.services.calculations import get_stock_positions

router = APIRouter(prefix="/api/investments", tags=["investments"])


@router.get("")
def investments():
    ledger = state.require_ledger()
    positions = get_stock_positions(ledger)
    total_value = sum(p["value"] or 0 for p in positions)
    return {
        "currency": ledger.base_currency,
        "total_value": total_value,
        "positions": positions,
    }
