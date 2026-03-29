"""Styled metric display card."""

from nicegui import ui


def metric_card(label: str, value: str, icon: str | None = None):
    """Display a metric in a styled card."""
    with ui.card().classes("p-4 min-w-48"):
        if icon:
            ui.icon(icon).classes("text-2xl text-primary mb-1")
        ui.label(label).classes("text-sm text-gray-500 uppercase tracking-wide")
        ui.label(value).classes("text-2xl font-bold")
