"""
Dash application factory.

Creates and configures the Dash app instance without running it,
following the application factory pattern for testability.
"""

import dash

from src.config import AppConfig
from src.dashboard.callbacks import register_callbacks
from src.dashboard.layout import build_layout


def create_app(config: AppConfig) -> dash.Dash:
    """
    Instantiate and configure the Dash application.

    Args:
        config: Loaded AppConfig instance.

    Returns:
        A configured (but not yet running) Dash application.
    """
    app = dash.Dash(
        __name__,
        title="Gold Price Tracker",
        update_title="Updating...",
        # assets/ folder is picked up automatically by Dash
    )

    refresh_interval_ms = config.refresh_interval * 1_000
    ai_refresh_interval_ms = config.ai_refresh_interval * 1_000

    app.layout = build_layout(refresh_interval_ms, ai_refresh_interval_ms)

    register_callbacks(
        app,
        gemini_api_key=config.gemini_api_key,
        ai_cache_ttl=config.ai_refresh_interval,
    )

    return app
