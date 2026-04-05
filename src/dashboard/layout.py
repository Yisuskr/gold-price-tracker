"""
Dashboard layout builder.

Defines the visual structure of the Dash application:
header, KPI cards, the price chart, period/currency controls,
and the AI analysis side panel.
"""

from dash import dcc, html


def build_layout(refresh_interval_ms: int, ai_refresh_interval_ms: int) -> html.Div:
    """
    Construct and return the full page layout.

    Args:
        refresh_interval_ms:    Price chart auto-refresh in milliseconds.
        ai_refresh_interval_ms: AI panel auto-refresh in milliseconds.
    """
    return html.Div(
        id="app-container",
        children=[
            # ── Header ────────────────────────────────────────────────────────
            html.Div(
                className="header",
                children=[
                    html.H1("Gold Price Tracker", className="header-title"),
                    html.P(
                        id="header-subtitle",
                        className="header-subtitle",
                        children="Real-time gold market value (XAU/USD)",
                    ),
                ],
            ),

            # ── KPI Cards ─────────────────────────────────────────────────────
            html.Div(
                className="kpi-row",
                children=[
                    _kpi_card("current-price", "Current Price", "kpi-unit-price"),
                    _kpi_card("price-change", "Change (Period)", "%"),
                    _kpi_card("price-high", "Period High", "kpi-unit-high"),
                    _kpi_card("price-low", "Period Low", "kpi-unit-low"),
                ],
            ),

            # ── Controls row ──────────────────────────────────────────────────
            html.Div(
                className="controls",
                children=[
                    html.Span("Period:", className="controls-label"),
                    dcc.RadioItems(
                        id="period-selector",
                        options=[
                            {"label": "1 Day", "value": "1d"},
                            {"label": "1 Week", "value": "5d"},
                            {"label": "1 Month", "value": "1mo"},
                            {"label": "1 Year", "value": "1y"},
                        ],
                        value="1mo",
                        inline=True,
                        className="period-radio",
                    ),
                    html.Span(className="controls-spacer"),
                    html.Span("Currency:", className="controls-label"),
                    dcc.RadioItems(
                        id="currency-selector",
                        options=[
                            {"label": "USD ($)", "value": "USD"},
                            {"label": "EUR (€)", "value": "EUR"},
                        ],
                        value="USD",
                        inline=True,
                        className="currency-radio",
                    ),
                ],
            ),

            # ── Main content: chart + AI panel ────────────────────────────────
            html.Div(
                className="main-content",
                children=[
                    # Left: price chart
                    html.Div(
                        className="chart-container",
                        children=[
                            dcc.Graph(
                                id="gold-price-chart",
                                config={"displayModeBar": True, "scrollZoom": True},
                            )
                        ],
                    ),

                    # Right: AI analysis panel
                    html.Div(
                        className="ai-panel",
                        children=[
                            html.Div(
                                className="ai-panel-header",
                                children=[
                                    html.H3("AI Analysis", className="ai-panel-title"),
                                    html.Button(
                                        "Refresh",
                                        id="ai-refresh-btn",
                                        className="ai-refresh-btn",
                                        n_clicks=0,
                                    ),
                                ],
                            ),

                            # Signal badge (BULLISH / BEARISH / NEUTRAL)
                            html.Div(id="ai-signal-badge", className="ai-signal-badge"),

                            # Confidence bar
                            html.Div(
                                className="ai-confidence-row",
                                children=[
                                    html.Span("Confidence", className="ai-label"),
                                    html.Div(
                                        className="ai-confidence-bar-bg",
                                        children=[
                                            html.Div(
                                                id="ai-confidence-bar",
                                                className="ai-confidence-bar-fill",
                                            )
                                        ],
                                    ),
                                    html.Span(
                                        id="ai-confidence-pct", className="ai-label"
                                    ),
                                ],
                            ),

                            # Technical indicators snapshot
                            html.Div(id="ai-indicators", className="ai-indicators"),

                            # Gemini narrative
                            html.Div(
                                className="ai-section",
                                children=[
                                    html.P("Analysis", className="ai-section-title"),
                                    html.P(
                                        id="ai-summary", className="ai-summary-text"
                                    ),
                                ],
                            ),

                            # Technical signal bullets
                            html.Div(
                                className="ai-section",
                                children=[
                                    html.P(
                                        "Technical Signals",
                                        className="ai-section-title",
                                    ),
                                    html.Ul(
                                        id="ai-technical-reasons",
                                        className="ai-reasons-list",
                                    ),
                                ],
                            ),

                            # News correlation bullets
                            html.Div(
                                className="ai-section",
                                children=[
                                    html.P(
                                        "News Correlations",
                                        className="ai-section-title",
                                    ),
                                    html.Ul(
                                        id="ai-news-reasons",
                                        className="ai-reasons-list",
                                    ),
                                ],
                            ),

                            # Related article links
                            html.Div(
                                className="ai-section",
                                children=[
                                    html.P(
                                        "Related News", className="ai-section-title"
                                    ),
                                    html.Div(
                                        id="ai-articles", className="ai-articles"
                                    ),
                                ],
                            ),

                            html.P(id="ai-generated-at", className="ai-timestamp"),

                            # Loading spinner
                            dcc.Loading(
                                id="ai-loading",
                                type="circle",
                                color="#f9e2af",
                                children=html.Div(id="ai-loading-output"),
                            ),
                        ],
                    ),
                ],
            ),

            # ── Intervals ─────────────────────────────────────────────────────
            dcc.Interval(
                id="interval-component",
                interval=refresh_interval_ms,
                n_intervals=0,
            ),
            dcc.Interval(
                id="ai-interval-component",
                interval=ai_refresh_interval_ms,
                n_intervals=0,
            ),

            # ── Last updated timestamp ────────────────────────────────────────
            html.Div(id="last-updated", className="last-updated"),
        ],
    )


def _kpi_card(card_id: str, title: str, unit_id: str) -> html.Div:
    """Return a single KPI card component."""
    return html.Div(
        className="kpi-card",
        children=[
            html.P(title, className="kpi-title"),
            html.H2(id=card_id, className="kpi-value", children="--"),
            html.Span(id=unit_id, className="kpi-unit", children=""),
        ],
    )
