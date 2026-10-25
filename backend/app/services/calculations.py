"""Financial calculations: net worth, asset categories, positions."""

from decimal import Decimal

from beancount.core import prices
from datetime import date


def _posting_amount_in_base(ledger, posting) -> Decimal | None:
    """Posting amount converted to base currency, or None if not quantified."""
    units = posting.units
    if units is None or units.number is None or units.number == 0:
        return None
    return ledger.convert_to_currency(units.number, units.currency)


def _pnl_flow(account: str, amount_base: Decimal) -> Decimal:
    """Signed P&L flow: income earned and expenses spent are positive."""
    if account.startswith("Income:"):
        return -amount_base
    if account.startswith("Expenses:"):
        return amount_base
    return Decimal(0)


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


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return (start inclusive, end exclusive) for a calendar month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def inclusive_range_bounds(start: date, end: date) -> tuple[date, date]:
    """Convert inclusive [start, end] dates to [start, end_exclusive)."""
    return start, end.fromordinal(end.toordinal() + 1)


def months_in_inclusive_range(start: date, end: date) -> list[tuple[int, int]]:
    """Calendar months overlapping an inclusive date range."""
    months: list[tuple[int, int]] = []
    y, m = start.year, start.month
    while date(y, m, 1) <= date(end.year, end.month, 1):
        months.append((y, m))
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return months


def get_income_expenses_for_range(
    ledger, start: date, end_exclusive: date
) -> tuple[Decimal, Decimal]:
    """Total income and expenses between start (inclusive) and end (exclusive)."""
    from beancount.core import data as core_data

    total_income = Decimal(0)
    total_expenses = Decimal(0)

    for entry in ledger.entries:
        if not isinstance(entry, core_data.Transaction):
            continue
        if entry.date < start or entry.date >= end_exclusive:
            continue

        for posting in entry.postings:
            account = posting.account
            converted = _posting_amount_in_base(ledger, posting)
            if converted is None:
                continue

            flow = _pnl_flow(account, converted)
            if account.startswith("Income:"):
                total_income += flow
            elif account.startswith("Expenses:"):
                total_expenses += flow

    return total_income, total_expenses


def get_monthly_income_expenses(
    ledger, year: int, month: int
) -> tuple[Decimal, Decimal]:
    """Calculate total income and expenses for a specific month."""
    start, end = month_bounds(year, month)
    return get_income_expenses_for_range(ledger, start, end)


def get_monthly_income_expenses_series(
    ledger, start: date, end_exclusive: date
) -> list[dict]:
    """Monthly income/expense totals for each month overlapping a date range."""
    last_inclusive = end_exclusive.fromordinal(end_exclusive.toordinal() - 1)
    series: list[dict] = []
    for year, month in months_in_inclusive_range(start, last_inclusive):
        m_start, m_end = month_bounds(year, month)
        income, expenses = get_income_expenses_for_range(ledger, m_start, m_end)
        series.append(
            {
                "year": year,
                "month": month,
                "income": income,
                "expenses": expenses,
            }
        )
    return series


def get_category_breakdown_for_range(
    ledger, start: date, end_exclusive: date, account_prefix: str
) -> dict[str, dict]:
    """Category breakdown for income or expenses in a date range (end exclusive)."""
    from beancount.core import data as core_data

    categories: dict[str, dict] = {}

    for entry in ledger.entries:
        if not isinstance(entry, core_data.Transaction):
            continue
        if entry.date < start or entry.date >= end_exclusive:
            continue

        for posting in entry.postings:
            account = posting.account
            if not account.startswith(f"{account_prefix}:"):
                continue

            parts = account.split(":")
            if len(parts) < 2:
                continue

            main_category = parts[1]
            subcategory = ":".join(parts[2:]) if len(parts) > 2 else None

            converted = _posting_amount_in_base(ledger, posting)
            if converted is None:
                continue

            flow = _pnl_flow(account, converted)
            if flow == 0:
                continue

            if main_category not in categories:
                categories[main_category] = {
                    "total": Decimal(0),
                    "subcategories": {},
                }

            categories[main_category]["total"] += flow

            if subcategory is not None:
                subs = categories[main_category]["subcategories"]
                if subcategory not in subs:
                    subs[subcategory] = {"total": Decimal(0)}
                subs[subcategory]["total"] += flow

    return {k: v for k, v in categories.items() if v["total"] != 0}


def get_category_breakdown(
    ledger, year: int, month: int, account_prefix: str
) -> dict[str, dict]:
    """Category breakdown for a single calendar month."""
    start, end = month_bounds(year, month)
    return get_category_breakdown_for_range(ledger, start, end, account_prefix)


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
