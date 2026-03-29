"""Overview page: net worth, asset allocation, account breakdown."""

from nicegui import ui
import state
from core.calculations import calculate_net_worth, get_assets_by_category
from components.layout import page_layout
from components.metric_card import metric_card
from components.charts import allocation_pie


@ui.page("/")
def overview_page():
    ledger = state.ledger
    currency = ledger.base_currency

    with page_layout("Overview"):
        net_worth, total_assets, total_liabilities = calculate_net_worth(ledger)
        categories = get_assets_by_category(ledger)

        # Metrics row
        with ui.row().classes("w-full gap-4"):
            metric_card("Net Worth", f"{net_worth:,.0f} {currency}", icon="account_balance")
            metric_card("Total Assets", f"{total_assets:,.0f} {currency}", icon="trending_up")
            metric_card("Total Liabilities", f"{total_liabilities:,.0f} {currency}", icon="trending_down")

        # Assets by category
        ui.label("Assets by Category").classes("text-h5 mt-4")

        sorted_cats = sorted(categories.items(), key=lambda x: x[1]["total"], reverse=True)

        with ui.row().classes("w-full gap-6"):
            # Category table
            with ui.column().classes("flex-grow"):
                rows = []
                for cat, info in sorted_cats:
                    pct = (info["total"] / total_assets * 100) if total_assets > 0 else 0
                    rows.append({
                        "category": cat,
                        "value": f"{info['total']:,.0f} {currency}",
                        "allocation": f"{pct:.1f}%",
                    })

                ui.table(
                    columns=[
                        {"name": "category", "label": "Category", "field": "category", "align": "left"},
                        {"name": "value", "label": "Value", "field": "value", "align": "right"},
                        {"name": "allocation", "label": "Allocation", "field": "allocation", "align": "right"},
                    ],
                    rows=rows,
                ).classes("w-full")

            # Pie chart
            with ui.column().classes("w-96"):
                labels = [cat for cat, _ in sorted_cats]
                values = [float(info["total"]) for _, info in sorted_cats]
                fig = allocation_pie(labels, values)
                ui.plotly(fig).classes("w-full")

        # Detailed account breakdown
        ui.label("Account Details").classes("text-h5 mt-4")

        for cat, info in sorted_cats:
            with ui.expansion(
                f"{cat} — {info['total']:,.0f} {currency}",
            ).classes("w-full"):
                account_rows = []
                for acc in sorted(info["accounts"], key=lambda x: x["value"], reverse=True):
                    account_rows.append({
                        "account": acc["account"],
                        "currency": acc["currency"],
                        "amount": f"{acc['amount']:,.2f}",
                        "value": f"{acc['value']:,.0f} {currency}",
                    })

                ui.table(
                    columns=[
                        {"name": "account", "label": "Account", "field": "account", "align": "left"},
                        {"name": "currency", "label": "Currency", "field": "currency", "align": "center"},
                        {"name": "amount", "label": "Amount", "field": "amount", "align": "right"},
                        {"name": "value", "label": "Value", "field": "value", "align": "right"},
                    ],
                    rows=account_rows,
                ).classes("w-full")
