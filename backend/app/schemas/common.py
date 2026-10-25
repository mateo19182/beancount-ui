from pydantic import BaseModel


class MessageResponse(BaseModel):
    success: bool
    message: str


class PostingInput(BaseModel):
    account: str
    amount: float
    currency: str
    signed: float | None = None
    direction: str = "auto"


class TransactionCreate(BaseModel):
    date: str
    flag: str = "*"
    payee: str | None = None
    narration: str | None = None
    postings: list[PostingInput]
    metadata: dict[str, str] | None = None


class TransactionUpdate(BaseModel):
    id: str
    date: str | None = None
    flag: str | None = None
    payee: str | None = None
    narration: str | None = None
    postings: list[PostingInput] | None = None


class TransactionDelete(BaseModel):
    id: str


class LedgerOpenRequest(BaseModel):
    path: str


class AccountCreateRequest(BaseModel):
    account: str
    date: str | None = None
    currencies: list[str] | None = None


class AccountCreateResponse(BaseModel):
    success: bool
    message: str
    account: str
