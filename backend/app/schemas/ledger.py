from pydantic import BaseModel


class LedgerMeta(BaseModel):
    ledger_path: str
    base_currency: str
    accounts: list[str]
    currencies: list[str]
    error_count: int


class ValidateResponse(BaseModel):
    valid: bool
    message: str


class PriceUpdateResponse(BaseModel):
    success: bool
    message: str


class LedgerReloadResponse(BaseModel):
    valid: bool
    message: str


class LedgerStatus(BaseModel):
    loaded: bool
    ledger_path: str | None = None
    base_currency: str | None = None
    error_count: int = 0
    errors: list[str] = []
