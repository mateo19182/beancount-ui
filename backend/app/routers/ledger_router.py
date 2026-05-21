from fastapi import APIRouter

from app.deps import state
from app.schemas.common import LedgerOpenRequest, MessageResponse
from app.schemas.ledger import LedgerMeta, LedgerStatus, PriceUpdateResponse, ValidateResponse
from app.services.price_fetcher import update_prices, validate_ledger as bean_validate
from app.services.price_fetcher_alt import update_prices_with_yfinance
from app.services.transaction_writer import verify_ledger

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


@router.get("/status", response_model=LedgerStatus)
def status():
    if not state.ledger:
        return LedgerStatus(loaded=False)
    ledger = state.ledger
    errors = [str(e) for e in ledger.errors[:20]]
    return LedgerStatus(
        loaded=True,
        ledger_path=str(ledger.ledger_path),
        base_currency=ledger.base_currency,
        error_count=len(ledger.errors),
        errors=errors,
    )


@router.get("/meta", response_model=LedgerMeta)
def meta():
    ledger = state.require_ledger()
    return LedgerMeta(
        ledger_path=str(ledger.ledger_path),
        base_currency=ledger.base_currency,
        accounts=ledger.accounts,
        currencies=sorted(ledger.currencies),
        error_count=len(ledger.errors),
    )


@router.post("/open", response_model=MessageResponse)
def open_ledger(body: LedgerOpenRequest):
    state.open_ledger(body.path)
    return MessageResponse(success=True, message=f"Opened {state.config.ledger_path}")


@router.post("/reload")
def reload():
    state.reload_ledger()
    if not state.ledger:
        return {"success": False, "message": "No ledger configured"}
    return {"success": True, "message": "Ledger reloaded"}


@router.post("/validate", response_model=ValidateResponse)
def validate():
    ledger = state.require_ledger()
    valid, message = bean_validate(ledger.ledger_path)
    if not valid:
        ok, fallback = verify_ledger(ledger.ledger_path)
        if ok and "bean-check" in message:
            return ValidateResponse(valid=True, message=fallback)
    return ValidateResponse(valid=valid, message=message)


@router.post("/prices", response_model=PriceUpdateResponse)
def update_prices_endpoint():
    ledger = state.require_ledger()
    success, message = update_prices(ledger.ledger_path)
    if not success and "Price fetch failed" in message:
        success, message = update_prices_with_yfinance(ledger.ledger_path)
    if success:
        state.reload_ledger()
    return PriceUpdateResponse(success=success, message=message)
