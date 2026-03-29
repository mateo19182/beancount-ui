"""Financial calculations: net worth, asset categories, positions."""

from decimal import Decimal
from beancount.core import prices
from datetime import date


def calculate_net_worth(ledger) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate (net_worth, total_assets, total_liabilities) in base currency."""
    assets = ledger.get_assets()
    liabilities = ledger.get_liabilities()

    total_assets = Decimal(0)
    for b in assets:
        converted = ledger.convert_to_currency(b["amount"], b["currency"])
        if converted is not None:
            total_assets += converted

    total_liabilities = Decimal(0)
    for b in liabilities:
        converted = ledger.convert_to_currency(b["amount"], b["currency"])
        if converted is not None:
            total_liabilities += abs(converted)

    return total_assets - total_liabilities, total_assets, total_liabilities


def get_assets_by_category(ledger) -> dict[str, dict]:
    """Assets grouped by top-level category (Bank, Investment, Crypto, etc.)."""
    assets = ledger.get_assets()
    categories: dict[str, dict] = {}

    for b in assets:
        parts = b["account"].split(":")
        category = parts[1] if len(parts) >= 2 else "Other"

        converted = ledger.convert_to_currency(b["amount"], b["currency"])
        if converted is None:
            continue

        if category not in categories:
            categories[category] = {"total": Decimal(0), "accounts": []}

        categories[category]["total"] += converted
        categories[category]["accounts"].append({
            "account": b["account"],
            "currency": b["currency"],
            "amount": b["amount"],
            "value": converted,
        })

    return categories


def get_stock_positions(ledger) -> list[dict]:
    """Find all stock/equity holdings across the ledger.

    Detects stocks by finding non-fiat commodities held under
    investment-related accounts (any account containing 'Investment' or 'Broker').
    """
    real_root = ledger.realize()
    positions = []

    def scan_node(node, account_path: str = ""):
        if hasattr(node, "balance") and not node.balance.is_empty():
            for key, position in node.balance.items():
                commodity = key[0] if isinstance(key, tuple) else key
                amount = position.units.number

                if amount > 0 and not ledger.is_fiat_currency(commodity):
                    price = _get_latest_price(ledger, commodity)
                    value = float(amount) * price if price else None
                    positions.append({
                        "symbol": commodity,
                        "shares": float(amount),
                        "price": price,
                        "value": value,
                        "account": account_path,
                    })

        if hasattr(node, "keys"):
            for key in node.keys():
                child = f"{account_path}:{key}" if account_path else key
                scan_node(node[key], child)

    # Scan investment-related subtrees
    if "Assets" in real_root:
        assets_node = real_root["Assets"]
        if hasattr(assets_node, "keys"):
            for key in assets_node.keys():
                lower = key.lower()
                if any(kw in lower for kw in ("investment", "broker", "trading", "stock")):
                    scan_node(assets_node[key], f"Assets:{key}")

    return sorted(positions, key=lambda x: x["value"] or 0, reverse=True)


def get_crypto_positions(ledger) -> list[dict]:
    """Find all cryptocurrency holdings across the ledger.

    Detects crypto by finding non-fiat commodities held under
    accounts containing 'Crypto' in their path.
    """
    real_root = ledger.realize()
    holdings: dict[str, dict] = {}

    def scan_node(node, account_path: str = ""):
        if hasattr(node, "balance") and not node.balance.is_empty():
            for key, position in node.balance.items():
                commodity = key[0] if isinstance(key, tuple) else key
                amount = position.units.number

                if amount > 0 and not ledger.is_fiat_currency(commodity):
                    if commodity not in holdings:
                        holdings[commodity] = {"total": Decimal(0), "accounts": []}
                    holdings[commodity]["total"] += amount
                    holdings[commodity]["accounts"].append(account_path)

        if hasattr(node, "keys"):
            for key in node.keys():
                child = f"{account_path}:{key}" if account_path else key
                scan_node(node[key], child)

    # Scan crypto-related subtrees
    if "Assets" in real_root:
        assets_node = real_root["Assets"]
        if hasattr(assets_node, "keys"):
            for key in assets_node.keys():
                if "crypto" in key.lower():
                    scan_node(assets_node[key], f"Assets:{key}")

    positions = []
    for symbol, info in holdings.items():
        price = _get_latest_price(ledger, symbol)
        total = float(info["total"])
        value = total * price if price else None

        positions.append({
            "symbol": symbol,
            "amount": total,
            "price": price,
            "value": value,
        })

    return sorted(positions, key=lambda x: x["value"] or 0, reverse=True)


def _get_latest_price(ledger, commodity: str) -> float | None:
    """Get the latest price for a commodity in the base currency."""
    today = date.today()
    base = ledger.base_currency

    # Try direct price to base currency
    rate = prices.get_price(ledger.price_map, (commodity, base), today)
    if rate and rate[1] is not None:
        return float(rate[1])

    # Try via USD
    if base != "USD":
        rate = prices.get_price(ledger.price_map, (commodity, "USD"), today)
        if rate and rate[1] is not None:
            usd_price = float(rate[1])
            fx = ledger.convert_to_currency(Decimal(1), "USD")
            if fx is not None:
                return usd_price * float(fx)

    # Try via EUR
    if base != "EUR":
        rate = prices.get_price(ledger.price_map, (commodity, "EUR"), today)
        if rate and rate[1] is not None:
            eur_price = float(rate[1])
            fx = ledger.convert_to_currency(Decimal(1), "EUR")
            if fx is not None:
                return eur_price * float(fx)

    return None
