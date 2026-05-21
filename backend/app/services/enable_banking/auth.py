"""Enable Banking OAuth PKCE flow and session management."""

import json
import webbrowser
from datetime import datetime, timezone, timedelta
from pathlib import Path

import jwt
import requests

API_BASE_URL = "https://api.enablebanking.com"


def create_jwt(app_id: str, key_path: str) -> str:
    """Create JWT for API authentication."""
    with open(key_path, "rb") as f:
        private_key = f.read()

    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": app_id})


def get_auth_headers(app_id: str, key_path: str) -> dict:
    token = create_jwt(app_id, key_path)
    return {"Authorization": f"Bearer {token}"}


def get_sessions_file(cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "sessions.json"


def load_sessions(cache_dir: Path) -> dict[str, dict]:
    f = get_sessions_file(cache_dir)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_sessions(cache_dir: Path, sessions: dict):
    f = get_sessions_file(cache_dir)
    f.write_text(json.dumps(sessions, indent=2))


def start_authorization(app_id: str, key_path: str, bank_name: str, country: str) -> dict:
    """Start OAuth authorization. Returns dict with 'url' to redirect user to."""
    headers = get_auth_headers(app_id, key_path)

    # Find ASPSP
    r = requests.get(f"{API_BASE_URL}/aspsps?country={country}", headers=headers)
    r.raise_for_status()
    aspsps = r.json().get("aspsps", [])
    aspsp = next((a for a in aspsps if bank_name.lower() in a.get("name", "").lower()), None)
    if not aspsp:
        raise ValueError(f"Bank not found: {bank_name}")

    # Get redirect URL
    r = requests.get(f"{API_BASE_URL}/application", headers=headers)
    r.raise_for_status()
    redirect_urls = r.json().get("redirect_urls", [])
    if not redirect_urls:
        raise ValueError("No redirect URLs registered")

    valid_until = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
    body = {
        "access": {"valid_until": valid_until},
        "aspsp": {"name": aspsp["name"], "country": aspsp["country"]},
        "state": "beancount-ui-import",
        "redirect_url": redirect_urls[0],
        "psu_type": "personal",
    }

    r = requests.post(f"{API_BASE_URL}/auth", json=body, headers=headers)
    r.raise_for_status()
    return r.json()


def complete_session(app_id: str, key_path: str, code: str, bank_key: str, cache_dir: Path) -> dict:
    """Complete authorization and save session."""
    headers = get_auth_headers(app_id, key_path)
    r = requests.post(f"{API_BASE_URL}/sessions", json={"code": code}, headers=headers)
    r.raise_for_status()

    session = r.json()
    sessions = load_sessions(cache_dir)
    sessions[bank_key] = session
    save_sessions(cache_dir, sessions)
    return session


def get_account_transactions(app_id: str, key_path: str, account_uid: str,
                              date_from: str | None = None, date_to: str | None = None) -> dict:
    headers = get_auth_headers(app_id, key_path)
    params = {}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    r = requests.get(f"{API_BASE_URL}/accounts/{account_uid}/transactions", headers=headers, params=params)
    r.raise_for_status()
    return r.json()
