"""Load and hold a beancount ledger in memory."""

from pathlib import Path
from datetime import date
from decimal import Decimal
from beancount import loader
from beancount.core import data, prices, realization


class Ledger:
    """Loads a beancount ledger and provides access to its data.

    Single instance per app. Call reload() after writing transactions.
    """

    def __init__(self, ledger_path: Path):
        self.ledger_path = ledger_path
        self.entries: list = []
        self.errors: list = []
        self.options_map: dict = {}
        self.price_map = None
        self._accounts: list[str] | None = None
        self._currencies: set[str] | None = None
        self._realized = None
        self.load()

    def load(self):
        self.entries, self.errors, self.options_map = loader.load_file(
            str(self.ledger_path)
        )
        self.price_map = prices.build_price_map(self.entries)
        self._accounts = None
        self._currencies = None
        self._realized = None

    def reload(self):
        self.load()

    @property
    def base_currency(self) -> str:
        """First operating currency from beancount options."""
        currencies = self.options_map.get("operating_currency", [])
        return currencies[0] if currencies else "USD"

    @property
    def operating_currencies(self) -> list[str]:
        return self.options_map.get("operating_currency", ["USD"])

    @property
    def accounts(self) -> list[str]:
        if self._accounts is None:
            self._accounts = sorted(
                entry.account
                for entry in self.entries
                if isinstance(entry, data.Open)
            )
        return self._accounts

    @property
    def currencies(self) -> set[str]:
        if self._currencies is None:
            self._currencies = set()
            for entry in self.entries:
                if isinstance(entry, data.Commodity):
                    self._currencies.add(entry.currency)
            self._currencies.update(self.operating_currencies)
        return self._currencies

    def realize(self):
        """Return realized account tree. Cached until reload()."""
        if self._realized is None:
            self._realized = realization.realize(self.entries)
        return self._realized

    def get_account_balances(self, node, account_path: str = "") -> list[dict]:
        """Recursively extract balances from a realized account tree node."""
        balances = []

        if hasattr(node, "balance") and not node.balance.is_empty():
            for key, position in node.balance.items():
                currency = key[0] if isinstance(key, tuple) else key
                amount = position.units.number
                if amount != 0:
                    balances.append({
                        "account": account_path,
                        "currency": currency,
                        "amount": amount,
                    })

        if hasattr(node, "keys"):
            for key in node.keys():
                child_path = f"{account_path}:{key}" if account_path else key
                balances.extend(self.get_account_balances(node[key], child_path))

        return balances

    def get_assets(self) -> list[dict]:
        real_root = self.realize()
        if "Assets" not in real_root:
            return []
        return self.get_account_balances(real_root["Assets"], "Assets")

    def get_liabilities(self) -> list[dict]:
        real_root = self.realize()
        if "Liabilities" not in real_root:
            return []
        return self.get_account_balances(real_root["Liabilities"], "Liabilities")

    def convert_to_currency(
        self, amount: Decimal, from_currency: str, target: str | None = None
    ) -> Decimal | None:
        """Convert an amount to the target currency (defaults to base_currency)."""
        target = target or self.base_currency
        if from_currency == target:
            return amount
        return self._convert(amount, from_currency, target, set())

    def _convert(
        self, amount: Decimal, from_currency: str, target: str, tried: set
    ) -> Decimal | None:
        if from_currency == target:
            return amount

        pair = (from_currency, target)
        if pair in tried:
            return None
        tried = tried | {pair}

        today = date.today()

        # Direct conversion
        rate = prices.get_price(self.price_map, (from_currency, target), today)
        if rate and rate[1] is not None:
            return amount * rate[1]

        # Reverse conversion
        rate = prices.get_price(self.price_map, (target, from_currency), today)
        if rate and rate[1] is not None:
            return amount / rate[1]

        # Two-hop via common intermediaries
        for via in ("USD", "EUR"):
            if via == from_currency or via == target:
                continue
            mid = self._convert(amount, from_currency, via, tried)
            if mid is not None:
                result = self._convert(mid, via, target, tried)
                if result is not None:
                    return result

        return None

    def is_fiat_currency(self, commodity: str) -> bool:
        """Check if a commodity is a fiat currency (not an investment)."""
        common_fiat = {"USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD", "NZD",
                       "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "RON", "BGN",
                       "HRK", "ISK", "TRY", "RUB", "CNY", "INR", "BRL", "MXN",
                       "KRW", "SGD", "HKD", "TWD", "THB", "MYR", "PHP", "IDR",
                       "ZAR", "ARS", "CLP", "COP", "PEN", "VND"}
        return commodity in common_fiat
