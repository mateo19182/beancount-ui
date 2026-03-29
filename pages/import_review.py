"""Import Review page: authorize banks, fetch, categorize, review, and import."""

from datetime import date, timedelta
from pathlib import Path
from nicegui import ui
import state
from core.categorizer import learn_from_ledger, suggest_account, get_all_expense_income_accounts
from core.transaction_writer import write_transaction, verify_ledger
from components.layout import page_layout
from components.date_input import date_input


def _get_cache_dir() -> Path:
    d = state.config.ledger_path.parent / ".import-cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


@ui.page("/import")
def import_review_page():
    ledger = state.ledger
    config = state.config

    from plugins.enable_banking.auth import start_authorization, complete_session, load_sessions
    from plugins.enable_banking.fetch import fetch_bank_transactions, get_available_banks
    from plugins.enable_banking.staging import (
        load_staged, save_staged, stage_transactions, check_duplicate, get_bank_account,
    )

    with page_layout("Import Review"):

        # If banking not configured, show setup guide
        if not config.banking.enabled or not config.banking.app_id:
            _render_setup_guide()
            return

        cache_dir = _get_cache_dir()
        banks = get_available_banks(cache_dir, config.banking.banks)
        authorized = [b for b in banks if b["authorized"]]
        unauthorized = [b for b in banks if not b["authorized"]]

        # =====================================================================
        # Section 1: Bank Authorization
        # =====================================================================
        with ui.expansion(
            "Bank Connections",
            icon="account_balance",
            value=len(authorized) == 0,  # auto-expand if no banks authorized
        ).classes("w-full"):

            if authorized:
                ui.label("Connected Banks").classes("text-subtitle1 mt-2")
                for b in authorized:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("check_circle", color="green")
                        ui.label(f"{b['name']} — {b['accounts']} account(s)")

                        async def on_revoke(bank_key=b["key"]):
                            sessions = load_sessions(cache_dir)
                            sessions.pop(bank_key, None)
                            from plugins.enable_banking.auth import save_sessions
                            save_sessions(cache_dir, sessions)
                            ui.notify(f"Disconnected {bank_key}", type="info")
                            ui.navigate.reload()

                        ui.button("Disconnect", on_click=on_revoke, icon="link_off").props("flat dense color=negative")

            if unauthorized:
                ui.label("Available Banks" if authorized else "No banks connected yet").classes("text-subtitle1 mt-2")

                for b in unauthorized:
                    _render_auth_flow(b, config, cache_dir)

            if not banks:
                ui.label("No banks configured. Add banks to your config.toml:").classes("text-gray-500")
                ui.code(
                    '[enable_banking.banks.revolut]\n'
                    'name = "Revolut"\n'
                    'country = "ES"',
                    language="toml",
                )

        ui.separator().classes("my-4")

        # =====================================================================
        # Section 2: Fetch Controls
        # =====================================================================
        if not authorized:
            ui.label("Connect a bank above to start importing transactions.").classes("text-gray-400 py-4")
            return

        ui.label("Fetch Transactions").classes("text-h5")

        with ui.row().classes("w-full gap-4 items-end flex-wrap"):
            end = date.today()
            start = end - timedelta(days=7)
            date_from = date_input("From", start.isoformat())
            date_to = date_input("To", end.isoformat())

            bank_options = {b["key"]: b["name"] for b in authorized}
            bank_select = ui.select(
                options=bank_options,
                value=list(bank_options.keys()),
                label="Banks",
            ).props("outlined dense multiple use-chips").classes("min-w-64")

            fetch_status = ui.column().classes("w-full")

            async def on_fetch():
                selected = bank_select.value or []
                if not selected:
                    ui.notify("Select at least one bank", type="warning")
                    return

                fetch_status.clear()
                with fetch_status:
                    spinner = ui.row().classes("items-center gap-2")
                    with spinner:
                        ui.spinner(size="sm")
                        status_label = ui.label("Fetching transactions...")

                try:
                    fetch_data = fetch_bank_transactions(
                        config.banking.app_id, config.banking.key_path,
                        cache_dir, config.banking.banks,
                        date_from.value, date_to.value, selected,
                    )

                    fetch_status.clear()

                    if "error" in fetch_data:
                        with fetch_status:
                            ui.label(f"Error: {fetch_data['message']}").classes("text-red-600")
                            if fetch_data["error"] == "no_sessions":
                                ui.label("Bank sessions may have expired. Try reconnecting in Bank Connections above.").classes("text-sm text-gray-500")
                        return

                    total = fetch_data.get("total_transactions", 0)
                    if total == 0:
                        with fetch_status:
                            ui.label("No transactions found in the selected date range.").classes("text-orange-600")
                        return

                    new_count = stage_transactions(cache_dir, fetch_data)
                    ui.notify(f"Fetched {total} transactions, {new_count} new", type="positive")

                    # Show per-bank errors if any accounts failed
                    fetch_errors = fetch_data.get("errors", [])
                    if fetch_errors:
                        with fetch_status:
                            ui.label(f"Some accounts had errors ({len(fetch_errors)}):").classes("text-orange-600 text-sm")
                            for err in fetch_errors:
                                ui.label(f"  {err}").classes("text-sm text-gray-500")

                    ui.navigate.reload()

                except Exception as e:
                    fetch_status.clear()
                    error_msg = str(e)
                    with fetch_status:
                        ui.label("Fetch failed").classes("text-red-600 font-bold")
                        ui.label(error_msg).classes("text-sm text-red-500")
                        if "401" in error_msg or "403" in error_msg or "Unauthorized" in error_msg:
                            ui.label("Your bank session may have expired. Reconnect in Bank Connections above.").classes("text-sm text-gray-500")
                        elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                            ui.label("Network issue. Check your internet connection and try again.").classes("text-sm text-gray-500")

            ui.button("Fetch", on_click=on_fetch, icon="sync").props("color=primary")

        ui.separator().classes("my-4")

        # =====================================================================
        # Section 3: Review & Categorize
        # =====================================================================
        learned = learn_from_ledger(ledger.entries)
        all_categories = get_all_expense_income_accounts(ledger.entries)

        staged_data = load_staged(cache_dir)
        all_txns = staged_data.get("transactions", [])

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
            # Summary
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

            # AG Grid
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

            # Action buttons
            with ui.row().classes("gap-4 mt-4"):
                async def on_import():
                    selected_rows = await grid.get_selected_rows()

                    if not selected_rows:
                        ui.notify("No transactions selected", type="warning")
                        return

                    # Also get all client data to pick up inline edits
                    all_grid_rows = await grid.get_client_data()
                    edited_by_idx = {r["idx"]: r for r in all_grid_rows}

                    success_count = 0
                    error_count = 0

                    for row in selected_rows:
                        idx = row["idx"]
                        txn = all_txns[idx]
                        # Use edited values from the grid
                        edited = edited_by_idx.get(idx, row)
                        category = edited.get("category") or txn.get("category")
                        if not category:
                            error_count += 1
                            continue

                        txn["payee"] = edited.get("payee", txn["payee"])
                        txn["narration"] = edited.get("narration", txn["narration"])
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
                    selected_rows = await grid.get_selected_rows()
                    count = 0
                    for row in selected_rows:
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

        # =====================================================================
        # Section 4: History
        # =====================================================================
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

        discarded_txns = [t for t in all_txns if t.get("discarded")]
        if discarded_txns:
            with ui.expansion(f"Discarded ({len(discarded_txns)})").classes("w-full mt-2"):
                rows = [{
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


def _render_setup_guide():
    """Show setup instructions when banking is not configured."""
    ui.label("Bank Import Setup").classes("text-h5")
    ui.label(
        "To import transactions from your bank, you need an Enable Banking API account "
        "and a config file with your credentials."
    ).classes("text-gray-500")

    ui.label("1. Get Enable Banking credentials").classes("text-subtitle1 mt-4")
    ui.label("Sign up at enablebanking.com and create an application to get your app_id and private key.").classes("text-sm text-gray-500")

    ui.label("2. Create a config file").classes("text-subtitle1 mt-4")
    ui.label("Save this to ~/.config/beancount-ui/config.toml:").classes("text-sm text-gray-500")
    ui.code(
        'ledger_path = "/path/to/your/main.beancount"\n'
        "\n"
        "[enable_banking]\n"
        "enabled = true\n"
        'app_id = "your-app-id"\n'
        'key_path = "/path/to/private.pem"\n'
        "\n"
        "[enable_banking.banks.revolut]\n"
        'name = "Revolut"\n'
        'country = "ES"\n'
        "\n"
        "# Add more banks as needed:\n"
        "# [enable_banking.banks.my_bank]\n"
        '# name = "My Bank"\n'
        '# country = "ES"',
        language="toml",
    )

    ui.label("3. Restart the app").classes("text-subtitle1 mt-4")
    ui.label("After saving the config, restart beancount-ui. The Import page will let you connect your banks.").classes("text-sm text-gray-500")


def _render_auth_flow(bank: dict, config, cache_dir: Path):
    """Render the authorization UI for a single unauthorized bank."""
    from plugins.enable_banking.auth import start_authorization, complete_session

    bank_key = bank["key"]
    bank_name = bank["name"]
    bank_config = config.banking.banks.get(bank_key, {})
    country = bank_config.get("country", "ES")

    with ui.card().classes("w-full p-4"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("link_off", color="orange")
            ui.label(bank_name).classes("text-subtitle1 font-bold")
            ui.label("Not connected").classes("text-sm text-gray-500")

        # Step-by-step auth flow, driven by UI state
        auth_state = {"step": "idle", "url": None}
        steps_container = ui.column().classes("w-full gap-3 mt-2")

        def render_steps():
            steps_container.clear()
            with steps_container:
                if auth_state["step"] == "idle":
                    ui.label(
                        "Connect your bank account to import transactions automatically."
                    ).classes("text-sm text-gray-500")

                    async def start_auth():
                        try:
                            ui.notify(f"Starting {bank_name} authorization...", type="info")
                            result = start_authorization(
                                config.banking.app_id,
                                config.banking.key_path,
                                bank_config.get("name", bank_name),
                                country,
                            )
                            auth_state["url"] = result.get("url")
                            auth_state["step"] = "waiting_for_code"
                            render_steps()
                        except Exception as e:
                            ui.notify(f"Auth error: {e}", type="negative")

                    ui.button(
                        f"Connect {bank_name}", on_click=start_auth, icon="link"
                    ).props("color=primary")

                elif auth_state["step"] == "waiting_for_code":
                    ui.label("Step 1: Authorize in your browser").classes("text-subtitle2")
                    ui.label(
                        "A browser window should open. Log in to your bank and authorize access. "
                        "If the browser didn't open, click the link below."
                    ).classes("text-sm text-gray-500")

                    auth_url = auth_state["url"]
                    if auth_url:
                        # Open browser automatically
                        import webbrowser
                        try:
                            webbrowser.open(auth_url)
                        except Exception:
                            pass

                        with ui.row().classes("items-center gap-2"):
                            ui.link("Open authorization page", auth_url, new_tab=True).classes("text-sm")
                            ui.button(
                                icon="content_copy",
                                on_click=lambda: ui.run_javascript(
                                    f'navigator.clipboard.writeText("{auth_url}")'
                                ),
                            ).props("flat dense size=sm").tooltip("Copy URL")

                    ui.separator()
                    ui.label("Step 2: Paste the authorization code").classes("text-subtitle2")
                    ui.label(
                        "After authorizing, your bank will redirect you to a page with a code. "
                        "Copy the full URL or the code parameter and paste it below."
                    ).classes("text-sm text-gray-500")

                    code_input = ui.input(
                        label="Authorization code or redirect URL",
                        placeholder="Paste the code or full redirect URL here...",
                    ).props("outlined dense").classes("w-full")

                    with ui.row().classes("gap-2"):
                        async def submit_code():
                            raw = code_input.value or ""
                            raw = raw.strip()
                            if not raw:
                                ui.notify("Please paste the authorization code", type="warning")
                                return

                            # Extract code from URL if user pasted the full redirect URL
                            code = _extract_code(raw)

                            try:
                                ui.notify("Completing authorization...", type="info")
                                session = complete_session(
                                    config.banking.app_id,
                                    config.banking.key_path,
                                    code,
                                    bank_key,
                                    cache_dir,
                                )
                                accounts = session.get("accounts", [])
                                ui.notify(
                                    f"Connected {bank_name} with {len(accounts)} account(s)",
                                    type="positive",
                                )
                                ui.navigate.reload()
                            except Exception as e:
                                ui.notify(f"Authorization failed: {e}", type="negative")

                        ui.button("Complete Authorization", on_click=submit_code, icon="check").props("color=primary")

                        def cancel_auth():
                            auth_state["step"] = "idle"
                            auth_state["url"] = None
                            render_steps()

                        ui.button("Cancel", on_click=cancel_auth).props("flat")

        render_steps()


def _extract_code(raw: str) -> str:
    """Extract the authorization code from a raw input (URL or bare code)."""
    raw = raw.strip()

    # If it looks like a URL, try to extract the 'code' parameter
    if "?" in raw or "code=" in raw:
        from urllib.parse import urlparse, parse_qs
        try:
            parsed = urlparse(raw)
            params = parse_qs(parsed.query)
            if "code" in params:
                return params["code"][0]
        except Exception:
            pass

    return raw
