"""Payee-to-account pattern learning and suggestion."""

import re
from collections import defaultdict
from difflib import SequenceMatcher
from beancount.core import data


def normalize_payee(payee: str) -> str:
    if not payee:
        return ""
    normalized = payee.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^\w\s]", "", normalized)
    return normalized


def learn_from_ledger(entries) -> dict[str, dict[str, int]]:
    """Build payee -> {account: count} mapping from existing transactions."""
    payee_accounts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        payee = normalize_payee(entry.payee or "")
        if not payee:
            continue
        for posting in entry.postings:
            if posting.account.startswith(("Expenses:", "Income:")):
                payee_accounts[payee][posting.account] += 1

    return dict(payee_accounts)


def suggest_account(
    payee: str, narration: str, patterns: dict[str, dict[str, int]], amount: float = 0
) -> str | None:
    """Suggest the best matching account for a payee/narration."""
    result = _best_match(payee, patterns)
    if result:
        return result

    if narration and narration != payee:
        result = _best_match(narration, patterns)
        if result:
            return result

    return "Expenses:Uncategorized" if amount < 0 else "Income:Uncategorized"


def get_all_expense_income_accounts(entries) -> list[str]:
    """Get all unique expense/income accounts from the ledger."""
    accounts = set()
    for entry in entries:
        if isinstance(entry, data.Transaction):
            for posting in entry.postings:
                if posting.account.startswith(("Expenses:", "Income:")):
                    accounts.add(posting.account)
    return sorted(accounts)


def _best_match(text: str, patterns: dict[str, dict[str, int]]) -> str | None:
    normalized = normalize_payee(text)
    if not normalized:
        return None

    scores: dict[str, float] = defaultdict(float)

    # Exact match (boosted)
    if normalized in patterns:
        for account, count in patterns[normalized].items():
            scores[account] += count * 2

    # Fuzzy match
    for learned, accounts in patterns.items():
        sim = SequenceMatcher(None, normalized, learned).ratio()
        if sim > 0.6:
            for account, count in accounts.items():
                scores[account] += count * sim

    if not scores:
        return None

    best = max(scores.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0.5 else None
