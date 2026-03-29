"""Fetch transactions from banks via Enable Banking API."""

from datetime import datetime
from .auth import load_sessions, get_account_transactions, get_auth_headers
import requests

API_BASE_URL = "https://api.enablebanking.com"


def fetch_bank_transactions(
    app_id: str, key_path: str, cache_dir, bank_configs: dict,
    date_from: str, date_to: str, selected_banks: list[str],
) -> dict:
    """Fetch transactions from selected banks.

    Returns {banks: {bank_key: {bank_name, accounts: [...]}}, total_transactions: int}
    """
    from pathlib import Path
    sessions = load_sessions(Path(cache_dir))

    if not sessions:
        return {"error": "no_sessions", "message": "No authorized banks found"}

    result = {
        "fetch_date": datetime.now().isoformat(),
        "date_from": date_from,
        "date_to": date_to,
        "banks": {},
    }
    total = 0

    for bank_key in selected_banks:
        if bank_key not in sessions:
            continue

        session = sessions[bank_key]
        config = bank_configs.get(bank_key, {})
        bank_name = config.get("name", bank_key)
        accounts = session.get("accounts", [])

        accounts_data = []
        for account in accounts:
            uid = account.get("uid")
            try:
                txns = get_account_transactions(app_id, key_path, uid, date_from, date_to)
                accounts_data.append({
                    "account_uid": uid,
                    "account_name": account.get("name", uid[:8]),
                    "transactions": txns,
                })
                total += len((txns or {}).get("transactions", []))
            except Exception as e:
                print(f"Error fetching {bank_key}/{uid}: {e}")

        if accounts_data:
            result["banks"][bank_key] = {
                "bank_name": bank_name,
                "accounts": accounts_data,
            }

    result["total_transactions"] = total
    return result


def get_available_banks(cache_dir, bank_configs: dict) -> list[dict]:
    """Get list of banks with authorization status."""
    from pathlib import Path
    sessions = load_sessions(Path(cache_dir))
    banks = []

    for key, config in bank_configs.items():
        name = config.get("name", key)
        session = sessions.get(key)
        if session:
            count = len(session.get("accounts", []))
            banks.append({
                "key": key,
                "name": name,
                "accounts": count,
                "authorized": True,
            })
        else:
            banks.append({
                "key": key,
                "name": name,
                "accounts": 0,
                "authorized": False,
            })

    return banks
