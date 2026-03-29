"""Shared page layout with navigation header."""

from contextlib import contextmanager
from nicegui import ui
import state


@contextmanager
def page_layout(title: str):
    """Page wrapper with navigation header and centered content."""
    banking_enabled = state.config and state.config.banking.enabled

    ui.colors(primary="#1a73e8")

    with ui.header().classes("items-center justify-between bg-primary px-6"):
        with ui.row().classes("items-center gap-2"):
            ui.label("Beancount").classes("text-h6 text-white font-bold")

        with ui.row().classes("gap-1"):
            _nav_button("Overview", "/")
            _nav_button("Investments", "/investments")
            _nav_button("Crypto", "/crypto")
            _nav_button("Transactions", "/transactions")
            _nav_button("Add", "/add")
            if banking_enabled:
                _nav_button("Import", "/import")

        with ui.row().classes("items-center"):
            async def on_reload():
                if state.ledger:
                    state.ledger.reload()
                    ui.notify("Ledger reloaded", type="positive")
                    ui.navigate.reload()

            ui.button(icon="refresh", on_click=on_reload).props(
                "flat round text-color=white"
            )

    with ui.column().classes("w-full max-w-7xl mx-auto p-6 gap-6"):
        ui.label(title).classes("text-h4")
        yield


def _nav_button(label: str, target: str):
    ui.link(label, target).classes(
        "text-white no-underline px-3 py-1 rounded hover:bg-white/20 transition"
    )
