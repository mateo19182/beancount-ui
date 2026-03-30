"""Transactions page: browse, filter, search, edit, and attach documents."""

from datetime import date, timedelta
from nicegui import ui
import state
from core.analytics import get_all_transactions
from core.transaction_writer import (
    edit_transaction,
    delete_transaction,
    verify_ledger,
    find_transaction_file,
    add_document_to_transaction,
)
from core.document_handler import save_document
from components.layout import page_layout
from components.date_input import date_input


def _parse_query_params():
    """Parse query parameters from current URL."""
    try:
        return ui.context.client.page.query
    except:
        return {}


@ui.page("/transactions")
def transactions_page():
    ledger = state.ledger
    transactions, all_accounts = get_all_transactions(ledger.entries)
    currency = ledger.base_currency

    # Parse query parameters
    query_params = _parse_query_params()

    # Extract filter values from query
    month_param = query_params.get("month", "")
    search_param = query_params.get("search", "")

    with page_layout("Transactions"):
        # --- Filters ---
        with ui.expansion("Filters", icon="filter_list").classes("w-full"):
            with ui.row().classes("w-full gap-4 flex-wrap"):
                # Set default date range based on query param
                if month_param:
                    try:
                        year, month = month_param.split("-")
                        year, month = int(year), int(month)
                        start = date(year, month, 1)
                        if month == 12:
                            end = date(year + 1, 1, 1) - timedelta(days=1)
                        else:
                            end = date(year, month + 1, 1) - timedelta(days=1)
                    except:
                        end = date.today()
                        start = end - timedelta(days=365)
                else:
                    end = date.today()
                    start = end - timedelta(days=365)

                date_from = date_input("From", start.isoformat())
                date_to = date_input("To", end.isoformat())

                def _render_on_change():
                    render_transactions()

                search_input = (
                    ui.input(label="Search", placeholder="payee, narration, account...", value=search_param, on_change=_render_on_change)
                    .props("outlined dense")
                    .classes("w-64")
                )

        # --- Transaction list container ---
        results_container = ui.column().classes("w-full gap-0")

        def render_transactions():
            results_container.clear()

            d_from = date.fromisoformat(date_from.value) if date_from.value else start
            d_to = date.fromisoformat(date_to.value) if date_to.value else end
            search = (search_input.value or "").lower()

            filtered = []
            for tx in transactions:
                if not (d_from <= tx["date"] <= d_to):
                    continue
                if search:
                    haystack = f"{tx['payee']} {tx['narration']} {' '.join(tx['accounts'])}".lower()
                    if search not in haystack:
                        continue
                filtered.append(tx)

            with results_container:
                ui.label(f"{len(filtered)} transactions").classes(
                    "text-sm text-gray-500 mb-2"
                )

                if not filtered:
                    ui.label("No transactions match your filters.").classes(
                        "text-gray-400 py-8"
                    )
                    return

                for tx in filtered:
                    doc_icon = " 📎" if tx["has_document"] else ""
                    header = f"{tx['date']}  |  {tx['payee'][:40]}  |  {tx['amount_str']}{doc_icon}"

                    with ui.expansion(header).classes("w-full"):
                        with ui.row().classes("w-full gap-8"):
                            with ui.column().classes("flex-grow"):
                                ui.label(f"Date: {tx['date']}").classes("text-sm")
                                ui.label(f"Payee: {tx['payee']}").classes("text-sm")
                                ui.label(f"Narration: {tx['narration']}").classes(
                                    "text-sm"
                                )

                            with ui.column().classes("flex-grow"):
                                for i, acc in enumerate(tx["accounts"]):
                                    if i < len(tx["posting_amounts"]):
                                        p = tx["posting_amounts"][i]
                                        ui.label(
                                            f"{acc}: {p['direction']}{p['amount']:,.2f} {p['currency']}"
                                        ).classes("text-sm")
                                    else:
                                        ui.label(acc).classes("text-sm")

                                if tx["has_document"]:
                                    ui.label(
                                        f"Document: {tx['document_path']}"
                                    ).classes("text-xs text-gray-400")

                            with ui.column().classes("gap-1"):
                                _edit_button(tx, ledger)
                                if not tx["has_document"]:
                                    _doc_button(tx, ledger)
                                _delete_button(tx, ledger)

        # Set up event handlers for date inputs (they use on_value_change)
        date_from.on_value_change(_render_on_change)
        date_to.on_value_change(_render_on_change)

        render_transactions()


