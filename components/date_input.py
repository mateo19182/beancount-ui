"""Date input with popup calendar picker."""

from nicegui import ui


def date_input(label: str, value: str = "") -> ui.input:
    """An input field with a date picker popup. Returns the ui.input element."""
    with ui.input(label, value=value).props("outlined dense") as inp:
        with inp.add_slot("append"):
            icon = ui.icon("edit_calendar").classes("cursor-pointer")
            with ui.menu().props("auto-close") as menu:
                ui.date(value=value, on_change=lambda e: _sync(inp, e.value)).bind_value(inp)
            icon.on("click", menu.open)
    return inp


def _sync(inp: ui.input, value: str):
    inp.value = value
