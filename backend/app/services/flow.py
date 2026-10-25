"""Money flow (in/out) inference and bank-import posting construction."""

from __future__ import annotations

Flow = str  # "in" | "out"


def migrate_legacy_direction(txn: dict) -> None:
    """Convert legacy direction field to flow when present."""
    if txn.get("flow") in ("in", "out"):
        return
    direction = txn.get("direction")
    if direction in ("positive", "reverse"):
        txn["flow"] = "in"
        txn["flow_manual"] = True
    elif direction in ("negative", "normal", "auto"):
        txn["flow"] = "out"


def infer_flow(txn: dict) -> dict:
    """Infer flow and whether signals disagree. Returns {flow, flow_conflict}."""
    amount = float(txn.get("amount") or 0)
    category = txn.get("category") or ""

    in_signals = 0
    out_signals = 0

    cdi = (txn.get("credit_debit") or "").upper()
    if cdi in ("CRDT", "CREDIT"):
        in_signals += 1
    elif cdi in ("DBIT", "DEBIT"):
        out_signals += 1

    if amount < 0:
        out_signals += 1
    elif amount > 0:
        in_signals += 1

    payee_source = txn.get("payee_source")
    if payee_source == "creditor":
        out_signals += 1
    elif payee_source == "debtor":
        in_signals += 1

    if category.startswith("Expenses:"):
        out_signals += 1
    elif category.startswith("Income:"):
        in_signals += 1

    if in_signals == 0 and out_signals == 0:
        return {"flow": "out", "flow_conflict": False}

    flow: Flow = "in" if in_signals > out_signals else "out"
    conflict = in_signals > 0 and out_signals > 0 and in_signals != out_signals
    return {"flow": flow, "flow_conflict": conflict}


def ensure_flow(txn: dict) -> None:
    """Set flow on a staged txn unless the user chose it manually."""
    migrate_legacy_direction(txn)
    if txn.get("flow_manual") and txn.get("flow") in ("in", "out"):
        return
    inferred = infer_flow(txn)
    txn["flow"] = inferred["flow"]
    txn["flow_conflict"] = inferred["flow_conflict"]


def build_import_postings(
    category: str,
    bank_account: str,
    amount: float,
    currency: str,
    flow: str,
) -> list[dict]:
    """Build balanced two-posting import entries with explicit signed amounts."""
    amt = abs(float(amount))
    if flow == "in":
        return [
            {"account": category, "amount": amt, "currency": currency, "signed": -amt},
            {"account": bank_account, "amount": amt, "currency": currency, "signed": amt},
        ]
    return [
        {"account": category, "amount": amt, "currency": currency, "signed": amt},
        {"account": bank_account, "amount": amt, "currency": currency, "signed": -amt},
    ]


def apply_simple_flow(
    postings: list[dict],
    flow: str,
    bank_account_hint: str | None = None,
) -> list[dict]:
    """Apply in/out flow to a two-posting transaction (manual entry helper)."""
    if flow not in ("in", "out") or len(postings) != 2:
        return postings

    result = []
    for posting in postings:
        p = dict(posting)
        account = p.get("account", "")
        amt = abs(float(p.get("amount") or 0))
        is_bank = _is_bank_account(account, bank_account_hint)

        if flow == "out":
            if is_bank:
                p["signed"] = -amt
            elif account.startswith("Income:"):
                p["signed"] = -amt
            else:
                p["signed"] = amt
        else:
            if is_bank:
                p["signed"] = amt
            elif account.startswith("Expenses:"):
                p["signed"] = -amt
            else:
                p["signed"] = -amt
        p["amount"] = amt
        result.append(p)
    return result


def infer_simple_flow(postings: list[dict]) -> str | None:
    """Guess in/out from signed postings when editing an existing transaction."""
    if len(postings) != 2:
        return None
    for posting in postings:
        signed = posting.get("signed")
        if signed is None:
            continue
        account = posting.get("account", "")
        if _is_bank_account(account):
            return "in" if float(signed) > 0 else "out"
    return None


def _is_bank_account(account: str, hint: str | None = None) -> bool:
    if hint and account == hint:
        return True
    lower = account.lower()
    return account.startswith("Assets:") and (
        "bank" in lower or "checking" in lower or "savings" in lower
    )
