"""Dash callbacks: data refresh, tab rendering, interactivity."""

from datetime import datetime

from dash import html, Input, Output, State, callback, dcc, no_update
import dash_bootstrap_components as dbc

from config import TICKERS
from sentiment.composite import compute_all_summaries, compute_composite
from sentiment.market_sentiment import compute_fear_greed_proxy, interpret_vix
from data.market_data import get_price_history, get_current_quote
from dashboard.components import (
    category_summary_card,
    fear_greed_gauge,
    signal_gauge,
    price_chart,
    rsi_chart,
    news_panel,
    indicators_table,
    signal_card,
)


def register_callbacks(app):
    """Register all Dash callbacks."""

    # ── Data refresh → store ─────────────────────────────────────────
    @app.callback(
        Output("summaries-store", "data"),
        [
            Input("fast-refresh", "n_intervals"),
            Input("manual-refresh", "n_clicks"),
        ],
    )
    def refresh_data(_n_intervals, _n_clicks):
        try:
            return compute_all_summaries()
        except Exception as e:
            print(f"Error refreshing data: {e}")
            return {}

    # ── Header stats ─────────────────────────────────────────────────
    @app.callback(
        Output("header-stats", "children"),
        Input("summaries-store", "data"),
    )
    def update_header(summaries):
        if not summaries:
            return "Loading..."

        try:
            vix = interpret_vix()
            fg = compute_fear_greed_proxy()

            vix_val = vix.get("raw", "—")
            vix_chg = vix.get("change_pct", 0)
            vix_color = "#ff8a65" if vix.get("zone") in ("elevated", "extreme_fear") else "#69f0ae"

            fg_val = fg.get("value", 50)
            fg_label = fg.get("label", "Neutral")
            fg_color = "#ff1744" if fg_val < 35 else "#00c853" if fg_val > 65 else "#ffd740"

            now = datetime.now().strftime("%H:%M UTC")

            return html.Span(
                [
                    html.Span(f"Fear & Greed: {fg_val:.0f} ", style={"color": fg_color}),
                    html.Span(f"({fg_label})", style={"color": "#888"}),
                    html.Span(" | ", style={"color": "#444"}),
                    html.Span(f"VIX: {vix_val} ", style={"color": vix_color}),
                    html.Span(f"({vix_chg:+.1f}%)" if vix_chg else "", style={"color": "#888"}),
                    html.Span(" | ", style={"color": "#444"}),
                    html.Span(f"Updated: {now}", style={"color": "#666"}),
                ]
            )
        except Exception:
            return "Data loading..."

    # ── Tab content rendering ────────────────────────────────────────
    @app.callback(
        Output("tab-content", "children"),
        [Input("main-tabs", "active_tab"), Input("summaries-store", "data")],
    )
    def render_tab(active_tab, summaries):
        if not summaries:
            return dbc.Alert("Loading data... This may take a moment on first load.", color="info")

        if active_tab == "tab-overview":
            return _render_overview(summaries)
        elif active_tab == "tab-sp500":
            return _render_sp500(summaries)
        elif active_tab == "tab-oil-gas":
            return _render_stub("Oil & Gas", summaries.get("oil_gas", {}))
        elif active_tab == "tab-gold":
            return _render_stub("Gold", summaries.get("gold", {}))
        elif active_tab == "tab-defense":
            return _render_stub("EU Defense", summaries.get("defense", {}))
        elif active_tab == "tab-fx":
            return _render_stub("FX Rates", summaries.get("fx", {}))

        return html.Div("Select a tab")


def _render_overview(summaries: dict):
    """Render the Overview tab with category summary cards and fear/greed gauge."""
    # Category cards
    cards = []
    for cat_key in ["sp500", "oil_gas", "gold", "defense", "fx"]:
        cat_data = summaries.get(cat_key, {})
        if cat_data:
            cards.append(dbc.Col(category_summary_card(cat_data), md=2, sm=4, xs=6))

    # Fear & Greed gauge
    fg = compute_fear_greed_proxy()

    # Ticker heatmap rows
    heatmap_rows = []
    for cat_key, cat_data in summaries.items():
        tickers = cat_data.get("tickers", {})
        for ticker, data in tickers.items():
            score = data.get("composite_score", 0)
            signal = data.get("signal", "NEUTRAL")
            color = data.get("signal_color", "#ffd740")
            tech = data.get("components", {}).get("technical", {})
            rsi_val = tech.get("detail", {}).get("rsi", {}).get("raw", "—")
            news_score = data.get("components", {}).get("news_sentiment", {}).get("score", 0)

            heatmap_rows.append(
                html.Tr(
                    [
                        html.Td(ticker, style={"color": "#ccc", "fontWeight": "bold"}),
                        html.Td(
                            TICKERS.get(cat_key, {}).get("symbols", {}).get(ticker, ""),
                            style={"color": "#888"},
                        ),
                        html.Td(str(rsi_val), style={"color": "#aaa"}),
                        html.Td(f"{news_score:+.2f}", style={"color": "#aaa"}),
                        html.Td(
                            signal,
                            style={"color": color, "fontWeight": "bold"},
                        ),
                        html.Td(f"{score:+.3f}", style={"color": color}),
                    ]
                )
            )

    heatmap_table = dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Ticker", style={"color": "#888"}),
                        html.Th("Name", style={"color": "#888"}),
                        html.Th("RSI", style={"color": "#888"}),
                        html.Th("News", style={"color": "#888"}),
                        html.Th("Signal", style={"color": "#888"}),
                        html.Th("Score", style={"color": "#888"}),
                    ]
                )
            ),
            html.Tbody(heatmap_rows),
        ],
        bordered=False,
        dark=True,
        hover=True,
        responsive=True,
        size="sm",
        style={"backgroundColor": "transparent"},
    )

    return html.Div(
        [
            # Summary cards row
            dbc.Row(cards, className="mb-4 g-3"),

            # Fear & Greed + signal heatmap
            dbc.Row(
                [
                    dbc.Col(
                        fear_greed_gauge(fg.get("value", 50), fg.get("label", "Neutral")),
                        md=4,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    "All Signals",
                                    style={"backgroundColor": "#16162a", "color": "#aaa"},
                                ),
                                dbc.CardBody(
                                    heatmap_table,
                                    style={"maxHeight": "400px", "overflowY": "auto"},
                                ),
                            ],
                            style={"backgroundColor": "#1e1e2f", "border": "1px solid #333"},
                        ),
                        md=8,
                    ),
                ],
                className="mb-4",
            ),
        ]
    )


