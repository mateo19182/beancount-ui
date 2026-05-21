from fastapi import APIRouter

from app.deps import state
from app.services.calculations import get_crypto_positions

router = APIRouter(prefix="/api/crypto", tags=["crypto"])


@router.get("")
def crypto():
    ledger = state.require_ledger()
    positions = get_crypto_positions(ledger)
    total_value = sum(p["value"] or 0 for p in positions)
    return {
        "currency": ledger.base_currency,
        "total_value": total_value,
        "positions": positions,
    }
