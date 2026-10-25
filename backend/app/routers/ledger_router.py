from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.deps import state
from app.schemas.common import (
    AccountCreateRequest,
    AccountCreateResponse,
    LedgerOpenRequest,
    MessageResponse,
)
from app.schemas.ledger import (
    LedgerMeta,
    LedgerReloadResponse,
    LedgerStatus,
    PriceUpdateResponse,
    ValidateResponse,
)
from app.services.price_fetcher import update_prices
from app.services.price_fetcher import validate_ledger as bean_validate
from app.services.price_fetcher_alt import update_prices_with_yfinance
from app.services.transaction_writer import (
    format_open_directive,
    is_valid_account_name,
    verify_ledger,
    write_open_directive,
)

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


@router.post("/accounts", response_model=AccountCreateResponse)
def create_account(body: AccountCreateRequest):
    ledger = state.require_ledger()
    account = body.account.strip()
    if not is_valid_account_name(account):
        raise HTTPException(400, f"Invalid account name: {account}")
    if account in ledger.accounts:
        raise HTTPException(409, f"Account already exists: {account}")
    open_date = body.date or date.today().isoformat()
    directive = format_open_directive(open_date, account, body.currencies)
    ok, message = write_open_directive(directive, ledger.ledger_path)
    if ok:
        state.reload_ledger()
    return AccountCreateResponse(success=ok, message=message, account=account)


def _validate_ledger(ledger_path: Path) -> tuple[bool, str]:
    valid, message = bean_validate(ledger_path)
    if not valid:
        ok, fallback = verify_ledger(ledger_path)
        if ok and "bean-check" in message:
            return True, fallback
    return valid, message


@router.post("/reload", response_model=LedgerReloadResponse)
def reload():
    ledger = state.require_ledger()
    messages: list[str] = []

    price_ok, price_msg = update_prices(ledger.ledger_path)
    if not price_ok and "Price fetch failed" in price_msg:
        _, price_msg = update_prices_with_yfinance(ledger.ledger_path)
    messages.append(price_msg)

    state.reload_ledger()
    messages.append("Ledger reloaded")

    valid, val_msg = _validate_ledger(ledger.ledger_path)
    messages.append(val_msg)

    return LedgerReloadResponse(valid=valid, message=" — ".join(messages))


@router.post("/validate", response_model=ValidateResponse)
def validate():
    ledger = state.require_ledger()
    valid, message = _validate_ledger(ledger.ledger_path)
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