def _render_sp500(summaries: dict):
    """Render the full S&P & Indices tab."""
    cat_data = summaries.get("sp500", {})
    tickers_data = cat_data.get("tickers", {})

    # Default to SPY for the main chart
    default_ticker = "SPY"
    spy_data = tickers_data.get(default_ticker, {})
    spy_tech = spy_data.get("components", {}).get("technical", {}).get("detail", {})
    spy_news = spy_data.get("components", {}).get("news_sentiment", {}).get("detail", {})

    # Price chart
    df = get_price_history(default_ticker, period="6mo")
    main_chart = price_chart(df, default_ticker, "S&P 500 ETF")
    rsi_subplot = rsi_chart(df, default_ticker)

    # Signal cards for key indices
    index_cards = []
    for ticker in ["^GSPC", "SPY", "^DJI", "^IXIC", "^RUT"]:
        data = tickers_data.get(ticker, {})
        if data:
            name = TICKERS["sp500"]["symbols"].get(ticker, ticker)
            index_cards.append(dbc.Col(signal_card(ticker, name, data), lg=2, md=4, sm=6))

    # VIX card
    vix_data = tickers_data.get("^VIX", {})
    vix_quote = get_current_quote("^VIX")
    vix_card = dbc.Card(
        dbc.CardBody(
            [
                html.H5("VIX", style={"color": "#ccc"}),
                html.H2(
                    f"{vix_quote.get('price', '—'):.1f}" if vix_quote.get("price") else "—",
                    style={
                        "color": "#ff8a65"
                        if (vix_quote.get("price") or 0) > 20
                        else "#69f0ae"
                    },
                ),
                html.P(
                    f"{vix_quote.get('change_pct', 0):+.1f}%",
                    style={"color": "#aaa"},
                ),
            ],
            className="text-center",
        ),
        style={"backgroundColor": "#1e1e2f", "border": "1px solid #555"},
    )

    # News articles
    articles = spy_news.get("articles", []) if isinstance(spy_news, dict) else []

    return html.Div(
        [
            # Signal cards row
            dbc.Row(index_cards, className="mb-3 g-2"),

            # Main content
            dbc.Row(
                [
                    # Chart column
                    dbc.Col(
                        [
                            main_chart,
                            rsi_subplot,
                        ],
                        md=8,
                    ),
                    # Sidebar
                    dbc.Col(
                        [
                            # Composite gauge
                            signal_gauge(
                                spy_data.get("composite_score", 0),
                                "SPY Composite Signal",
                            ),
                            html.Hr(style={"borderColor": "#333"}),
                            # VIX
                            vix_card,
                            html.Hr(style={"borderColor": "#333"}),
                            # Indicators table
                            html.H6("Technical Indicators", style={"color": "#aaa"}),
                            indicators_table(spy_tech) if spy_tech else html.P("Loading..."),
                        ],
                        md=4,
                    ),
                ],
                className="mb-3",
            ),

            # News row
            dbc.Row(
                dbc.Col(news_panel(articles)),
                className="mb-3",
            ),
        ]
    )


def _render_stub(title: str, cat_data: dict):
    """Render a stub tab for categories not yet fully built."""
    tickers_data = cat_data.get("tickers", {})

    cards = []
    for ticker, data in tickers_data.items():
        cat_key = cat_data.get("category", "")
        cat_symbols = TICKERS.get(cat_key, {}).get("symbols", {})
        name = cat_symbols.get(ticker, ticker)
        cards.append(dbc.Col(signal_card(ticker, name, data), lg=3, md=4, sm=6))

    # Show a chart for the first ticker
    first_ticker = next(iter(tickers_data), None)
    chart = html.Div()
    if first_ticker:
        df = get_price_history(first_ticker, period="6mo")
        cat_symbols = TICKERS.get(cat_data.get("category", ""), {}).get("symbols", {})
        name = cat_symbols.get(first_ticker, first_ticker)
        chart = price_chart(df, first_ticker, name)

    # News
    news_data = (
        list(tickers_data.values())[0]
        .get("components", {})
        .get("news_sentiment", {})
        .get("detail", {})
        if tickers_data
        else {}
    )
    articles = news_data.get("articles", []) if isinstance(news_data, dict) else []

    return html.Div(
        [
            html.H4(title, style={"color": "white", "marginBottom": "15px"}),
            # Summary gauge
            signal_gauge(
                cat_data.get("avg_score", 0),
                f"{title} Composite",
            ),
            # Signal cards
            dbc.Row(cards, className="mb-3 g-2"),
            # Chart
            chart,
            # News
            dbc.Row(dbc.Col(news_panel(articles)), className="mt-3"),
        ]
    )