def _edit_button(tx: dict, ledger):
    """Create an edit button that opens a dialog."""

    async def open_edit():
        accounts = sorted(ledger.accounts)
        currencies = sorted(ledger.currencies)
        base_currency = ledger.base_currency

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label("Edit Transaction").classes("text-h6")

            with ui.row().classes("w-full gap-4"):
                edit_date = date_input("Date", str(tx["date"]))
                edit_flag = ui.select(
                    ["*", "!"], value=tx.get("flag", "*"), label="Flag"
                ).props("outlined dense")

            edit_payee = (
                ui.input(label="Payee", value=tx["payee"])
                .props("outlined dense")
                .classes("w-full")
            )
            edit_narration = (
                ui.input(label="Narration", value=tx["narration"])
                .props("outlined dense")
                .classes("w-full")
            )

            ui.label("Postings").classes("text-subtitle1 mt-2")

            # Data model for postings
            rows = []
            for i, acc in enumerate(tx["accounts"]):
                if i < len(tx["posting_amounts"]):
                    p = tx["posting_amounts"][i]
                    rows.append({
                        "account": acc,
                        "amount": float(p["amount"] if p["direction"] == "+" else -p["amount"]),
                        "currency": p["currency"],
                    })

            widget_refs = []
            postings_container = ui.column().classes("w-full gap-2")

            def render_postings():
                postings_container.clear()
                widget_refs.clear()
                with postings_container:
                    for idx, row in enumerate(rows):
                        refs = {}
                        with ui.row().classes("w-full gap-2 items-center"):
                            refs["account"] = (
                                ui.select(
                                    options=accounts,
                                    value=row["account"],
                                    label="Account",
                                    with_input=True,
                                )
                                .props("outlined dense use-input input-debounce=0 fill-input hide-selected")
                                .classes("flex-grow")
                            )
                            refs["amount"] = (
                                ui.number(label="Amount", value=row["amount"], format="%.2f")
                                .props("outlined dense")
                                .classes("w-32")
                            )
                            refs["currency"] = (
                                ui.select(options=currencies, value=row["currency"], label="Ccy")
                                .props("outlined dense")
                                .classes("w-24")
                            )

                            def remove(i=idx):
                                for j, wr in enumerate(widget_refs):
                                    rows[j]["account"] = wr["account"].value
                                    rows[j]["amount"] = wr["amount"].value
                                    rows[j]["currency"] = wr["currency"].value
                                rows.pop(i)
                                render_postings()

                            ui.button(icon="delete", on_click=remove).props("flat dense color=negative")
                        widget_refs.append(refs)

            def add_posting():
                for j, wr in enumerate(widget_refs):
                    rows[j]["account"] = wr["account"].value
                    rows[j]["amount"] = wr["amount"].value
                    rows[j]["currency"] = wr["currency"].value
                rows.append({"account": "", "amount": 0.0, "currency": base_currency})
                render_postings()

            render_postings()
            ui.button("Add Posting", icon="add", on_click=add_posting).props("flat dense")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

                async def save():
                    postings = [
                        {
                            "account": wr["account"].value,
                            "amount": wr["amount"].value,
                            "currency": wr["currency"].value,
                        }
                        for wr in widget_refs
                    ]

                    success, msg = edit_transaction(
                        ledger.ledger_path.parent,
                        str(tx["date"]),
                        tx["payee"],
                        tx["narration"],
                        new_date=edit_date.value,
                        new_flag=edit_flag.value,
                        new_payee=edit_payee.value
                        if edit_payee.value != tx["payee"]
                        else None,
                        new_narration=edit_narration.value
                        if edit_narration.value != tx["narration"]
                        else None,
                        new_postings=postings,
                    )

                    if success:
                        valid, check_msg = verify_ledger(ledger.ledger_path)
                        ledger.reload()
                        ui.notify(msg, type="positive")
                        dialog.close()
                        ui.navigate.reload()
                    else:
                        ui.notify(msg, type="negative")

                ui.button("Save", on_click=save, icon="save").props("color=primary")

        dialog.open()

    ui.button("Edit", on_click=open_edit, icon="edit").props("flat dense")


