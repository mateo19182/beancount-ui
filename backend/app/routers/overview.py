from decimal import Decimal
from fastapi import APIRouter

from app.deps import state
from app.services.calculations import calculate_net_worth, get_assets_by_category

router = APIRouter(prefix="/api/overview", tags=["overview"])


def _dec(v: Decimal) -> float:
    return float(v)


@router.get("")
def overview():
    ledger = state.require_ledger()
    net_worth, total_assets, total_liabilities = calculate_net_worth(ledger)
    categories = get_assets_by_category(ledger)
    currency = ledger.base_currency

    cats = []
    for name, info in sorted(categories.items(), key=lambda x: x[1]["total"], reverse=True):
        pct = (info["total"] / total_assets * 100) if total_assets > 0 else Decimal(0)
        cats.append({
            "category": name,
            "total": _dec(info["total"]),
            "allocation_pct": float(pct),
            "accounts": [
                {
                    "account": a["account"],
                    "currency": a["currency"],
                    "amount": float(a["amount"]),
                    "value": float(a["value"]),
                }
                for a in info["accounts"]
            ],
        })

    return {
        "currency": currency,
        "net_worth": _dec(net_worth),
        "total_assets": _dec(total_assets),
        "total_liabilities": _dec(total_liabilities),
        "categories": cats,
    }
