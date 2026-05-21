"""Consolidated posting sign logic for beancount transactions."""


def signed_amount(posting: dict, postings: list[dict]) -> float:
    """Compute the signed amount for a single posting."""
    account = posting["account"]
    amount = posting["amount"]
    currency = posting["currency"]
    direction = posting.get("direction", "auto")
    is_bank_account = "Bank" in account or account.startswith("Assets:")

    has_expense = any(p["account"].startswith("Expenses:") for p in postings)
    has_income = any(p["account"].startswith("Income:") for p in postings)

    if is_bank_account and direction == "reverse":
        return abs(amount)
    if is_bank_account and direction == "normal":
        return -abs(amount)
    if amount < 0:
        return amount
    if account.startswith("Expenses:"):
        return abs(amount)
    if account.startswith("Income:"):
        return -abs(amount)
    if has_expense:
        return -abs(amount)
    if has_income:
        return abs(amount)
    return amount


def balance_by_currency(postings: list[dict]) -> dict[str, float]:
    """Calculate balance per currency for postings."""
    balance: dict[str, float] = {}
    for posting in postings:
        currency = posting["currency"]
        signed = signed_amount(posting, postings)
        balance[currency] = balance.get(currency, 0.0) + signed
    return balance


def is_balanced(postings: list[dict], tolerance: float = 0.005) -> tuple[bool, str]:
    """Check whether postings balance to zero per currency."""
    if len(postings) < 2:
        return False, "Transaction must have at least 2 postings"

    balances = balance_by_currency(postings)
    for currency, balance in balances.items():
        if abs(balance) > tolerance:
            return False, f"Transaction unbalanced: {balance:.2f} {currency}"
    return True, "Transaction balances"
