"""Fetch and update commodity prices using bean-price."""

import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class PriceFetchResult:
    """Result of a price fetch operation."""

    success: bool
    prices_fetched: int
    message: str
    prices_content: Optional[str] = None


def get_prices_file_path(ledger_path: Path) -> Path:
    """Get the path to the prices file based on ledger location."""
    return ledger_path.parent / "prices" / "prices.beancount"


def backup_prices_file(prices_file: Path) -> Optional[Path]:
    """Backup the current prices file before updating."""
    if not prices_file.exists():
        return None

    backup_dir = prices_file.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"prices_{timestamp}.beancount"

    shutil.copy2(prices_file, backup_file)
    return backup_file


def fetch_prices_with_bean_price(ledger_path: Path) -> PriceFetchResult:
    """Fetch prices using bean-price command."""
    if not ledger_path.exists():
        return PriceFetchResult(
            success=False,
            prices_fetched=0,
            message=f"Ledger file not found: {ledger_path}",
        )

    try:
        result = subprocess.run(
            ["uv", "run", "bean-price", "--no-cache", "--clobber", str(ledger_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        prices_output = result.stdout.strip()
        stderr_output = result.stderr.strip()

        # Check for errors in stderr
        if (
            result.returncode != 0
            or "Error" in stderr_output
            or "Exception" in stderr_output
        ):
            error_msg = (
                stderr_output if stderr_output else f"Exit code: {result.returncode}"
            )
            return PriceFetchResult(
                success=False,
                prices_fetched=0,
                message=f"Price fetch failed: {error_msg[:200]}",
            )

        if prices_output:
            prices_fetched = len(
                [
                    line
                    for line in prices_output.split("\n")
                    if line.strip() and line[0].isdigit()
                ]
            )

            return PriceFetchResult(
                success=True,
                prices_fetched=prices_fetched,
                message=f"Fetched {prices_fetched} price entries",
                prices_content=prices_output,
            )
        else:
            return PriceFetchResult(
                success=True,
                prices_fetched=0,
                message="No new prices to fetch (price sources may be unavailable)",
            )

    except subprocess.TimeoutExpired:
        return PriceFetchResult(
            success=False,
            prices_fetched=0,
            message="Price fetch timed out after 2 minutes",
        )
    except FileNotFoundError:
        return PriceFetchResult(
            success=False,
            prices_fetched=0,
            message="bean-price command not found",
        )
    except Exception as e:
        return PriceFetchResult(
            success=False,
            prices_fetched=0,
            message=f"Unexpected error: {str(e)}",
        )


def append_prices_to_file(
    prices_file: Path, prices_content: str, backup: bool = True
) -> tuple[bool, str]:
    """Append fetched prices to the prices file."""
    try:
        prices_file.parent.mkdir(parents=True, exist_ok=True)

        if backup and prices_file.exists():
            backup_path = backup_prices_file(prices_file)
            if backup_path:
                print(f"Backed up prices to {backup_path}")

        with open(prices_file, "a") as f:
            timestamp = datetime.now().strftime(
                "\n; Prices updated: %Y-%m-%d %H:%M:%S\n"
            )
            f.write(timestamp)
            f.write(prices_content)
            if not prices_content.endswith("\n"):
                f.write("\n")

        return True, f"Prices saved to {prices_file.name}"

    except Exception as e:
        return False, f"Failed to write prices: {str(e)}"


def validate_ledger(ledger_path: Path) -> tuple[bool, str]:
    """Validate the ledger after price update using bean-check."""
    try:
        result = subprocess.run(
            ["uv", "run", "bean-check", str(ledger_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return True, "Ledger valid"
        else:
            error_msg = (
                result.stderr.strip() if result.stderr else "Unknown validation error"
            )
            return False, f"Validation failed: {error_msg}"

    except FileNotFoundError:
        return False, "bean-check command not found"
    except subprocess.TimeoutExpired:
        return False, "Ledger validation timed out"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def update_prices(ledger_path: Path) -> tuple[bool, str]:
    """Main function to fetch and update prices.

    Returns:
        Tuple of (success, message)
    """
    prices_file = get_prices_file_path(ledger_path)

    fetch_result = fetch_prices_with_bean_price(ledger_path)

    if not fetch_result.success:
        return False, f"Failed to fetch: {fetch_result.message}"

    if fetch_result.prices_content:
        success, message = append_prices_to_file(
            prices_file, fetch_result.prices_content, backup=True
        )

        if not success:
            return False, message

        valid, validation_msg = validate_ledger(ledger_path)

        if valid:
            return True, f"{fetch_result.message}. {message}. {validation_msg}"
        else:
            return False, f"{fetch_result.message}. {message}. {validation_msg}"
    else:
        return True, fetch_result.message
