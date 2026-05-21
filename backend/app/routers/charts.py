from fastapi import APIRouter, Query

from app.deps import state
from app.services.calculations import (
    get_available_months,
    get_category_breakdown,
    get_monthly_income_expenses,
)

router = APIRouter(prefix="/api/charts", tags=["charts"])


@router.get("/months")
def months():
    ledger = state.require_ledger()
    return {"months": [{"year": y, "month": m} for y, m in get_available_months(ledger)]}


@router.get("/income-expenses")
def income_expenses(year: int = Query(...), month: int = Query(...)):
    ledger = state.require_ledger()
    income, expenses = get_monthly_income_expenses(ledger, year, month)
    return {
        "year": year,
        "month": month,
        "currency": ledger.base_currency,
        "income": float(income),
        "expenses": float(expenses),
    }


@router.get("/breakdown")
def breakdown(
    year: int = Query(...),
    month: int = Query(...),
    kind: str = Query("expenses", pattern="^(expenses|income)$"),
):
    ledger = state.require_ledger()
    prefix = "Expenses" if kind == "expenses" else "Income"
    data = get_category_breakdown(ledger, year, month, prefix)

    categories = []
    for name, info in sorted(data.items(), key=lambda x: x[1]["total"], reverse=True):
        subcats = [
            {"name": s, "total": float(info["subcategories"][s]["total"])}
            for s in info["subcategories"]
        ]
        categories.append({
            "name": name,
            "total": float(info["total"]),
            "subcategories": subcats,
        })

    return {
        "year": year,
        "month": month,
        "kind": kind,
        "currency": ledger.base_currency,
        "categories": categories,
    }
