"""
Configuration module.

Loads application settings from environment variables (.env file).
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration."""

    # Server
    host: str
    port: int
    debug: bool

    # Data refresh (price chart)
    refresh_interval: int           # seconds

    # AI analysis
    gemini_api_key: str
    ai_refresh_interval: int        # seconds between Gemini calls (respects free-tier quota)
    ai_confidence_threshold: float  # minimum confidence to show BULLISH/BEARISH signal


def load_config() -> AppConfig:
    """Load and return application configuration from environment."""
    return AppConfig(
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8050")),
        debug=os.getenv("DEBUG", "True").lower() == "true",
        refresh_interval=int(os.getenv("REFRESH_INTERVAL", "60")),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        ai_refresh_interval=int(os.getenv("AI_REFRESH_INTERVAL", "1800")),
        ai_confidence_threshold=float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.4")),
    )
