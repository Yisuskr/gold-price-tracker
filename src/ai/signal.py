"""
Gold market signal model.

Defines the structured output that the AI analyzer produces.
This is the contract between the analyzer and the dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class SignalDirection(str, Enum):
    """Predicted direction of the gold price movement."""

    BULLISH = "BULLISH"   # Upward pressure expected
    BEARISH = "BEARISH"   # Downward pressure expected
    NEUTRAL = "NEUTRAL"   # No clear directional signal


@dataclass
class GoldSignal:
    """
    Complete AI-generated analysis signal for the gold market.

    Produced by the GoldAnalyzer and consumed by the dashboard callbacks.
    """

    # Core prediction
    direction: SignalDirection
    confidence: float                    # 0.0 – 1.0

    # Explanation buckets
    technical_reasons: list[str] = field(default_factory=list)
    news_reasons: list[str] = field(default_factory=list)
    pattern_summary: str = ""            # Free-text summary of detected patterns
    gemini_summary: str = ""            # Full Gemini-generated narrative

    # Recent news that influenced the signal
    related_articles: list[dict] = field(default_factory=list)  # [{title, url, domain}]

    # Technical indicators snapshot
    rsi: float | None = None
    volatility_pct: float | None = None  # 20-day ATR as % of price
    trend: Literal["UP", "DOWN", "SIDEWAYS"] | None = None
    ma50_vs_ma200: Literal["GOLDEN_CROSS", "DEATH_CROSS", "NEUTRAL"] | None = None

    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None            # Set if analysis partially failed

    # ── Convenience helpers ───────────────────────────────────────────────

    @property
    def confidence_pct(self) -> int:
        """Return confidence as an integer percentage (0-100)."""
        return round(self.confidence * 100)

    @property
    def is_valid(self) -> bool:
        """Return True if the signal was generated without critical errors."""
        return self.error is None

    @classmethod
    def error_signal(cls, reason: str) -> "GoldSignal":
        """Factory: return a neutral signal carrying an error message."""
        return cls(
            direction=SignalDirection.NEUTRAL,
            confidence=0.0,
            error=reason,
        )
