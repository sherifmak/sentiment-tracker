"""Dash layout: header bar + 6 tabs."""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_layout() -> dbc.Container:
    """Build the full dashboard layout."""
    return dbc.Container(
        [
            # Auto-refresh intervals
            dcc.Interval(id="fast-refresh", interval=5 * 60 * 1000, n_intervals=0),
            dcc.Interval(id="slow-refresh", interval=60 * 60 * 1000, n_intervals=0),

            # Hidden data stores
            dcc.Store(id="summaries-store", data={}),

            # ── Top Bar ──────────────────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        html.H3(
                            "SENTIMENT TRACKER",
                            style={"fontWeight": "bold", "letterSpacing": "2px"},
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        html.Div(id="header-stats", style={"color": "#aaa"}),
                        className="d-flex align-items-center",
                    ),
                    dbc.Col(
                        dbc.Button(
                            "Refresh",
                            id="manual-refresh",
                            color="secondary",
                            size="sm",
                            outline=True,
                        ),
                        width="auto",
                        className="d-flex align-items-center",
                    ),
                ],
                className="py-3 px-2 mb-3",
                style={
                    "backgroundColor": "#12122a",
                    "borderRadius": "8px",
                    "border": "1px solid #333",
                },
            ),

            # ── Tabs ─────────────────────────────────────────────────────
            dbc.Tabs(
                [
                    dbc.Tab(label="Overview", tab_id="tab-overview"),
                    dbc.Tab(label="S&P & Indices", tab_id="tab-sp500"),
                    dbc.Tab(label="Oil & Gas", tab_id="tab-oil-gas"),
                    dbc.Tab(label="Gold", tab_id="tab-gold"),
                    dbc.Tab(label="EU Defense", tab_id="tab-defense"),
                    dbc.Tab(label="FX Rates", tab_id="tab-fx"),
                ],
                id="main-tabs",
                active_tab="tab-overview",
                className="mb-3",
            ),

            # ── Tab Content ──────────────────────────────────────────────
            html.Div(id="tab-content"),

            # ── Footer ───────────────────────────────────────────────────
            html.Hr(style={"borderColor": "#333"}),
            html.P(
                "Data: yfinance | Sentiment: GDELT + TextBlob | Not financial advice",
                style={"color": "#555", "fontSize": "0.75rem", "textAlign": "center"},
            ),
        ],
        fluid=True,
        style={"maxWidth": "1400px"},
    )
