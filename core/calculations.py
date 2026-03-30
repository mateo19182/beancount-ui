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


def get_monthly_income_expenses(
    ledger, year: int, month: int
) -> tuple[Decimal, Decimal]:
    """Calculate total income and expenses for a specific month.

    Returns (total_income, total_expenses) in base currency.
    Income is identified by Income: accounts.
    Expenses is identified by Expenses: accounts.
    """
    from beancount.core import data as core_data

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    total_income = Decimal(0)
    total_expenses = Decimal(0)

    for entry in ledger.entries:
        if not isinstance(entry, core_data.Transaction):
            continue
        if entry.date < start_date or entry.date >= end_date:
            continue

        for posting in entry.postings:
            account = posting.account
            amount = posting.units.number
            currency = posting.units.currency

            converted = ledger.convert_to_currency(amount, currency)
            if converted is None:
                continue

            if account.startswith("Income:"):
                # Income is negative (increasing net worth), but we want positive value
                total_income += abs(converted)
            elif account.startswith("Expenses:"):
                # Expenses are positive (decreasing net worth)
                total_expenses += abs(converted)

    return total_income, total_expenses


def get_category_breakdown(
    ledger, year: int, month: int, account_prefix: str
) -> dict[str, dict]:
    """Get category breakdown for income or expenses with subcategory support.

    Returns dict with hierarchical structure:
    {category_name: {
        "total": Decimal,
        "subcategories": {subcat_name: {"total": Decimal, ...}, ...},
        "accounts": [...]
    }}
    """
    from beancount.core import data as core_data

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    categories: dict[str, dict] = {}

    for entry in ledger.entries:
        if not isinstance(entry, core_data.Transaction):
            continue
        if entry.date < start_date or entry.date >= end_date:
            continue

        for posting in entry.postings:
            account = posting.account
            if not account.startswith(f"{account_prefix}:"):
                continue

            parts = account.split(":")
            if len(parts) < 2:
                continue

            main_category = parts[1]
            subcategory = parts[2] if len(parts) >= 3 else "Other"

            amount = posting.units.number
            currency = posting.units.currency
            converted = ledger.convert_to_currency(amount, currency)
            if converted is None:
                continue

            if main_category not in categories:
                categories[main_category] = {
                    "total": Decimal(0),
                    "subcategories": {},
                    "accounts": [],
                }

            categories[main_category]["total"] += abs(converted)

            if subcategory not in categories[main_category]["subcategories"]:
                categories[main_category]["subcategories"][subcategory] = {
                    "total": Decimal(0),
                    "accounts": [],
                }

            categories[main_category]["subcategories"][subcategory]["total"] += abs(
                converted
            )
            categories[main_category]["subcategories"][subcategory]["accounts"].append(
                {
                    "account": account,
                    "amount": abs(amount),
                    "currency": currency,
                    "value": abs(converted),
                }
            )

            categories[main_category]["accounts"].append(
                {
                    "account": account,
                    "amount": abs(amount),
                    "currency": currency,
                    "value": abs(converted),
                    "subcategory": subcategory,
                }
            )

    # Remove zero totals and sort by value
    return {k: v for k, v in categories.items() if v["total"] > 0}


def get_available_months(ledger) -> list[tuple[int, int]]:
    """Get list of (year, month) tuples that have transaction data.

    Returns sorted list from oldest to newest.
    """
    from beancount.core import data as core_data

    months = set()

    for entry in ledger.entries:
        if isinstance(entry, core_data.Transaction):
            months.add((entry.date.year, entry.date.month))

    return sorted(months)


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
        categories[category]["accounts"].append(
            {
                "account": b["account"],
                "currency": b["currency"],
                "amount": b["amount"],
                "value": converted,
            }
        )

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
                    positions.append(
                        {
                            "symbol": commodity,
                            "shares": float(amount),
                            "price": price,
                            "value": value,
                            "account": account_path,
                        }
                    )

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
                if any(
                    kw in lower for kw in ("investment", "broker", "trading", "stock")
                ):
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

        positions.append(
            {
                "symbol": symbol,
                "amount": total,
                "price": price,
                "value": value,
            }
        )

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
