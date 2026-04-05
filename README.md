# Gold Price Tracker

Real-time gold market dashboard with AI-powered analysis, built with Python, Dash and Google Gemini.

## Features

- Live candlestick chart (XAU/USD or XAU/EUR) powered by Yahoo Finance
- KPI cards: current price, period change, high and low
- Selectable time periods: 1 Day · 1 Week · 1 Month · 1 Year
- USD / EUR currency toggle with live exchange rate
- Auto-refresh every 60 seconds (configurable)
- **AI analysis panel** — BULLISH / BEARISH / NEUTRAL signal with confidence score
- Technical indicators: RSI-14, ATR-20 volatility, SMA-50/200, trend direction
- News correlation via GDELT Project — geopolitical and economic headlines
- Google Gemini 2.0 Flash generates a plain-English market narrative
- Result cache (30 min TTL) to stay within Gemini free-tier quota
- Dark theme (Catppuccin Mocha palette)

## Project Structure

```
gold-price-tracker/
├── assets/
│   └── style.css               # global styles (auto-loaded by Dash)
├── src/
│   ├── config.py               # environment-based configuration
│   ├── data/
│   │   └── fetcher.py          # gold price + exchange rate (yfinance)
│   ├── news/
│   │   └── fetcher.py          # GDELT news fetcher
│   ├── ai/
│   │   ├── analyzer.py         # technical indicators + Gemini call
│   │   ├── cache.py            # file-backed signal cache with TTL
│   │   └── signal.py           # GoldSignal dataclass
│   └── dashboard/
│       ├── app.py              # Dash app factory
│       ├── layout.py           # UI layout
│       └── callbacks.py        # reactive callbacks
├── main.py                     # entry point
├── requirements.txt
├── .env.example
└── .gitignore
```

## Getting Started

```bash
# 1. Clone the repository
git clone git@github.com:Yisuskr/gold-price-tracker.git
cd gold-price-tracker

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# 5. Run the app
python main.py
```

Open your browser at **http://127.0.0.1:8050**

## Configuration

| Variable                  | Default     | Description                                  |
|---------------------------|-------------|----------------------------------------------|
| `APP_HOST`                | `127.0.0.1` | Server bind address                          |
| `APP_PORT`                | `8050`      | Server port                                  |
| `DEBUG`                   | `True`      | Enable Dash debug mode                       |
| `REFRESH_INTERVAL`        | `60`        | Price chart auto-refresh (seconds)           |
| `GEMINI_API_KEY`          | —           | Google Gemini API key (required for AI)      |
| `AI_REFRESH_INTERVAL`     | `1800`      | AI analysis cache TTL (seconds)              |
| `AI_CONFIDENCE_THRESHOLD` | `0.4`       | Minimum confidence to show directional signal|

## Data Sources

- **Gold price:** `GC=F` futures from Yahoo Finance via `yfinance` — ~15 min delay, no API key needed
- **News:** [GDELT Project DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) — free, no API key needed
- **AI:** Google Gemini 2.0 Flash — free tier (1,500 requests/day)
