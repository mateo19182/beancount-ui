"""Investments page: stock portfolio holdings and allocation."""

from nicegui import ui
import state
from core.calculations import get_stock_positions
from components.layout import page_layout
from components.metric_card import metric_card
from components.charts import allocation_bar


@ui.page("/investments")
def investments_page():
    ledger = state.ledger
    currency = ledger.base_currency

    with page_layout("Stock Portfolio"):
        positions = get_stock_positions(ledger)

        if not positions:
            ui.label("No stock positions found.").classes("text-gray-500")
            return

        total_value = sum(p["value"] for p in positions if p["value"])

        # Metrics
        with ui.row().classes("w-full gap-4"):
            metric_card("Portfolio Value", f"{total_value:,.0f} {currency}", icon="show_chart")
            metric_card("Holdings", str(len(positions)), icon="inventory_2")

        # Holdings table
        ui.label("Holdings").classes("text-h5 mt-4")

        rows = []
        for p in positions:
            pct = (p["value"] / total_value * 100) if p["value"] and total_value else 0
            rows.append({
                "symbol": p["symbol"],
                "shares": f"{p['shares']:,.2f}",
                "price": f"{p['price']:,.2f} {currency}" if p["price"] else "N/A",
                "value": f"{p['value']:,.0f} {currency}" if p["value"] else "N/A",
                "allocation": f"{pct:.1f}%",
            })

        ui.table(
            columns=[
                {"name": "symbol", "label": "Symbol", "field": "symbol", "align": "left"},
                {"name": "shares", "label": "Shares", "field": "shares", "align": "right"},
                {"name": "price", "label": "Price", "field": "price", "align": "right"},
                {"name": "value", "label": "Value", "field": "value", "align": "right"},
                {"name": "allocation", "label": "Allocation", "field": "allocation", "align": "right"},
            ],
            rows=rows,
        ).classes("w-full")

        # Bar chart
        symbols = [p["symbol"] for p in positions if p["value"]]
        values = [p["value"] for p in positions if p["value"]]
        fig = allocation_bar(
            symbols, values, color="steelblue",
            title="Portfolio Allocation", y_label=f"Value ({currency})",
        )
        ui.plotly(fig).classes("w-full mt-4")