def _doc_button(tx: dict, ledger):
    """Create a button to attach a document."""

    async def open_doc_dialog():
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label("Attach Document").classes("text-h6")
            ui.label(f"{tx['date']} — {tx['payee']}").classes("text-sm text-gray-500")
            ui.label(f"{tx['amount_str']}").classes("text-sm text-gray-500")

            uploaded = {"bytes": None, "name": None}

            def on_upload(e):
                uploaded["bytes"] = e.content.read()
                uploaded["name"] = e.name

            upload = (
                ui.upload(
                    label="Choose file (PDF, JPG, PNG)",
                    on_upload=on_upload,
                    auto_upload=True,
                )
                .props("accept='.pdf,.jpg,.jpeg,.png'")
                .classes("w-full")
            )

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

                async def save_doc():
                    if not uploaded["bytes"]:
                        ui.notify("No file selected", type="warning")
                        return

                    docs_dir = ledger.ledger_path.parent / "documents"
                    success, msg, rel_path = save_document(
                        uploaded["bytes"],
                        uploaded["name"],
                        str(tx["date"]),
                        tx["payee"],
                        tx["narration"],
                        docs_dir,
                    )

                    if not success:
                        ui.notify(msg, type="negative")
                        return

                    target = find_transaction_file(
                        ledger.ledger_path.parent,
                        str(tx["date"]),
                        tx["payee"],
                        tx["narration"],
                    )
                    if target:
                        ok, doc_msg = add_document_to_transaction(
                            target,
                            str(tx["date"]),
                            tx["payee"],
                            tx["narration"],
                            str(rel_path),
                        )
                        if ok:
                            ledger.reload()
                            ui.notify(f"Document attached: {rel_path}", type="positive")
                            dialog.close()
                            ui.navigate.reload()
                        else:
                            ui.notify(doc_msg, type="negative")
                    else:
                        ui.notify("Could not find transaction file", type="negative")

                ui.button("Save", on_click=save_doc, icon="attach_file").props(
                    "color=primary"
                )

        dialog.open()

    ui.button("Add Doc", on_click=open_doc_dialog, icon="attach_file").props(
        "flat dense"
    )


def _delete_button(tx: dict, ledger):
    """Create a delete button with confirmation dialog."""

    async def open_delete_dialog():
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label("Delete Transaction").classes("text-h6")
            ui.label("Are you sure you want to delete this transaction?").classes(
                "text-sm"
            )

            with ui.column().classes("w-full border-l-4 border-red-400 pl-3 mt-2"):
                ui.label(f"{tx['date']} — {tx['payee']}").classes("font-bold")
                ui.label(tx["narration"]).classes("text-sm opacity-70")
                ui.label(tx["amount_str"]).classes("text-sm")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

                async def confirm_delete():
                    success, msg = delete_transaction(
                        ledger.ledger_path.parent,
                        str(tx["date"]),
                        tx["payee"],
                        tx["narration"],
                    )
                    if success:
                        valid, check_msg = verify_ledger(ledger.ledger_path)
                        ledger.reload()
                        ui.notify(msg, type="positive")
                        if not valid:
                            ui.notify(check_msg, type="warning")
                        dialog.close()
                        ui.navigate.reload()
                    else:
                        ui.notify(msg, type="negative")

                ui.button("Delete", on_click=confirm_delete, icon="delete").props(
                    "color=negative"
                )

        dialog.open()

    ui.button("Delete", on_click=open_delete_dialog, icon="delete").props(
        "flat dense color=negative"
    )
