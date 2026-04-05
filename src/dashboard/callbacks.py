"""
Dashboard callbacks.

All Dash reactive callbacks live here, keeping them separated
from layout definitions and data-fetching logic.

Two independent callback groups:
  1. Price chart callbacks  — triggered by interval / period / currency changes.
  2. AI analysis callbacks  — triggered by AI interval or the Refresh button.
"""

import logging
from datetime import datetime
from typing import Any

import plotly.graph_objects as go
from dash import Input, Output, no_update
from dash.exceptions import PreventUpdate

from src.ai.analyzer import GoldAnalyzer
from src.ai.cache import SignalCache
from src.ai.signal import GoldSignal, SignalDirection
from src.data.fetcher import ExchangeRateFetcher, GoldDataFetcher

logger = logging.getLogger(__name__)

# module-level fetchers — reused across callbacks to avoid rebuilding on every refresh
_fetcher = GoldDataFetcher()
_fx = ExchangeRateFetcher()

# maps period selector values to the right fetcher method
_PERIOD_MAP = {
    "1d": _fetcher.get_intraday_data,
    "5d": _fetcher.get_weekly_data,
    "1mo": _fetcher.get_monthly_data,
    "1y": _fetcher.get_yearly_data,
}

_PERIOD_LABELS = {
    "1d": "Today",
    "5d": "Last 5 Days",
    "1mo": "Last Month",
    "1y": "Last Year",
}

_CURRENCY_SYMBOL = {"USD": "$", "EUR": "€"}
_CURRENCY_LABEL = {"USD": "USD/oz", "EUR": "EUR/oz"}

# badge colours match the Catppuccin Mocha palette used in style.css
_SIGNAL_COLOR = {
    SignalDirection.BULLISH: "#26a69a",
    SignalDirection.BEARISH: "#ef5350",
    SignalDirection.NEUTRAL: "#f9e2af",
}


def register_callbacks(app: Any, gemini_api_key: str, ai_cache_ttl: int) -> None:
    """
    Register all Dash callbacks onto the given app instance.

    Args:
        app:             Dash application instance.
        gemini_api_key:  Key for the Gemini API.
        ai_cache_ttl:    Cache TTL in seconds for AI analysis results.
    """
    # created here so each app instance gets its own analyzer and cache
    _analyzer = GoldAnalyzer(gemini_api_key=gemini_api_key)
    _cache = SignalCache(ttl_seconds=ai_cache_ttl)

    # ── 1. Price chart callback ───────────────────────────────────────────

    @app.callback(
        Output("gold-price-chart", "figure"),
        Output("current-price", "children"),
        Output("price-change", "children"),
        Output("price-high", "children"),
        Output("price-low", "children"),
        Output("kpi-unit-price", "children"),
        Output("kpi-unit-high", "children"),
        Output("kpi-unit-low", "children"),
        Output("header-subtitle", "children"),
        Output("last-updated", "children"),
        Input("interval-component", "n_intervals"),
        Input("period-selector", "value"),
        Input("currency-selector", "value"),
    )
    def update_price_chart(n_intervals: int, period: str, currency: str) -> tuple:
        """Fetch fresh price data and refresh the chart and KPI cards."""
        fetch_fn = _PERIOD_MAP.get(period, _fetcher.get_monthly_data)
        df = fetch_fn()

        if df.empty:
            raise PreventUpdate

        # apply USD→EUR conversion if needed; rate is 1.0 for USD so it's a no-op
        rate = _fx.get_usd_to_eur() if currency == "EUR" else 1.0
        df_conv = df.copy()
        for col in ("Open", "High", "Low", "Close"):
            df_conv[col] = df_conv[col] * rate

        close = df_conv["Close"]
        current = close.iloc[-1]
        high = close.max()
        low = close.min()
        change_pct = ((current - close.iloc[0]) / close.iloc[0]) * 100
        change_sign = "+" if change_pct >= 0 else ""

        symbol = _CURRENCY_SYMBOL[currency]
        unit = _CURRENCY_LABEL[currency]
        subtitle = f"Real-time gold market value (XAU/{currency})"

        fig = _build_candlestick_chart(df_conv, period, symbol, currency)
        timestamp = datetime.now().strftime("Last updated: %Y-%m-%d %H:%M:%S")

        return (
            fig,
            f"{symbol}{current:,.2f}",
            f"{change_sign}{change_pct:.2f}%",
            f"{symbol}{high:,.2f}",
            f"{symbol}{low:,.2f}",
            unit,
            unit,
            unit,
            subtitle,
            timestamp,
        )

    # ── 2. AI analysis callback ───────────────────────────────────────────

    @app.callback(
        Output("ai-signal-badge", "children"),
        Output("ai-signal-badge", "style"),
        Output("ai-confidence-bar", "style"),
        Output("ai-confidence-pct", "children"),
        Output("ai-indicators", "children"),
        Output("ai-summary", "children"),
        Output("ai-technical-reasons", "children"),
        Output("ai-news-reasons", "children"),
        Output("ai-articles", "children"),
        Output("ai-generated-at", "children"),
        Output("ai-loading-output", "children"),
        Input("ai-interval-component", "n_intervals"),
        Input("ai-refresh-btn", "n_clicks"),
    )
    def update_ai_panel(n_intervals: int, n_clicks: int) -> tuple:
        """
        Run (or serve from cache) the AI analysis and update the side panel.

        The Refresh button invalidates the cache and forces a fresh Gemini call.
        Automatic timer refreshes serve the cached result if it hasn't expired,
        keeping us well within Gemini's free-tier quota.
        """
        # manual refresh: invalidate cache so the next read triggers a fresh Gemini call
        if n_clicks and n_clicks > 0:
            _cache.invalidate()

        signal = _cache.get()
        if signal is None:
            logger.info("Cache miss — running full AI analysis")
            signal = _analyzer.analyze()
            _cache.set(signal)

        return _render_ai_panel(signal)


