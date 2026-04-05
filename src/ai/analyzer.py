"""
Gold market AI analyzer.

Combines two analytical layers:

1. Technical / ML analysis (no external API)
   - Computes RSI, 20-day ATR (volatility), 50/200-day moving averages,
     and momentum from 1 year of daily gold price data.
   - Detects historical price spikes (>= SPIKE_THRESHOLD % in one day).

2. News correlation + prediction via Google Gemini
   - For each historical spike, fetches GDELT headlines from the same
     ±3-day window and builds a correlation context.
   - Fetches current week's GDELT headlines.
   - Sends everything to Gemini-2.0-Flash for structured JSON analysis.

The final GoldSignal merges both layers.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
from google import genai
from google.genai import types

from src.ai.signal import GoldSignal, SignalDirection
from src.data.fetcher import GoldDataFetcher
from src.news.fetcher import GdeltNewsFetcher, NewsArticle

logger = logging.getLogger(__name__)

# A single-day move >= this percentage is considered a price spike worth studying
SPIKE_THRESHOLD_PCT = 1.5

# How many historical spikes to include in the Gemini context (keeps the prompt small)
MAX_HISTORICAL_SPIKES = 8

# Max headlines per GDELT query window passed to Gemini
MAX_HEADLINES_PER_WINDOW = 8


class GoldAnalyzer:
    """
    Orchestrates ML technical analysis and Gemini-powered news correlation
    to produce a structured GoldSignal prediction.
    """

    def __init__(self, gemini_api_key: str) -> None:
        self._gold = GoldDataFetcher()
        self._news = GdeltNewsFetcher()
        # The Gemini client is stateless — we create it once and reuse it
        self._gemini = genai.Client(api_key=gemini_api_key)

    # ── Public API ────────────────────────────────────────────────────────

    def analyze(self) -> GoldSignal:
        """
        Run the full analysis pipeline and return a GoldSignal.

        Steps:
          1. Fetch 1 year of daily gold price data.
          2. Compute technical indicators.
          3. Detect historical spikes and correlate with GDELT news.
          4. Fetch current week's news.
          5. Call Gemini for structured prediction.
          6. Merge everything into a GoldSignal.
        """
        try:
            df = self._gold.get_yearly_data()
            if df.empty:
                return GoldSignal.error_signal("Could not retrieve gold price data.")

            indicators = self._compute_indicators(df)
            spikes = self._detect_spikes(df)

            # For each spike we pull the news context from around that date —
            # this teaches Gemini what kinds of events actually move gold
            historical_context = self._build_historical_context(spikes)
            current_news = self._news.get_recent_articles(timespan="7d", max_records=30)

            gemini_result = self._call_gemini(
                indicators, historical_context, current_news
            )

            return self._build_signal(indicators, gemini_result, current_news)

        except Exception as exc:
            logger.exception("Analysis pipeline failed: %s", exc)
            return GoldSignal.error_signal(f"Analysis failed: {exc}")

    # ── Technical indicators ──────────────────────────────────────────────

    @staticmethod
    def _compute_indicators(df: pd.DataFrame) -> dict[str, Any]:
        """
        Compute RSI-14, 20-day ATR volatility, 50/200-day SMA and trend.

        Returns a flat dict of indicator values.
        """
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # RSI-14: measures momentum on a 0–100 scale
        # above 70 = overbought, below 30 = oversold
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])

        # 20-day ATR as % of current price — normalised volatility
        # True Range accounts for overnight gaps, not just intra-day range
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        atr20 = float(tr.rolling(20).mean().iloc[-1])
        current_price = float(close.iloc[-1])
        volatility_pct = (atr20 / current_price) * 100

        # 50 and 200-day SMAs — the classic trend-following pair
        # golden cross (MA50 above MA200) = bullish signal
        ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        if ma50 and ma200:
            prev_ma50 = float(close.rolling(50).mean().iloc[-2])
            prev_ma200 = float(close.rolling(200).mean().iloc[-2])
            if prev_ma50 <= prev_ma200 and ma50 > ma200:
                ma_signal = "GOLDEN_CROSS"
            elif prev_ma50 >= prev_ma200 and ma50 < ma200:
                ma_signal = "DEATH_CROSS"
            else:
                ma_signal = "NEUTRAL"
        else:
            ma_signal = "NEUTRAL"

        # short-term trend via 20-day linear regression slope
        # positive slope = price has been climbing over the past month
        if len(close) >= 20:
            y = close.iloc[-20:].values
            x = np.arange(len(y))
            slope = float(np.polyfit(x, y, 1)[0])
            trend = "UP" if slope > 0 else "DOWN"
        else:
            trend = "SIDEWAYS"

        # 30-day price change — simple momentum reference for Gemini
        change_30d = float(
            ((close.iloc[-1] - close.iloc[-30]) / close.iloc[-30]) * 100
        ) if len(close) >= 30 else 0.0

        return {
            "rsi": round(rsi, 2),
            "volatility_pct": round(volatility_pct, 3),
            "trend": trend,
            "ma50_vs_ma200": ma_signal,
            "ma50": round(ma50, 2) if ma50 else None,
            "ma200": round(ma200, 2) if ma200 else None,
            "current_price": round(current_price, 2),
            "change_30d_pct": round(change_30d, 2),
        }

    # ── Spike detection ───────────────────────────────────────────────────

    @staticmethod
    def _detect_spikes(df: pd.DataFrame) -> list[dict]:
        """
        Find days where the gold price moved >= SPIKE_THRESHOLD_PCT in one day.

        Returns a list of dicts: {date, change_pct, direction}.
        """
        close = df["Close"]
        pct_change = close.pct_change() * 100
        spikes = pct_change[pct_change.abs() >= SPIKE_THRESHOLD_PCT]

        result = []
        for date, change in spikes.items():
            result.append(
                {
                    "date": date if isinstance(date, datetime) else pd.Timestamp(date).to_pydatetime(),
                    "change_pct": round(float(change), 2),
                    "direction": "UP" if change > 0 else "DOWN",
                }
            )

        # most recent spikes are more relevant, sort descending and cap the list
        result.sort(key=lambda x: x["date"], reverse=True)
        return result[:MAX_HISTORICAL_SPIKES]

    # ── GDELT correlation ─────────────────────────────────────────────────

    def _build_historical_context(self, spikes: list[dict]) -> list[dict]:
        """
        For each spike, fetch GDELT headlines from the ±3 day window and
        return a list of {date, change_pct, direction, headlines} dicts.

        This builds the "training examples" we give Gemini so it can learn
        which news patterns tend to cause big gold moves.
        """
        context = []
        for spike in spikes:
            dt: datetime = spike["date"]
            # GDELT requires timezone-aware datetimes
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            start = dt - timedelta(days=3)
            end = dt + timedelta(days=1)

            articles = self._news.get_articles_for_date_range(
                start, end, max_records=MAX_HEADLINES_PER_WINDOW
            )
            headlines = [a.title for a in articles if a.title][:MAX_HEADLINES_PER_WINDOW]

            context.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "change_pct": spike["change_pct"],
                    "direction": spike["direction"],
                    "headlines": headlines,
                }
            )
        return context

    # ── Gemini call ───────────────────────────────────────────────────────

    def _call_gemini(
        self,
        indicators: dict,
        historical_context: list[dict],
        current_news: list[NewsArticle],
    ) -> dict:
        """
        Send technical indicators + historical correlations + current news
        to Gemini-2.0-Flash and receive a structured JSON analysis.

        We use response_mime_type='application/json' to guarantee valid JSON
        output without needing to strip markdown fences manually.

        Returns the parsed JSON dict, or a safe fallback dict on failure.
        """
        current_headlines = [
            {"title": a.title, "domain": a.domain, "date": a.seen_date.strftime("%Y-%m-%d")}
            for a in current_news[:20]
        ]

        prompt = f"""You are a senior gold market analyst. Your task is to analyze the gold (XAU/USD) market and generate a structured prediction.

