"""
GDELT news fetcher.

Retrieves gold-related and geopolitical news articles from the GDELT
Project DOC 2.0 API. No API key required.

GDELT themes used:
  - ECON_GOLD              → gold / precious metals
  - ECON_STOCKMARKET       → stock market events
  - ECON_TRADE             → trade / sanctions
  - WB_2671_CONFLICT_AND_VIOLENCE → armed conflicts
  - TERROR                 → terrorism events
  - PROTEST                → civil unrest
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Themes that historically correlate with gold price movements
GOLD_QUERY = (
    '(theme:ECON_GOLD OR theme:ECON_STOCKMARKET OR theme:ECON_TRADE '
    'OR theme:WB_2671_CONFLICT_AND_VIOLENCE OR theme:TERROR OR theme:PROTEST) '
    'sourcelang:english'
)


@dataclass(frozen=True)
class NewsArticle:
    """Represents a single news article from GDELT."""

    title: str
    url: str
    domain: str
    seen_date: datetime
    language: str
    source_country: str


class GdeltNewsFetcher:
    """Fetches gold-relevant news from the GDELT Project API."""

    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "GoldPriceTracker/1.0"})

    def get_recent_articles(
        self,
        timespan: str = "7d",
        max_records: int = 50,
    ) -> list[NewsArticle]:
        """
        Return recent articles relevant to gold price movements.

        Args:
            timespan:    GDELT rolling window string (e.g. '1d', '7d', '3m').
                         Maximum supported by GDELT is 3 months ('3m').
            max_records: Maximum number of articles to retrieve (max 250).

        Returns:
            List of NewsArticle objects sorted by date descending.
        """
        params = {
            "query": GOLD_QUERY,
            "mode": "artlist",
            "format": "json",
            "timespan": timespan,
            "maxrecords": min(max_records, 250),
            "sort": "datedesc",
        }

        try:
            response = self._session.get(
                GDELT_API_URL, params=params, timeout=self._timeout
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_articles(data)
        except requests.RequestException as exc:
            logger.error("GDELT request failed: %s", exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error fetching GDELT news: %s", exc)
            return []

    def get_articles_for_date_range(
        self,
        start: datetime,
        end: datetime,
        max_records: int = 30,
    ) -> list[NewsArticle]:
        """
        Return articles within a specific date range.

        Used for historical correlation analysis (matching past gold price
        spikes with news events that occurred in the same window).

        Args:
            start:       Start of the date range (UTC).
            end:         End of the date range (UTC).
            max_records: Maximum articles to return.

        Returns:
            List of NewsArticle objects.
        """
        fmt = "%Y%m%d%H%M%S"
        params = {
            "query": GOLD_QUERY,
            "mode": "artlist",
            "format": "json",
            "startdatetime": start.strftime(fmt),
            "enddatetime": end.strftime(fmt),
            "maxrecords": min(max_records, 250),
            "sort": "datedesc",
        }

        try:
            response = self._session.get(
                GDELT_API_URL, params=params, timeout=self._timeout
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_articles(data)
        except requests.RequestException as exc:
            logger.error("GDELT date-range request failed: %s", exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error in GDELT date-range fetch: %s", exc)
            return []

    @staticmethod
    def _parse_articles(data: dict) -> list[NewsArticle]:
        """Parse raw GDELT JSON response into NewsArticle objects."""
        articles = []
        for item in data.get("articles", []):
            try:
                seen_raw = item.get("seendate", "")
                # GDELT format: '20240315T120000Z'
                seen_dt = datetime.strptime(seen_raw, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc
                )
                articles.append(
                    NewsArticle(
                        title=item.get("title", "").strip(),
                        url=item.get("url", ""),
                        domain=item.get("domain", ""),
                        seen_date=seen_dt,
                        language=item.get("language", ""),
                        source_country=item.get("sourcecountry", ""),
                    )
                )
            except (ValueError, KeyError) as exc:
                logger.debug("Skipping malformed article: %s", exc)
                continue
        return articles
