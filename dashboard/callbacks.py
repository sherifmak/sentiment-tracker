"""Dash callbacks: data refresh, tab rendering, interactivity."""

from datetime import datetime

from dash import html, Input, Output, dcc
import dash_bootstrap_components as dbc

from config import TICKERS
from sentiment.composite import compute_all_summaries, compute_composite
from sentiment.market_sentiment import compute_fear_greed_proxy, interpret_vix
from data.market_data import get_price_history, get_current_quote
from data.market_data import get_batch_quotes
from dashboard.components import (
    category_summary_card,
    comparison_chart,
    daily_change_heatmap,
    fear_greed_gauge,
    fx_rate_table,
    indicators_table,
    news_panel,
    price_chart,
    price_table,
    rsi_chart,
    signal_card,
    signal_gauge,
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

        renderers = {
            "tab-overview": lambda: _render_overview(summaries),
            "tab-sp500": lambda: _render_sp500(summaries),
            "tab-oil-gas": lambda: _render_oil_gas(summaries),
            "tab-gold": lambda: _render_gold(summaries),
            "tab-defense": lambda: _render_defense(summaries),
            "tab-fx": lambda: _render_fx(summaries),
        }
        renderer = renderers.get(active_tab)
        return renderer() if renderer else html.Div("Select a tab")


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


def _get_cat_news(tickers_data: dict) -> list[dict]:
    """Extract news articles from the first ticker in a category."""
    if not tickers_data:
        return []
    first = next(iter(tickers_data.values()), {})
    detail = first.get("components", {}).get("news_sentiment", {}).get("detail", {})
    return detail.get("articles", []) if isinstance(detail, dict) else []


def _render_oil_gas(summaries: dict):
    """Full Oil & Gas tab: crude chart, XLE chart, comparison, signals, news."""
    cat_data = summaries.get("oil_gas", {})
    tickers_data = cat_data.get("tickers", {})
    symbols = TICKERS["oil_gas"]["symbols"]

    # Signal cards
    cards = []
    for ticker in ["XLE", "CL=F", "BZ=F", "NG=F", "USO"]:
        data = tickers_data.get(ticker, {})
        if data:
            cards.append(dbc.Col(signal_card(ticker, symbols.get(ticker, ticker), data), lg=2, md=4, sm=6))

    # Main chart: WTI Crude
    crude_ticker = "CL=F"
    df_crude = get_price_history(crude_ticker, period="6mo")
    crude_chart = price_chart(df_crude, crude_ticker, "WTI Crude Oil")
    crude_rsi = rsi_chart(df_crude, crude_ticker)

    # Comparison chart: XLE vs crude vs brent normalized
    comp_data = {}
    for t in ["XLE", "CL=F", "BZ=F"]:
        df = get_price_history(t, period="6mo")
        comp_data[t] = (symbols.get(t, t), df)
    comp = comparison_chart(comp_data, "Energy: XLE vs Crude vs Brent (% Change)", normalize=True)

    # XLE technical detail
    xle_data = tickers_data.get("XLE", {})
    xle_tech = xle_data.get("components", {}).get("technical", {}).get("detail", {})

    return html.Div([
        # Signal cards
        dbc.Row(cards, className="mb-3 g-2"),

        dbc.Row([
            # Charts
            dbc.Col([crude_chart, crude_rsi], md=8),
            # Sidebar
            dbc.Col([
                signal_gauge(cat_data.get("avg_score", 0), "Oil & Gas Composite"),
                html.Hr(style={"borderColor": "#333"}),
                html.H6("XLE Technical Indicators", style={"color": "#aaa"}),
                indicators_table(xle_tech) if xle_tech else html.P("Loading...", style={"color": "#888"}),
            ], md=4),
        ], className="mb-3"),

        # Comparison chart
        comp,

        # Prices table
        dbc.Row(dbc.Col([
            html.H6("All Energy Tickers", style={"color": "#aaa", "marginTop": "15px"}),
            price_table(tickers_data, symbols),
        ]), className="mb-3"),

        # News
        dbc.Row(dbc.Col(news_panel(_get_cat_news(tickers_data))), className="mb-3"),
    ])


def _render_gold(summaries: dict):
    """Full Gold tab: futures chart, ETF comparison, signals, news."""
    cat_data = summaries.get("gold", {})
    tickers_data = cat_data.get("tickers", {})
    symbols = TICKERS["gold"]["symbols"]

    # Signal cards
    cards = []
    for ticker in ["GC=F", "GLD", "IAU", "SI=F"]:
        data = tickers_data.get(ticker, {})
        if data:
            cards.append(dbc.Col(signal_card(ticker, symbols.get(ticker, ticker), data), lg=3, md=4, sm=6))

    # Main chart: Gold Futures
    gold_ticker = "GC=F"
    df_gold = get_price_history(gold_ticker, period="6mo")
    gold_chart = price_chart(df_gold, gold_ticker, "Gold Futures (GC=F)")
    gold_rsi = rsi_chart(df_gold, gold_ticker)

    # Comparison: Gold vs Silver normalized
    comp_data = {}
    for t in ["GC=F", "SI=F", "GLD"]:
        df = get_price_history(t, period="6mo")
        comp_data[t] = (symbols.get(t, t), df)
    comp = comparison_chart(comp_data, "Gold vs Silver vs GLD (% Change)", normalize=True)

    # Gold Futures technical detail
    gc_data = tickers_data.get("GC=F", {})
    gc_tech = gc_data.get("components", {}).get("technical", {}).get("detail", {})

    # Safe haven indicator: Gold vs S&P relative performance
    df_spy = get_price_history("SPY", period="3mo")
    safe_haven_text = ""
    if not df_gold.empty and not df_spy.empty and len(df_gold) > 20 and len(df_spy) > 20:
        gold_ret = (float(df_gold["Close"].iloc[-1]) / float(df_gold["Close"].iloc[-21]) - 1) * 100
        spy_ret = (float(df_spy["Close"].iloc[-1]) / float(df_spy["Close"].iloc[-21]) - 1) * 100
        if gold_ret > spy_ret + 2:
            safe_haven_text = f"Safe-haven demand HIGH: Gold {gold_ret:+.1f}% vs S&P {spy_ret:+.1f}% (20d)"
            sh_color = "#ffa726"
        elif gold_ret < spy_ret - 2:
            safe_haven_text = f"Risk-on mode: S&P {spy_ret:+.1f}% vs Gold {gold_ret:+.1f}% (20d)"
            sh_color = "#69f0ae"
        else:
            safe_haven_text = f"Balanced: Gold {gold_ret:+.1f}% vs S&P {spy_ret:+.1f}% (20d)"
            sh_color = "#aaa"
    else:
        sh_color = "#888"
        safe_haven_text = "Safe-haven data loading..."

    return html.Div([
        # Signal cards
        dbc.Row(cards, className="mb-3 g-2"),

        dbc.Row([
            dbc.Col([gold_chart, gold_rsi], md=8),
            dbc.Col([
                signal_gauge(cat_data.get("avg_score", 0), "Gold Composite"),
                html.Hr(style={"borderColor": "#333"}),
                # Safe haven indicator
                dbc.Card(
                    dbc.CardBody([
                        html.H6("Safe Haven Demand", style={"color": "#ccc"}),
                        html.P(safe_haven_text, style={"color": sh_color, "fontSize": "0.9rem"}),
                    ]),
                    style={"backgroundColor": "#1e1e2f", "border": "1px solid #555", "marginBottom": "15px"},
                ),
                html.H6("Gold Futures Technicals", style={"color": "#aaa"}),
                indicators_table(gc_tech) if gc_tech else html.P("Loading...", style={"color": "#888"}),
            ], md=4),
        ], className="mb-3"),

        comp,

        dbc.Row(dbc.Col([
            html.H6("All Gold/Silver Tickers", style={"color": "#aaa", "marginTop": "15px"}),
            price_table(tickers_data, symbols),
        ]), className="mb-3"),

        dbc.Row(dbc.Col(news_panel(_get_cat_news(tickers_data))), className="mb-3"),
    ])


def _render_defense(summaries: dict):
    """Full EU Defense tab: normalized comparison, per-stock signals, news."""
    cat_data = summaries.get("defense", {})
    tickers_data = cat_data.get("tickers", {})
    symbols = TICKERS["defense"]["symbols"]

    # Signal cards
    cards = []
    for ticker in symbols:
        data = tickers_data.get(ticker, {})
        if data:
            cards.append(dbc.Col(signal_card(ticker, symbols[ticker], data), lg=2, md=4, sm=6))

    # Normalized comparison chart (all 5 defense stocks)
    comp_data = {}
    for t in symbols:
        df = get_price_history(t, period="6mo")
        comp_data[t] = (symbols[t], df)
    comp = comparison_chart(comp_data, "EU Defense Stocks — Relative Performance (% Change)", normalize=True)

    # Main chart: Rheinmetall (usually most traded)
    main_ticker = "RNMBY"
    df_main = get_price_history(main_ticker, period="6mo")
    main_chart = price_chart(df_main, main_ticker, "Rheinmetall (RNMBY)")
    main_rsi = rsi_chart(df_main, main_ticker)

    # Rheinmetall technicals
    rnm_data = tickers_data.get(main_ticker, {})
    rnm_tech = rnm_data.get("components", {}).get("technical", {}).get("detail", {})

    # Daily change heatmap
    quotes = get_batch_quotes(list(symbols.keys()))
    heatmap = daily_change_heatmap(quotes, symbols)

    return html.Div([
        # Signal cards
        dbc.Row(cards, className="mb-3 g-2"),

        # Daily change heatmap
        html.H6("Daily Performance", style={"color": "#aaa", "marginTop": "10px"}),
        heatmap,

        # Comparison chart
        comp,

        dbc.Row([
            dbc.Col([main_chart, main_rsi], md=8),
            dbc.Col([
                signal_gauge(cat_data.get("avg_score", 0), "EU Defense Composite"),
                html.Hr(style={"borderColor": "#333"}),
                html.H6("Rheinmetall Technicals", style={"color": "#aaa"}),
                indicators_table(rnm_tech) if rnm_tech else html.P("Loading...", style={"color": "#888"}),
            ], md=4),
        ], className="mb-3"),

        dbc.Row(dbc.Col([
            html.H6("All Defense Stocks", style={"color": "#aaa", "marginTop": "15px"}),
            price_table(tickers_data, symbols),
        ]), className="mb-3"),

        dbc.Row(dbc.Col(news_panel(_get_cat_news(tickers_data))), className="mb-3"),
    ])


def _render_fx(summaries: dict):
    """Full FX tab: rate table, DXY chart, multi-line comparison, heatmap."""
    cat_data = summaries.get("fx", {})
    tickers_data = cat_data.get("tickers", {})
    symbols = TICKERS["fx"]["symbols"]

    # Fetch current quotes for the rate table
    quotes = get_batch_quotes(list(symbols.keys()))

    # Daily change heatmap
    heatmap = daily_change_heatmap(quotes, symbols)

    # DXY chart
    dxy_ticker = "DX-Y.NYB"
    df_dxy = get_price_history(dxy_ticker, period="6mo")
    dxy_chart = price_chart(df_dxy, dxy_ticker, "US Dollar Index (DXY)", show_ma=True)
    dxy_rsi = rsi_chart(df_dxy, dxy_ticker)

    # Multi-line comparison of major pairs
    pairs = ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "CADUSD=X"]
    comp_data = {}
    for t in pairs:
        df = get_price_history(t, period="6mo")
        comp_data[t] = (symbols.get(t, t), df)
    comp = comparison_chart(comp_data, "Major FX Pairs vs USD (% Change)", normalize=True)

    # DXY technicals
    dxy_data = tickers_data.get(dxy_ticker, {})
    dxy_tech = dxy_data.get("components", {}).get("technical", {}).get("detail", {})

    # Strength summary
    strong_pairs = []
    weak_pairs = []
    for t, data in tickers_data.items():
        if t == dxy_ticker:
            continue
        score = data.get("composite_score", 0)
        name = symbols.get(t, t)
        if score > 0.15:
            strong_pairs.append(name)
        elif score < -0.15:
            weak_pairs.append(name)

    return html.Div([
        # Daily change heatmap at top
        html.H6("FX Daily Changes", style={"color": "#aaa"}),
        heatmap,

        # Rate table + DXY
        dbc.Row([
            # FX Rate table
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Exchange Rates", style={"backgroundColor": "#16162a", "color": "#aaa"}),
                    dbc.CardBody(fx_rate_table(tickers_data, symbols, quotes)),
                ], style={"backgroundColor": "#1e1e2f", "border": "1px solid #333"}),
            ], md=5),

            # DXY + sidebar
            dbc.Col([
                dxy_chart,
                dxy_rsi,
            ], md=7),
        ], className="mb-3 mt-3"),

        # Strength summary
        dbc.Row(dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H6("USD Strength Summary", style={"color": "#ccc"}),
                html.Div([
                    html.Span("Strengthening vs USD: ", style={"color": "#888"}),
                    html.Span(", ".join(strong_pairs) if strong_pairs else "None", style={"color": "#69f0ae"}),
                ], style={"marginBottom": "5px"}),
                html.Div([
                    html.Span("Weakening vs USD: ", style={"color": "#888"}),
                    html.Span(", ".join(weak_pairs) if weak_pairs else "None", style={"color": "#ff8a65"}),
                ]),
            ]), style={"backgroundColor": "#1e1e2f", "border": "1px solid #555"}),
        ), className="mb-3"),

        # Composite gauge + DXY technicals
        dbc.Row([
            dbc.Col(signal_gauge(cat_data.get("avg_score", 0), "FX Composite"), md=4),
            dbc.Col([
                html.H6("DXY Technical Indicators", style={"color": "#aaa"}),
                indicators_table(dxy_tech) if dxy_tech else html.P("Loading...", style={"color": "#888"}),
            ], md=8),
        ], className="mb-3"),

        # Comparison chart
        comp,

        # News
        dbc.Row(dbc.Col(news_panel(_get_cat_news(tickers_data))), className="mt-3 mb-3"),
    ])
