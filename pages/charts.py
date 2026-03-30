"""Charts page: income and expense breakdown with category drill-down."""

from nicegui import ui
from datetime import date
import state
from core.calculations import (
    get_monthly_income_expenses,
    get_category_breakdown,
    get_available_months,
)
from components.layout import page_layout
from components.metric_card import metric_card
from components.charts import income_pie, expense_pie, category_bar


@ui.page("/charts")
def charts_page():
    ledger = state.ledger
    currency = ledger.base_currency

    # Get available months and set default to current month
    available_months = get_available_months(ledger)
    current_year = date.today().year
    current_month = date.today().month

    # Use a list to hold mutable state (year, month)
    selected_year_month = [(current_year, current_month)]

    # Check if current month has data, otherwise use most recent
    if available_months:
        if (current_year, current_month) not in available_months:
            # Use most recent month with data
            selected_year_month[0] = available_months[-1]

    # Chart type preference: "pie" or "bar"
    chart_type_income = ["pie"]
    chart_type_expense = ["pie"]

    def refresh_charts():
        """Refresh the income and expenses section based on selected month."""
        year, month = selected_year_month[0]

        # Clear and rebuild the charts container
        charts_container.clear()

        with charts_container:
            total_income, total_expenses = get_monthly_income_expenses(
                ledger, year, month
            )
            net_flow = total_income - total_expenses

            # Monthly summary metrics
            ui.label(f"Income & Expenses — {year}-{month:02d}").classes("text-h5 mt-4")

            with ui.row().classes("w-full gap-4 mb-4"):
                metric_card(
                    "Income",
                    f"{total_income:,.0f} {currency}",
                    icon="trending_up",
                    color_class="text-green-600",
                )
                metric_card(
                    "Expenses",
                    f"{total_expenses:,.0f} {currency}",
                    icon="trending_down",
                    color_class="text-red-600",
                )
                metric_card(
                    "Net Flow",
                    f"{net_flow:,.0f} {currency}",
                    icon="account_balance_wallet",
                )

            # Side-by-side layout for income and expenses
            with ui.row().classes("w-full gap-6"):
                # Income column
                with ui.column().classes("flex-grow"):
                    ui.label("Income by Source").classes("text-h6 mt-2")

                    income_categories = get_category_breakdown(
                        ledger, year, month, "Income"
                    )

                    if income_categories:
                        sorted_income = sorted(
                            income_categories.items(),
                            key=lambda x: x[1]["total"],
                            reverse=True,
                        )

                        # Chart type toggle
                        with ui.row().classes("w-full gap-2 items-center mb-4"):
                            ui.label("Chart:").classes("text-caption")
                            ui.toggle(
                                {"pie": "Pie Chart", "bar": "Bar Chart"},
                                value=chart_type_income[0],
                                on_change=lambda e: (
                                    chart_type_income.__setitem__(0, e.value),
                                    refresh_charts(),
                                )[0],
                            ).props("dense").classes("compact-toggle")

                        # Income chart (pie or bar)
                        labels = [cat for cat, _ in sorted_income]
                        values = [float(info["total"]) for _, info in sorted_income]

                        def make_income_chart_handler(labels, sorted_income):
                            def handle_chart_click(e):
                                if e.args and "points" in e.args[0] and len(e.args[0]["points"]) > 0:
                                    point = e.args[0]["points"][0]
                                    clicked_label = point.get("label", "")
                                    if clicked_label:
                                        # Find the account prefix for this label
                                        for cat, info in sorted_income:
                                            if cat == clicked_label:
                                                navigate_to_transactions({"account_prefix": f"Income:{cat}"})
                                                break
                            return handle_chart_click

                        if chart_type_income[0] == "pie":
                            fig = income_pie(labels, values)
                            chart_plot = ui.plotly(fig).classes("w-full mb-4")
                            chart_plot.on("plotly_click", make_income_chart_handler(labels, sorted_income))
                        else:
                            fig_bar = category_bar(
                                labels=labels,
                                values=values,
                                color="#10b981",
                                title="",
                                y_label=f"Amount ({currency})",
                            )
                            chart_plot = ui.plotly(fig_bar).classes("w-full mb-4")
                            chart_plot.on("plotly_click", make_income_chart_handler(labels, sorted_income))

                        # Income category table with clickable rows
                        income_rows = []
                        for cat, info in sorted_income:
                            pct = (
                                (info["total"] / total_income * 100)
                                if total_income > 0
                                else 0
                            )
                            # Main category row - clickable
                            income_rows.append(
                                {
                                    "category": cat,
                                    "amount": f"{info['total']:,.0f} {currency}",
                                    "percentage": f"{pct:.1f}%",
                                    "indent": 0,
                                    "is_subcategory": False,
                                    "account_prefix": f"Income:{cat}",
                                }
                            )
                            # Subcategory rows - clickable
                            if info.get("subcategories"):
                                sorted_subcats = sorted(
                                    info["subcategories"].items(),
                                    key=lambda x: x[1]["total"],
                                    reverse=True,
                                )
                                for subcat, subinfo in sorted_subcats:
                                    sub_pct = (
                                        (subinfo["total"] / total_income * 100)
                                        if total_income > 0
                                        else 0
                                    )
                                    income_rows.append(
                                        {
                                            "category": f"  └─ {subcat}",
                                            "amount": f"{subinfo['total']:,.0f} {currency}",
                                            "percentage": f"{sub_pct:.1f}%",
                                            "indent": 1,
                                            "is_subcategory": True,
                                            "account_prefix": f"Income:{cat}:{subcat}",
                                        }
                                    )

                        def navigate_to_transactions(row):
                            """Navigate to transactions page with search pre-filled."""
                            year, month = selected_year_month[0]
                            account_prefix = row.get("account_prefix", "")
                            # Navigate to transactions with search parameter
                            from urllib.parse import quote

                            search_encoded = quote(account_prefix, safe="")
                            query = f"?month={year}-{month:02d}&search={search_encoded}"
                            ui.navigate.to(f"/transactions{query}")

                        table = ui.table(
                            columns=[
                                {
                                    "name": "category",
                                    "label": "Category",
                                    "field": "category",
                                    "align": "left",
                                },
                                {
                                    "name": "amount",
                                    "label": "Amount",
                                    "field": "amount",
                                    "align": "right",
                                },
                                {
                                    "name": "percentage",
                                    "label": "%",
                                    "field": "percentage",
                                    "align": "right",
                                },
                            ],
                            rows=income_rows,
                            row_key="category",
                        ).classes("w-full clickable-rows")
                        table.on(
                            "row-click", lambda e: navigate_to_transactions(e.args[0])
                        )
                    else:
                        ui.label("No income recorded for this month").classes(
                            "text-grey"
                        )

                # Expenses column
                with ui.column().classes("flex-grow"):
                    ui.label("Expenses by Category").classes("text-h6 mt-2")

                    expense_categories = get_category_breakdown(
                        ledger, year, month, "Expenses"
                    )

                    if expense_categories:
                        sorted_expenses = sorted(
                            expense_categories.items(),
                            key=lambda x: x[1]["total"],
                            reverse=True,
                        )

                        # Chart type toggle
                        with ui.row().classes("w-full gap-2 items-center mb-4"):
                            ui.label("Chart:").classes("text-caption")
                            ui.toggle(
                                {"pie": "Pie Chart", "bar": "Bar Chart"},
                                value=chart_type_expense[0],
                                on_change=lambda e: (
                                    chart_type_expense.__setitem__(0, e.value),
                                    refresh_charts(),
                                )[0],
                            ).props("dense").classes("compact-toggle")

                        # Expense chart (pie or bar)
                        labels = [cat for cat, _ in sorted_expenses]
                        values = [float(info["total"]) for _, info in sorted_expenses]

                        def make_expense_chart_handler(labels, sorted_expenses):
                            def handle_chart_click(e):
                                if e.args and "points" in e.args[0] and len(e.args[0]["points"]) > 0:
                                    point = e.args[0]["points"][0]
                                    clicked_label = point.get("label", "")
                                    if clicked_label:
                                        # Find the account prefix for this label
                                        for cat, info in sorted_expenses:
                                            if cat == clicked_label:
                                                navigate_to_expense_transactions({"account_prefix": f"Expenses:{cat}"})
                                                break
                            return handle_chart_click

                        if chart_type_expense[0] == "pie":
                            fig = expense_pie(labels, values)
                            chart_plot = ui.plotly(fig).classes("w-full mb-4")
                            chart_plot.on("plotly_click", make_expense_chart_handler(labels, sorted_expenses))
                        else:
                            fig_bar = category_bar(
                                labels=labels,
                                values=values,
                                color="#ef4444",
                                title="",
                                y_label=f"Amount ({currency})",
                            )
                            chart_plot = ui.plotly(fig_bar).classes("w-full mb-4")
                            chart_plot.on("plotly_click", make_expense_chart_handler(labels, sorted_expenses))

                        # Expense category table with clickable rows
                        expense_rows = []
                        for cat, info in sorted_expenses:
                            pct = (
                                (info["total"] / total_expenses * 100)
                                if total_expenses > 0
                                else 0
                            )
                            # Main category row - clickable
                            expense_rows.append(
                                {
                                    "category": cat,
                                    "amount": f"{info['total']:,.0f} {currency}",
                                    "percentage": f"{pct:.1f}%",
                                    "indent": 0,
                                    "is_subcategory": False,
                                    "account_prefix": f"Expenses:{cat}",
                                }
                            )
                            # Subcategory rows - clickable
                            if info.get("subcategories"):
                                sorted_subcats = sorted(
                                    info["subcategories"].items(),
                                    key=lambda x: x[1]["total"],
                                    reverse=True,
                                )
                                for subcat, subinfo in sorted_subcats:
                                    sub_pct = (
                                        (subinfo["total"] / total_expenses * 100)
                                        if total_expenses > 0
                                        else 0
                                    )
                                    expense_rows.append(
                                        {
                                            "category": f"  └─ {subcat}",
                                            "amount": f"{subinfo['total']:,.0f} {currency}",
                                            "percentage": f"{sub_pct:.1f}%",
                                            "indent": 1,
                                            "is_subcategory": True,
                                            "account_prefix": f"Expenses:{cat}:{subcat}",
                                        }
                                    )

                        def navigate_to_expense_transactions(row):
                            """Navigate to transactions page with search pre-filled."""
                            year, month = selected_year_month[0]
                            account_prefix = row.get("account_prefix", "")
                            # Navigate to transactions with search parameter
                            from urllib.parse import quote

                            search_encoded = quote(account_prefix, safe="")
                            query = f"?month={year}-{month:02d}&search={search_encoded}"
                            ui.navigate.to(f"/transactions{query}")

                        table = ui.table(
                            columns=[
                                {
                                    "name": "category",
                                    "label": "Category",
                                    "field": "category",
                                    "align": "left",
                                },
                                {
                                    "name": "amount",
                                    "label": "Amount",
                                    "field": "amount",
                                    "align": "right",
                                },
                                {
                                    "name": "percentage",
                                    "label": "%",
                                    "field": "percentage",
                                    "align": "right",
                                },
                            ],
                            rows=expense_rows,
                            row_key="category",
                        ).classes("w-full clickable-rows")
                        table.on(
                            "row-click",
                            lambda e: navigate_to_expense_transactions(e.args[0]),
                        )
                    else:
                        ui.label("No expenses recorded for this month").classes(
                            "text-grey"
                        )

    with page_layout("Charts"):
        # Month selector
        with ui.row().classes("w-full gap-2 items-center mb-4"):
            ui.label("Select Month:").classes("text-body1")

            # Previous month button
            def go_to_prev_month():
                year, month = selected_year_month[0]
                # Find previous available month
                current_idx = available_months.index((year, month))
                if current_idx > 0:
                    selected_year_month[0] = available_months[current_idx - 1]
                    refresh_charts()

            ui.button(icon="chevron_left", on_click=go_to_prev_month).props(
                "flat round"
            ).classes("mx-1")

            # Month dropdown
            month_options = {f"{y}-{m:02d}": (y, m) for y, m in available_months}
            month_selector = ui.select(
                options=list(month_options.keys()),
                value=f"{selected_year_month[0][0]}-{selected_year_month[0][1]:02d}",
                on_change=lambda e: (
                    selected_year_month.__setitem__(
                        0, month_options.get(e.value, selected_year_month[0])
                    ),
                    refresh_charts(),
                )[0],
            ).classes("w-32")

            # Next month button
            def go_to_next_month():
                year, month = selected_year_month[0]
                # Find next available month
                current_idx = available_months.index((year, month))
                if current_idx < len(available_months) - 1:
                    selected_year_month[0] = available_months[current_idx + 1]
                    refresh_charts()

            ui.button(icon="chevron_right", on_click=go_to_next_month).props(
                "flat round"
            ).classes("mx-1")

        # Container for charts section
        charts_container = ui.column().classes("w-full")
        refresh_charts()
