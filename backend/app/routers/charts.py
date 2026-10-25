from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.deps import state
from app.services.calculations import (
    get_available_months,
    get_category_breakdown_for_range,
    get_income_expenses_for_range,
    get_monthly_income_expenses_series,
    inclusive_range_bounds,
)

router = APIRouter(prefix="/api/charts", tags=["charts"])


def _parse_range(from_date: date, to_date: date) -> tuple[date, date]:
    if to_date < from_date:
        raise HTTPException(400, "to must be on or after from")
    return inclusive_range_bounds(from_date, to_date)


@router.get("/months")
def months():
    ledger = state.require_ledger()
    return {"months": [{"year": y, "month": m} for y, m in get_available_months(ledger)]}


@router.get("/income-expenses")
def income_expenses(
    date_from: date = Query(...),
    date_to: date = Query(...),
):
    ledger = state.require_ledger()
    start, end = _parse_range(date_from, date_to)
    income, expenses = get_income_expenses_for_range(ledger, start, end)
    return {
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
        "currency": ledger.base_currency,
        "income": float(income),
        "expenses": float(expenses),
    }


@router.get("/trend")
def trend(
    date_from: date = Query(...),
    date_to: date = Query(...),
):
    ledger = state.require_ledger()
    start, end = _parse_range(date_from, date_to)
    rows = get_monthly_income_expenses_series(ledger, start, end)
    return {
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
        "currency": ledger.base_currency,
        "months": [
            {
                "year": r["year"],
                "month": r["month"],
                "income": float(r["income"]),
                "expenses": float(r["expenses"]),
            }
            for r in rows
        ],
    }


@router.get("/breakdown")
def breakdown(
    date_from: date = Query(...),
    date_to: date = Query(...),
    kind: str = Query("expenses", pattern="^(expenses|income)$"),
):
    ledger = state.require_ledger()
    start, end = _parse_range(date_from, date_to)
    prefix = "Expenses" if kind == "expenses" else "Income"
    data = get_category_breakdown_for_range(ledger, start, end, prefix)

    categories = []
    for name, info in sorted(data.items(), key=lambda x: x[1]["total"], reverse=True):
        subcats = [
            {
                "name": s,
                "total": float(info["subcategories"][s]["total"]),
                "account": f"{prefix}:{name}:{s}",
            }
            for s in sorted(
                info["subcategories"],
                key=lambda s: info["subcategories"][s]["total"],
                reverse=True,
            )
        ]
        categories.append({
            "name": name,
            "total": float(info["total"]),
            "account": f"{prefix}:{name}",
            "subcategories": subcats,
        })

    return {
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
        "kind": kind,
        "currency": ledger.base_currency,
        "categories": categories,
    }
