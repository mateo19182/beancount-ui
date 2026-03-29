"""Crypto page: cryptocurrency holdings and allocation."""

from nicegui import ui
import state
from core.calculations import get_crypto_positions
from components.layout import page_layout
from components.metric_card import metric_card
from components.charts import allocation_bar


@ui.page("/crypto")
def crypto_page():
    ledger = state.ledger
    currency = ledger.base_currency

    with page_layout("Crypto Holdings"):
        positions = get_crypto_positions(ledger)

        if not positions:
            ui.label("No crypto positions found.").classes("text-gray-500")
            return

        total_value = sum(p["value"] for p in positions if p["value"])

        # Metrics
        with ui.row().classes("w-full gap-4"):
            metric_card("Total Crypto Value", f"{total_value:,.0f} {currency}", icon="currency_bitcoin")
            metric_card("Assets", str(len(positions)), icon="token")

        # Holdings table
        ui.label("Holdings").classes("text-h5 mt-4")

        rows = []
        for p in positions:
            pct = (p["value"] / total_value * 100) if p["value"] and total_value else 0
            rows.append({
                "symbol": p["symbol"],
                "amount": f"{p['amount']:,.4f}",
                "price": f"{p['price']:,.2f} {currency}" if p["price"] else "N/A",
                "value": f"{p['value']:,.0f} {currency}" if p["value"] else "N/A",
                "allocation": f"{pct:.1f}%",
            })

        ui.table(
            columns=[
                {"name": "symbol", "label": "Symbol", "field": "symbol", "align": "left"},
                {"name": "amount", "label": "Amount", "field": "amount", "align": "right"},
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
            symbols, values, color="#FF6B35",
            title="Crypto Allocation", y_label=f"Value ({currency})",
        )
        ui.plotly(fig).classes("w-full mt-4")