## Current Technical Indicators
{json.dumps(indicators, indent=2)}

## Historical Price Spikes (last 12 months) with correlated news
Each entry shows a significant single-day price movement and the news headlines
published within ±3 days of that event. Use these to learn what types of events
tend to move the gold price.
{json.dumps(historical_context, indent=2)}

## Current Week's Relevant News Headlines
{json.dumps(current_headlines, indent=2)}

## Your Task
Based on the technical indicators, the historical spike-news correlations you have learned,
and the current week's news, produce a market analysis and short-term prediction.

Return ONLY valid JSON matching this exact schema:
{{
  "direction": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence": <float 0.0-1.0>,
  "technical_reasons": [<list of strings, max 4>],
  "news_reasons": [<list of strings, max 4>],
  "pattern_summary": "<1-2 sentence summary of detected technical patterns>",
  "gemini_summary": "<3-5 sentence narrative explaining the full analysis and prediction in plain English>"
}}"""

        try:
            response = self._gemini.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,       # low temp = more deterministic, less hallucination
                    max_output_tokens=1024,
                ),
            )
            raw = response.text or "{}"
            return json.loads(raw)

        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            # return a neutral fallback so the dashboard still renders cleanly
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "technical_reasons": [],
                "news_reasons": [],
                "pattern_summary": "",
                "gemini_summary": f"AI analysis unavailable: {exc}",
            }

    # ── Signal assembly ───────────────────────────────────────────────────

    @staticmethod
    def _build_signal(
        indicators: dict,
        gemini_result: dict,
        current_news: list[NewsArticle],
    ) -> GoldSignal:
        """Merge indicator data and Gemini output into a GoldSignal."""
        try:
            direction = SignalDirection(gemini_result.get("direction", "NEUTRAL"))
        except ValueError:
            # gemini returned an unknown direction string — fall back to neutral
            direction = SignalDirection.NEUTRAL

        # top 6 articles for the side panel
        related = [
            {"title": a.title, "url": a.url, "domain": a.domain}
            for a in current_news[:6]
        ]

        return GoldSignal(
            direction=direction,
            confidence=float(gemini_result.get("confidence", 0.0)),
            technical_reasons=gemini_result.get("technical_reasons", []),
            news_reasons=gemini_result.get("news_reasons", []),
            pattern_summary=gemini_result.get("pattern_summary", ""),
            gemini_summary=gemini_result.get("gemini_summary", ""),
            related_articles=related,
            rsi=indicators.get("rsi"),
            volatility_pct=indicators.get("volatility_pct"),
            trend=indicators.get("trend"),
            ma50_vs_ma200=indicators.get("ma50_vs_ma200"),
            generated_at=datetime.utcnow(),
        )
