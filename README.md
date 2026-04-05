# Gold Price Tracker

Real-time gold market value dashboard built with Python, Dash and Plotly.

## Features

- Live candlestick chart (XAU/USD) powered by Yahoo Finance
- KPI cards: current price, period change, high and low
- Selectable time periods: 1 Day · 1 Week · 1 Month · 1 Year
- Auto-refresh every 60 seconds (configurable)
- Dark theme, responsive layout

## Project Structure

```
proyecto/
├── assets/
│   └── style.css          # Global styles (auto-loaded by Dash)
├── src/
│   ├── config.py           # Environment-based configuration
│   ├── data/
│   │   └── fetcher.py      # Gold price data layer (yfinance)
│   └── dashboard/
│       ├── app.py          # Dash app factory
│       ├── layout.py       # UI layout definition
│       └── callbacks.py    # Reactive callbacks
├── main.py                 # Entry point
├── requirements.txt
├── .env.example
└── .gitignore
```

## Getting Started

```bash
# 1. Clone the repository
git clone <repo-url>
cd proyecto

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env as needed

# 5. Run the app
python main.py
```

Open your browser at **http://127.0.0.1:8050**

## Configuration

| Variable           | Default       | Description                     |
|--------------------|---------------|---------------------------------|
| `APP_HOST`         | `127.0.0.1`   | Server bind address             |
| `APP_PORT`         | `8050`        | Server port                     |
| `DEBUG`            | `True`        | Enable Dash debug mode          |
| `REFRESH_INTERVAL` | `60`          | Auto-refresh interval (seconds) |

## Data Source

Gold futures data (`GC=F`) retrieved from **Yahoo Finance** via `yfinance`.  
Data has an approximate 15-minute delay; no API key required.

## Roadmap

- [ ] Phase 2: AI-powered analysis — correlate gold price movements with real-world news events
