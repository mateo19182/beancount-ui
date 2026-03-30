"""Styled metric display card."""

from nicegui import ui


def metric_card(label: str, value: str, icon: str | None = None, color_class: str = ""):
    """Display a metric in a styled card."""
    with ui.card().classes("p-4 min-w-48"):
        icon_classes = (
            f"text-2xl text-primary mb-1 {color_class}"
            if color_class
            else "text-2xl text-primary mb-1"
        )
        if icon:
            ui.icon(icon).classes(icon_classes)
        ui.label(label).classes("text-sm text-gray-500 uppercase tracking-wide")
        ui.label(value).classes("text-2xl font-bold")
