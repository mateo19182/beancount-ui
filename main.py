"""Beancount UI — desktop app for managing beancount ledgers."""

from nicegui import ui
from config import load_config
from core.ledger import Ledger
import state


def run():
    config = load_config()
    state.config = config

    if config.ledger_path:
        state.ledger = Ledger(config.ledger_path)

    # Import pages to register @ui.page routes
    import pages.overview
    import pages.charts
    import pages.investments
    import pages.crypto
    import pages.transactions
    import pages.add_transaction

    import pages.import_review

    ui.run(
        title="Beancount",
        native=config.native,
        port=config.port,
        reload=False,
        dark=None,
        storage_secret="beancount-ui",
    )


if __name__ == "__main__":
    run()
