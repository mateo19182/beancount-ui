"""Alternative price fetcher using yfinance to bypass Yahoo Finance blocks."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import subprocess


def extract_commodities_from_ledger(ledger_path: Path) -> list[tuple[str, str]]:
    """Extract commodities with price sources from ledger.

    Returns list of (commodity, yahoo_symbol) tuples.
    """
    commodities = []

    # Read the main ledger file to find included files
    includes = []
    try:
        with open(ledger_path) as f:
            for line in f:
                if line.strip().startswith("include "):
                    include_path = line.split("include ")[1].strip().strip('"')
                    includes.append(include_path)
    except Exception:
        pass

    # Search for commodity declarations in main file and includes
    commodities_file = ledger_path.parent / "commodities.beancount"
    if commodities_file.exists():
        try:
            with open(commodities_file) as f:
                content = f.read()

            # Parse commodity declarations
            # Match format: YYYY-MM-DD commodity SYMBOL\n  price: "CURRENCY:yahoo/YAHOO_SYMBOL"
            commodity_pattern = r'(\d{4}-\d{2}-\d{2}) commodity (\w+).*?\n\s+price: "(\w+):yahoo/([^"]+)"'
            matches = re.findall(commodity_pattern, content, re.DOTALL)

            for _, commodity, currency, symbol in matches:
                commodities.append((commodity, symbol))

        except Exception:
            pass

    return commodities


def fetch_price_with_yfinance(symbol: str) -> Optional[float]:
    """Fetch current price using yfinance library."""
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        # Get the most recent close price
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None
    except Exception:
        return None


def fetch_prices_alternative(ledger_path: Path) -> tuple[bool, str, Optional[str]]:
    """Fetch prices using yfinance as an alternative to bean-price.

    Returns:
        Tuple of (success, message, prices_content)
    """
    commodities = extract_commodities_from_ledger(ledger_path)

    if not commodities:
        return False, "No commodities with price sources found", None

    # Check if yfinance is available
    try:
        import yfinance as yf  # noqa: F401
    except ImportError:
        return (
            False,
            "yfinance not installed. Run: uv add yfinance",
            None,
        )

    prices_lines = []
    today = datetime.now().strftime("%Y-%m-%d")
    fetched_count = 0
    failed_symbols = []

    for commodity, symbol in commodities:
        price = fetch_price_with_yfinance(symbol)

        if price:
            # Determine currency from symbol
            if symbol.endswith("-USD") or symbol.endswith("=X"):
                currency = "USD"
            elif symbol.endswith("-EUR"):
                currency = "EUR"
            else:
                currency = "USD"

            prices_lines.append(
                f"{today} price {commodity:15} {price:15.8f} {currency}"
            )
            fetched_count += 1
        else:
            failed_symbols.append(symbol)

    if prices_lines:
        prices_content = "\n".join(prices_lines)
        message = f"Fetched {fetched_count} prices"
        if failed_symbols:
            message += f" ({len(failed_symbols)} failed: {', '.join(failed_symbols)})"
        return True, message, prices_content
    else:
        return (
            False,
            f"Failed to fetch any prices. Failed symbols: {', '.join(failed_symbols)}",
            None,
        )


def update_prices_with_yfinance(ledger_path: Path) -> tuple[bool, str]:
    """Update prices using yfinance as fallback.

    Returns:
        Tuple of (success, message)
    """
    from app.services.price_fetcher import (
        get_prices_file_path,
        append_prices_to_file,
        validate_ledger,
    )

    success, message, prices_content = fetch_prices_alternative(ledger_path)

    if not success or not prices_content:
        return False, message

    prices_file = get_prices_file_path(ledger_path)

    # Append to prices file
    write_success, write_message = append_prices_to_file(
        prices_file, prices_content, backup=True
    )

    if not write_success:
        return False, write_message

    # Validate ledger (but don't fail if prices were successfully saved)
    valid, validation_msg = validate_ledger(ledger_path)

    if valid:
        return True, f"{message}. {write_message}. {validation_msg}"
    else:
        # Still return success since prices were updated, but warn about validation
        return True, f"{message}. {write_message}. Warning: {validation_msg}"
