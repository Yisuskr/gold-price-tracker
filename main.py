"""
Entry point for the Gold Price Tracker application.

Just run `python main.py` and open http://127.0.0.1:8050 in your browser.
"""

import logging
import sys

from src.config import load_config
from src.dashboard.app import create_app


def setup_logging() -> None:
    """Set up a clean log format that shows timestamp, level, and module name."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    """Boot the app: load config, build the Dash instance, start the server."""
    setup_logging()
    logger = logging.getLogger(__name__)

    config = load_config()
    logger.info("Starting Gold Price Tracker on http://%s:%s", config.host, config.port)

    app = create_app(config)
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug,
    )


if __name__ == "__main__":
    main()
