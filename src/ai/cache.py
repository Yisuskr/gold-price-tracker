"""
AI analysis result cache.

Persists GoldSignal results to a local JSON file to avoid redundant
Gemini API calls on every dashboard refresh. Respects a configurable
TTL (time-to-live) in seconds.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.ai.signal import GoldSignal, SignalDirection

logger = logging.getLogger(__name__)

_CACHE_FILE = Path(__file__).parent.parent.parent / ".ai_cache.json"


class SignalCache:
    """
    Simple file-backed cache for GoldSignal objects.

    Stores the last computed signal as JSON. On read, checks whether
    the cached entry is still within the TTL window.
    """

    def __init__(self, ttl_seconds: int = 1800, cache_path: Path = _CACHE_FILE) -> None:
        self._ttl = ttl_seconds
        self._path = cache_path

    def get(self) -> Optional[GoldSignal]:
        """
        Return the cached signal if it exists and has not expired.

        Returns None if the cache is empty, corrupt, or stale.
        """
        if not self._path.exists():
            return None

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            generated_at = datetime.fromisoformat(data["generated_at"])

            # ensure timezone-aware comparison
            now = datetime.now(tz=timezone.utc)
            if generated_at.tzinfo is None:
                generated_at = generated_at.replace(tzinfo=timezone.utc)

            age_seconds = (now - generated_at).total_seconds()
            if age_seconds > self._ttl:
                logger.debug("Cache expired (age=%.0fs, ttl=%ds)", age_seconds, self._ttl)
                return None

            return self._deserialize(data)

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Could not read AI cache: %s", exc)
            return None

    def set(self, signal: GoldSignal) -> None:
        """Persist a GoldSignal to the cache file."""
        try:
            self._path.write_text(
                json.dumps(self._serialize(signal), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Could not write AI cache: %s", exc)

    def invalidate(self) -> None:
        """Remove the cache file, forcing a fresh analysis on next read."""
        if self._path.exists():
            self._path.unlink()

    # ── Serialization helpers ─────────────────────────────────────────────

    @staticmethod
    def _serialize(signal: GoldSignal) -> dict:
        return {
            "direction": signal.direction.value,
            "confidence": signal.confidence,
            "technical_reasons": signal.technical_reasons,
            "news_reasons": signal.news_reasons,
            "pattern_summary": signal.pattern_summary,
            "gemini_summary": signal.gemini_summary,
            "related_articles": signal.related_articles,
            "rsi": signal.rsi,
            "volatility_pct": signal.volatility_pct,
            "trend": signal.trend,
            "ma50_vs_ma200": signal.ma50_vs_ma200,
            "generated_at": signal.generated_at.isoformat(),
            "error": signal.error,
        }

    @staticmethod
    def _deserialize(data: dict) -> GoldSignal:
        return GoldSignal(
            direction=SignalDirection(data["direction"]),
            confidence=data["confidence"],
            technical_reasons=data.get("technical_reasons", []),
            news_reasons=data.get("news_reasons", []),
            pattern_summary=data.get("pattern_summary", ""),
            gemini_summary=data.get("gemini_summary", ""),
            related_articles=data.get("related_articles", []),
            rsi=data.get("rsi"),
            volatility_pct=data.get("volatility_pct"),
            trend=data.get("trend"),
            ma50_vs_ma200=data.get("ma50_vs_ma200"),
            generated_at=datetime.fromisoformat(data["generated_at"]),
            error=data.get("error"),
        )