def _render_ai_panel(signal: GoldSignal) -> tuple:
    """Convert a GoldSignal into the tuple of Dash component outputs."""
    from dash import html

    color = _SIGNAL_COLOR.get(signal.direction, "#f9e2af")

    # if something went wrong, show a grey UNAVAILABLE badge instead
    badge_text = signal.direction.value
    if signal.error:
        badge_text = "UNAVAILABLE"
        color = "#6c7086"

    badge_style = {
        "backgroundColor": color,
        "color": "#181825",
        "padding": "10px 20px",
        "borderRadius": "8px",
        "fontWeight": "700",
        "fontSize": "1.1rem",
        "textAlign": "center",
        "marginBottom": "12px",
        "letterSpacing": "0.08em",
    }

    conf_pct = signal.confidence_pct
    bar_style = {
        "width": f"{conf_pct}%",
        "backgroundColor": color,
        "height": "100%",
        "borderRadius": "4px",
        "transition": "width 0.5s ease",
    }

    # RSI chips coloured by zone, trend arrow, volatility %, MA cross label
    indicator_chips = []
    if signal.rsi is not None:
        rsi_color = (
            "#ef5350" if signal.rsi > 70    # overbought
            else "#26a69a" if signal.rsi < 30  # oversold
            else "#f9e2af"                      # neutral zone
        )
        indicator_chips.append(
            html.Span(
                f"RSI {signal.rsi:.0f}",
                className="ai-chip",
                style={"color": rsi_color},
            )
        )
    if signal.trend:
        icon = "↑" if signal.trend == "UP" else "↓" if signal.trend == "DOWN" else "→"
        indicator_chips.append(html.Span(f"Trend {icon}", className="ai-chip"))
    if signal.volatility_pct is not None:
        indicator_chips.append(
            html.Span(f"Vol {signal.volatility_pct:.2f}%", className="ai-chip")
        )
    if signal.ma50_vs_ma200 and signal.ma50_vs_ma200 != "NEUTRAL":
        ma_color = "#26a69a" if signal.ma50_vs_ma200 == "GOLDEN_CROSS" else "#ef5350"
        indicator_chips.append(
            html.Span(
                signal.ma50_vs_ma200.replace("_", " "),
                className="ai-chip",
                style={"color": ma_color},
            )
        )

    tech_items = [html.Li(r) for r in signal.technical_reasons] or [html.Li("—")]
    news_items = [html.Li(r) for r in signal.news_reasons] or [html.Li("—")]

    article_links = [
        html.A(
            art.get("title", art.get("domain", "Article")),
            href=art.get("url", "#"),
            target="_blank",
            className="ai-article-link",
        )
        for art in signal.related_articles
    ]

    ts = signal.generated_at.strftime("Analysis at %Y-%m-%d %H:%M UTC")
    summary = signal.gemini_summary or signal.error or "No analysis available."

    return (
        badge_text,
        badge_style,
        bar_style,
        f"{conf_pct}%",
        indicator_chips,
        summary,
        tech_items,
        news_items,
        article_links,
        ts,
        "",  # clears the dcc.Loading spinner placeholder
    )


def _build_candlestick_chart(
    df: Any, period: str, symbol: str, currency: str
) -> go.Figure:
    """Build a candlestick chart with a volume subplot below it."""
    from plotly.subplots import make_subplots

    # 75% price / 25% volume — shared x-axis keeps both panels in sync
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=f"XAU/{currency}",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    # colour each volume bar green or red to match its candle
    colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.6,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title={
            "text": f"Gold (XAU/{currency}) — {_PERIOD_LABELS.get(period, period)}",
            "x": 0.5,
            "xanchor": "center",
        },
        paper_bgcolor="#1e1e2e",
        plot_bgcolor="#1e1e2e",
        font={"color": "#cdd6f4"},
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "y": 1.02},
        margin={"l": 60, "r": 30, "t": 60, "b": 20},
        hovermode="x unified",
        yaxis_tickprefix=symbol,
        yaxis_tickformat=",.2f",
    )

    fig.update_xaxes(gridcolor="#313244", showgrid=True, zeroline=False)
    fig.update_yaxes(gridcolor="#313244", showgrid=True, zeroline=False)

    return fig
