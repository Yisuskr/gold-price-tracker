"""
Gold price data fetcher.

Responsible for retrieving historical and current gold price data
from Yahoo Finance using the yfinance library.
Also provides USD/EUR exchange rate for currency conversion.
"""

import logging
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Gold futures ticker on Yahoo Finance
GOLD_TICKER = "GC=F"

# USD to EUR exchange rate ticker on Yahoo Finance
USDEUR_TICKER = "EURUSD=X"


class GoldDataFetcher:
    """Fetches gold price data from Yahoo Finance."""

    def __init__(self, ticker: str = GOLD_TICKER) -> None:
        self.ticker = ticker
        self._asset = yf.Ticker(ticker)

    def get_current_price(self) -> Optional[float]:
        """
        Return the most recent available gold price in USD.

        Returns None if data cannot be retrieved.
        """
        try:
            data = self._asset.history(period="1d", interval="1m")
            if data.empty:
                logger.warning("No current price data returned for %s", self.ticker)
                return None
            return float(data["Close"].iloc[-1])
        except Exception as exc:
            logger.error("Failed to fetch current price: %s", exc)
            return None

    def get_historical_data(
        self,
        period: str = "1mo",
        interval: str = "1h",
    ) -> pd.DataFrame:
        """
        Return historical OHLCV data for gold.

        Args:
            period:   yfinance period string, e.g. '1d', '5d', '1mo', '3mo', '1y'.
            interval: yfinance interval string, e.g. '1m', '5m', '1h', '1d'.

        Returns:
            DataFrame with columns [Open, High, Low, Close, Volume] indexed by datetime.
        """
        try:
            data = self._asset.history(period=period, interval=interval)
            if data.empty:
                logger.warning(
                    "No historical data returned for %s (period=%s, interval=%s)",
                    self.ticker,
                    period,
                    interval,
                )
            return data
        except Exception as exc:
            logger.error("Failed to fetch historical data: %s", exc)
            return pd.DataFrame()

    def get_intraday_data(self) -> pd.DataFrame:
        """Return minute-by-minute data for the current trading day."""
        return self.get_historical_data(period="1d", interval="1m")

    def get_weekly_data(self) -> pd.DataFrame:
        """Return hourly data for the past week."""
        return self.get_historical_data(period="5d", interval="1h")

    def get_monthly_data(self) -> pd.DataFrame:
        """Return daily data for the past month."""
        return self.get_historical_data(period="1mo", interval="1d")

    def get_yearly_data(self) -> pd.DataFrame:
        """Return daily data for the past year."""
        return self.get_historical_data(period="1y", interval="1d")


class ExchangeRateFetcher:
    """Fetches USD/EUR exchange rate from Yahoo Finance."""

    def __init__(self) -> None:
        self._asset = yf.Ticker(USDEUR_TICKER)

    def get_usd_to_eur(self) -> float:
        """
        Return the current USD → EUR conversion rate.

        Falls back to a safe approximation if data is unavailable.
        """
        try:
            data = self._asset.history(period="1d", interval="1m")
            if data.empty:
                logger.warning("Could not fetch USD/EUR rate, using fallback 0.92")
                return 0.92
            return float(data["Close"].iloc[-1])
        except Exception as exc:
            logger.error("Failed to fetch exchange rate: %s", exc)
            return 0.92
