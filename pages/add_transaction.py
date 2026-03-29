"""Add Transaction page: create new multi-posting transactions."""

from datetime import date
from nicegui import ui
import state
from core.transaction_writer import (
    format_transaction, calculate_balance, validate_transaction,
    determine_target_file, write_transaction, verify_ledger,
)
from core.document_handler import save_document
from components.layout import page_layout
from components.date_input import date_input


@ui.page("/add")
def add_transaction_page():
    ledger = state.ledger
    all_accounts = ledger.accounts
    all_currencies = sorted(ledger.currencies)
    base_currency = ledger.base_currency

    with page_layout("Add Transaction"):
        # --- Basic info ---
        with ui.row().classes("w-full gap-4 items-end"):
            tx_date = date_input("Date", date.today().isoformat())
            tx_flag = ui.select(["*", "!"], value="*", label="Flag").props("outlined dense").classes("w-20")
            tx_payee = ui.input(label="Payee", placeholder="Who was it?").props("outlined dense").classes("flex-grow")
            tx_narration = ui.input(label="Narration", placeholder="What for?").props("outlined dense").classes("flex-grow")

        # --- Document upload ---
        with ui.expansion("Attach Document (optional)", icon="attach_file").classes("w-full"):
            uploaded = {"bytes": None, "name": None}

            def on_upload(e):
                uploaded["bytes"] = e.content.read()
                uploaded["name"] = e.name
                ui.notify(f"File ready: {e.name}", type="info")

            ui.upload(
                label="Choose file (PDF, JPG, PNG)",
                on_upload=on_upload,
                auto_upload=True,
            ).props("accept='.pdf,.jpg,.jpeg,.png'").classes("w-full")

        # --- Postings ---
        ui.label("Postings").classes("text-h6 mt-4")

        postings_container = ui.column().classes("w-full gap-2")
        posting_widgets: list[dict] = []

        def add_posting(account: str | None = None, amount: float = 0.0, currency: str = base_currency):
            with postings_container:
                with ui.row().classes("w-full gap-2 items-center") as row:
                    acc = ui.select(
                        all_accounts, value=account, label="Account",
                        with_input=True, clearable=True,
                    ).props("outlined dense").classes("flex-grow")
                    amt = ui.number(label="Amount", value=amount, format="%.2f").props("outlined dense").classes("w-36")
                    cur = ui.select(all_currencies, value=currency, label="Currency").props("outlined dense").classes("w-28")

                    posting_widgets.append({"row": row, "account": acc, "amount": amt, "currency": cur})

                    # Bind changes to update preview/balance
                    acc.on_value_change(lambda _: update_preview())
                    amt.on_value_change(lambda _: update_preview())
                    cur.on_value_change(lambda _: update_preview())

        def remove_last_posting():
            if len(posting_widgets) > 2:
                widget = posting_widgets.pop()
                postings_container.remove(widget["row"])
                update_preview()

        # Start with 2 postings
        add_posting()
        add_posting()

        with ui.row().classes("gap-2"):
            ui.button("Add Posting", on_click=lambda: add_posting(), icon="add").props("flat")
            ui.button("Remove Last", on_click=remove_last_posting, icon="remove").props("flat")

        # --- Balance & Preview ---
        ui.separator().classes("my-4")

        with ui.row().classes("w-full gap-8"):
            with ui.column().classes("flex-grow"):
                ui.label("Balance Check").classes("text-subtitle1")
                balance_display = ui.column().classes("gap-1")

            with ui.column().classes("flex-grow"):
                ui.label("Preview").classes("text-subtitle1")
                preview_code = ui.code("").classes("w-full")

        # --- Submit ---
        submit_btn = ui.button("Create Transaction", icon="check").props("color=primary").classes("mt-4")

        def get_postings_data() -> list[dict]:
            return [{
                "account": w["account"].value or "",
                "amount": float(w["amount"].value or 0),
                "currency": w["currency"].value or base_currency,
            } for w in posting_widgets]

        def update_preview():
            postings = get_postings_data()

            # Balance check
            balance = calculate_balance(postings)
            balance_display.clear()
            all_balanced = True
            with balance_display:
                for cur, total in balance.items():
                    balanced = abs(total) < 0.015
                    icon_name = "check_circle" if balanced else "error"
                    color = "text-green-600" if balanced else "text-red-600"
                    with ui.row().classes("items-center").style("gap: 4px"):
                        ui.icon(icon_name).classes(color)
                        ui.label(f"{cur}: {total:+.2f}").classes(f"text-sm {color}")
                    if not balanced:
                        all_balanced = False

            # Preview
            tx_str = format_transaction(
                tx_date.value or date.today().isoformat(),
                tx_flag.value or "*",
                tx_payee.value or None,
                tx_narration.value or None,
                postings,
            )
            preview_code.set_content(tx_str)

            # Enable/disable submit
            submit_btn.set_enabled(all_balanced and len(postings) >= 2)

        # Bind basic info changes to preview
        for widget in [tx_date, tx_flag, tx_payee, tx_narration]:
            widget.on_value_change(lambda _: update_preview())

        update_preview()

        async def on_submit():
            postings = get_postings_data()
            valid, msg = validate_transaction(postings, all_accounts, ledger.currencies)
            if not valid:
                ui.notify(msg, type="negative")
                return

            metadata = None
            if uploaded["bytes"]:
                docs_dir = ledger.ledger_path.parent / "documents"
                ok, doc_msg, rel_path = save_document(
                    uploaded["bytes"], uploaded["name"],
                    tx_date.value, tx_payee.value, tx_narration.value,
                    docs_dir,
                )
                if ok:
                    metadata = {"document": str(rel_path)}
                else:
                    ui.notify(doc_msg, type="negative")
                    return

            tx_str = format_transaction(
                tx_date.value, tx_flag.value,
                tx_payee.value or None, tx_narration.value or None,
                postings, metadata,
            )

            target = determine_target_file(
                ledger.ledger_path.parent,
                [p["account"] for p in postings],
            )
            success, write_msg = write_transaction(tx_str, target)

            if success:
                valid, check_msg = verify_ledger(ledger.ledger_path)
                ledger.reload()
                ui.notify(f"Transaction created in {target.name}", type="positive")
                if not valid:
                    ui.notify(check_msg, type="warning")
                ui.navigate.reload()
            else:
                ui.notify(write_msg, type="negative")

        submit_btn.on_click(on_submit)
