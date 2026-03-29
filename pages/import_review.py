"""Import Review page: fetch, categorize, review, and import bank transactions."""

from datetime import date, timedelta
from pathlib import Path
from nicegui import ui
import state
from core.categorizer import learn_from_ledger, suggest_account, get_all_expense_income_accounts
from core.transaction_writer import write_transaction, verify_ledger
from core.document_handler import save_document
from components.layout import page_layout


def _get_cache_dir() -> Path:
    d = state.config.ledger_path.parent / ".import-cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


@ui.page("/import")
def import_review_page():
    ledger = state.ledger
    config = state.config

    from plugins.enable_banking.fetch import fetch_bank_transactions, get_available_banks
    from plugins.enable_banking.staging import (
        load_staged, save_staged, stage_transactions, check_duplicate, get_bank_account,
    )

    cache_dir = _get_cache_dir()
    learned = learn_from_ledger(ledger.entries)
    all_categories = get_all_expense_income_accounts(ledger.entries)

    with page_layout("Import Review"):
        # --- Fetch Controls ---
        ui.label("Fetch Transactions").classes("text-h5")

        with ui.row().classes("w-full gap-4 items-end flex-wrap"):
            end = date.today()
            start = end - timedelta(days=90)
            date_from = ui.date(label="From", value=start.isoformat()).props("outlined dense")
            date_to = ui.date(label="To", value=end.isoformat()).props("outlined dense")

            banks = get_available_banks(cache_dir, config.banking.banks)
            authorized = [b for b in banks if b["authorized"]]
            bank_options = {b["key"]: b["name"] for b in authorized}

            bank_select = ui.select(
                options=bank_options,
                value=list(bank_options.keys()),
                label="Banks",
            ).props("outlined dense multiple use-chips").classes("min-w-64")

            async def on_fetch():
                selected = bank_select.value or []
                if not selected:
                    ui.notify("Select at least one bank", type="warning")
                    return

                ui.notify("Fetching transactions...", type="info")
                try:
                    fetch_data = fetch_bank_transactions(
                        config.banking.app_id, config.banking.key_path,
                        cache_dir, config.banking.banks,
                        date_from.value, date_to.value, selected,
                    )

                    if "error" in fetch_data:
                        ui.notify(fetch_data["message"], type="negative")
                        return

                    total = fetch_data.get("total_transactions", 0)
                    if total == 0:
                        ui.notify("No transactions found in range", type="warning")
                        return

                    new_count = stage_transactions(cache_dir, fetch_data)
                    ui.notify(f"Fetched {total} transactions, {new_count} new", type="positive")
                    ui.navigate.reload()
                except Exception as e:
                    ui.notify(f"Fetch error: {e}", type="negative")

            ui.button("Fetch", on_click=on_fetch, icon="sync").props("color=primary")

            # Show unauthorized banks
            unauthorized = [b for b in banks if not b["authorized"]]
            if unauthorized:
                with ui.expansion("Unauthorized Banks").classes("w-full"):
                    for b in unauthorized:
                        ui.label(f"{b['name']}: run auth for {b['key']}").classes("text-sm text-gray-500")

        ui.separator().classes("my-4")

        # --- Load staged transactions ---
        staged_data = load_staged(cache_dir)
        all_txns = staged_data.get("transactions", [])

        # Apply auto-categorization and duplicate detection
        for txn in all_txns:
            if not txn.get("category"):
                txn["category"] = suggest_account(
                    txn.get("payee", ""), txn.get("narration", ""),
                    learned, txn.get("amount", 0),
                )
            if not txn.get("duplicate"):
                txn["duplicate"] = check_duplicate(txn, ledger.entries)

        active_txns = [t for t in all_txns if not t.get("imported") and not t.get("discarded")]

        if not active_txns:
            ui.label("No transactions to review. Use Fetch to get started.").classes("text-gray-400 py-8")
        else:
            # --- Summary ---
            selected_count = sum(1 for t in active_txns if t.get("selected", True))
            totals: dict[str, float] = {}
            for t in active_txns:
                if t.get("selected", True):
                    cur = t.get("currency", "EUR")
                    totals[cur] = totals.get(cur, 0) + t.get("amount", 0)

            with ui.row().classes("w-full gap-4"):
                ui.label(f"{len(active_txns)} staged").classes("font-bold")
                ui.label(f"{selected_count} selected").classes("font-bold")
                for cur, total in totals.items():
                    color = "text-green-600" if total > 0 else "text-red-600"
                    ui.label(f"{cur}: {total:,.2f}").classes(f"font-bold {color}")

            # --- AG Grid ---
            ui.label("Review & Categorize").classes("text-h5 mt-4")

            row_data = []
            for i, txn in enumerate(all_txns):
                if txn.get("imported") or txn.get("discarded"):
                    continue
                row_data.append({
                    "idx": i,
                    "selected": txn.get("selected", True),
                    "date": txn.get("date", ""),
                    "bank": txn.get("bank", ""),
                    "payee": txn.get("payee", ""),
                    "narration": txn.get("narration", ""),
                    "amount": txn.get("amount", 0),
                    "currency": txn.get("currency", "EUR"),
                    "category": txn.get("category", ""),
                    "status": txn.get("status", "Booked"),
                    "duplicate": txn.get("duplicate") or "",
                })

            grid = ui.aggrid({
                "defaultColDef": {"sortable": True, "resizable": True},
                "columnDefs": [
                    {
                        "headerName": "",
                        "field": "selected",
                        "checkboxSelection": True,
                        "headerCheckboxSelection": True,
                        "width": 50,
                        "pinned": "left",
                    },
                    {"headerName": "Date", "field": "date", "width": 110},
                    {"headerName": "Bank", "field": "bank", "width": 100},
                    {"headerName": "Payee", "field": "payee", "width": 200, "editable": True},
                    {"headerName": "Narration", "field": "narration", "width": 250, "editable": True},
                    {
                        "headerName": "Amount", "field": "amount", "width": 120,
                        "type": "numericColumn",
                        "valueFormatter": "x.toFixed(2)",
                        ":cellStyle": """params => ({color: params.value > 0 ? '#16a34a' : params.value < 0 ? '#dc2626' : '#666'})""",
                    },
                    {"headerName": "Ccy", "field": "currency", "width": 70},
                    {
                        "headerName": "Category", "field": "category", "width": 260,
                        "editable": True,
                        "cellEditor": "agSelectCellEditor",
                        "cellEditorParams": {"values": all_categories},
                    },
                    {"headerName": "Status", "field": "status", "width": 90},
                    {"headerName": "Dup", "field": "duplicate", "width": 80},
                    {"headerName": "idx", "field": "idx", "hide": True},
                ],
                "rowData": row_data,
                "rowSelection": "multiple",
                ":getRowStyle": """params => {
                    if (params.data.duplicate) return {background: '#fef9c3'};
                }""",
            }).classes("w-full").style("height: 500px")

            # --- Action buttons ---
            with ui.row().classes("gap-4 mt-4"):
                async def on_import():
                    rows = await grid.get_client_data()
                    selected_rows = [r for r in rows if r.get("selected", True)]

                    if not selected_rows:
                        ui.notify("No transactions selected", type="warning")
                        return

                    success_count = 0
                    error_count = 0

                    for row in selected_rows:
                        idx = row["idx"]
                        txn = all_txns[idx]
                        category = row.get("category") or txn.get("category")
                        if not category:
                            error_count += 1
                            continue

                        # Update from grid edits
                        txn["payee"] = row.get("payee", txn["payee"])
                        txn["narration"] = row.get("narration", txn["narration"])
                        txn["category"] = category

                        flag = "!" if txn.get("status") == "Pending" else "*"
                        bank_account = get_bank_account(txn, ledger.accounts)
                        amount = txn.get("amount", 0)
                        currency = txn.get("currency", "EUR")

                        tx_str = f'{txn["date"]} {flag} "{txn["payee"]}" "{txn["narration"]}"\n'
                        tx_str += f'  transaction_id: "{txn.get("id", "")}"\n'
                        tx_str += f'  source: "{txn.get("bank_key", "")}"\n'
                        if txn.get("document_path"):
                            tx_str += f'  document: "{txn["document_path"]}"\n'
                        tx_str += f"  {category:<40} {-amount:>12.2f} {currency}\n"
                        tx_str += f"  {bank_account:<40} {amount:>12.2f} {currency}\n"

                        month_key = txn["date"][:7]
                        target = ledger.ledger_path.parent / "transactions" / "banks" / f"{month_key}.beancount"
                        target.parent.mkdir(parents=True, exist_ok=True)

                        ok, _ = write_transaction(tx_str, target)
                        if ok:
                            success_count += 1
                            txn["imported"] = True
                            txn["selected"] = False
                        else:
                            error_count += 1

                    save_staged(cache_dir, {"transactions": all_txns})

                    if success_count:
                        valid, msg = verify_ledger(ledger.ledger_path)
                        ledger.reload()
                        ui.notify(f"Imported {success_count} transactions", type="positive")
                        if not valid:
                            ui.notify(msg, type="warning")
                        ui.navigate.reload()

                    if error_count:
                        ui.notify(f"Failed: {error_count} (missing category?)", type="negative")

                async def on_discard():
                    rows = await grid.get_client_data()
                    count = 0
                    for row in rows:
                        if row.get("selected", True):
                            idx = row["idx"]
                            all_txns[idx]["discarded"] = True
                            all_txns[idx]["selected"] = False
                            count += 1

                    if count:
                        save_staged(cache_dir, {"transactions": all_txns})
                        ui.notify(f"Discarded {count} transactions", type="info")
                        ui.navigate.reload()

                ui.button("Import Selected", on_click=on_import, icon="download").props("color=primary")
                ui.button("Discard Selected", on_click=on_discard, icon="delete").props("color=negative outlined")

        # --- Previous Imports ---
        imported_txns = [t for t in all_txns if t.get("imported")]
        if imported_txns:
            with ui.expansion(f"Previous Imports ({len(imported_txns)})").classes("w-full mt-6"):
                recent = sorted(imported_txns, key=lambda x: x.get("date", ""), reverse=True)[:10]
                rows = [{
                    "date": t.get("date", ""),
                    "payee": t.get("payee", ""),
                    "amount": f"{t.get('amount', 0):,.2f} {t.get('currency', 'EUR')}",
                    "category": t.get("category", ""),
                    "bank": t.get("bank", ""),
                } for t in recent]

                ui.table(
                    columns=[
                        {"name": "date", "label": "Date", "field": "date"},
                        {"name": "payee", "label": "Payee", "field": "payee"},
                        {"name": "amount", "label": "Amount", "field": "amount"},
                        {"name": "category", "label": "Category", "field": "category"},
                        {"name": "bank", "label": "Bank", "field": "bank"},
                    ],
                    rows=rows,
                ).classes("w-full")

        # --- Discarded ---
        discarded_txns = [t for t in all_txns if t.get("discarded")]
        if discarded_txns:
            with ui.expansion(f"Discarded ({len(discarded_txns)})").classes("w-full mt-2"):
                rows = [{
                    "idx": i,
                    "date": t.get("date", ""),
                    "payee": t.get("payee", ""),
                    "amount": f"{t.get('amount', 0):,.2f} {t.get('currency', 'EUR')}",
                    "bank": t.get("bank", ""),
                } for i, t in enumerate(all_txns) if t.get("discarded")]

                ui.table(
                    columns=[
                        {"name": "date", "label": "Date", "field": "date"},
                        {"name": "payee", "label": "Payee", "field": "payee"},
                        {"name": "amount", "label": "Amount", "field": "amount"},
                        {"name": "bank", "label": "Bank", "field": "bank"},
                    ],
                    rows=rows,
                ).classes("w-full")

                async def restore_all():
                    for t in all_txns:
                        if t.get("discarded"):
                            t["discarded"] = False
                            t["selected"] = True
                    save_staged(cache_dir, {"transactions": all_txns})
                    ui.notify("Restored all discarded", type="positive")
                    ui.navigate.reload()

                ui.button("Restore All", on_click=restore_all, icon="restore").props("flat")
