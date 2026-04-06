"""Reusable dashboard components: gauges, signal cards, charts."""

import plotly.graph_objects as go
import plotly.express as px
from dash import html, dcc
import dash_bootstrap_components as dbc


def signal_gauge(score: float, title: str = "Composite Signal") -> dcc.Graph:
    """Create a gauge chart showing -1 to +1 composite score."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "", "font": {"size": 28, "color": "white"}},
            gauge={
                "axis": {"range": [-1, 1], "tickvals": [-1, -0.5, 0, 0.5, 1]},
                "bar": {"color": "rgba(255,255,255,0.3)"},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [-1, -0.6], "color": "#ff1744"},
                    {"range": [-0.6, -0.25], "color": "#ff8a65"},
                    {"range": [-0.25, 0.25], "color": "#ffd740"},
                    {"range": [0.25, 0.6], "color": "#69f0ae"},
                    {"range": [0.6, 1], "color": "#00c853"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 3},
                    "thickness": 0.8,
                    "value": score,
                },
            },
            title={"text": title, "font": {"size": 14, "color": "#aaa"}},
        )
    )
    fig.update_layout(
        height=200,
        margin=dict(t=40, b=10, l=30, r=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def fear_greed_gauge(value: float, label: str) -> dcc.Graph:
    """Create a 0-100 fear & greed gauge."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"font": {"size": 36, "color": "white"}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "rgba(255,255,255,0.3)"},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 25], "color": "#ff1744"},
                    {"range": [25, 45], "color": "#ff8a65"},
                    {"range": [45, 55], "color": "#ffd740"},
                    {"range": [55, 75], "color": "#69f0ae"},
                    {"range": [75, 100], "color": "#00c853"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 3},
                    "thickness": 0.8,
                    "value": value,
                },
            },
            title={"text": f"Fear & Greed: {label}", "font": {"size": 14, "color": "#aaa"}},
        )
    )
    fig.update_layout(
        height=250,
        margin=dict(t=50, b=10, l=30, r=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def signal_card(ticker: str, name: str, signal_data: dict) -> dbc.Card:
    """Create a compact signal card for a ticker."""
    score = signal_data.get("composite_score", 0)
    signal = signal_data.get("signal", "NEUTRAL")
    color = signal_data.get("signal_color", "#ffd740")
    confidence = signal_data.get("confidence", 0)

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6(name, className="card-title mb-1", style={"color": "#ccc"}),
                    html.Span(ticker, style={"color": "#888", "fontSize": "0.8rem"}),
                    html.H4(
                        signal,
                        style={"color": color, "fontWeight": "bold", "marginTop": "8px"},
                    ),
                    html.Div(
                        [
                            html.Span(f"Score: {score:+.2f}", style={"color": "#aaa", "fontSize": "0.85rem"}),
                            html.Span(
                                f" | Confidence: {confidence:.0%}",
                                style={"color": "#888", "fontSize": "0.85rem"},
                            ),
                        ]
                    ),
                ]
            )
        ],
        style={
            "backgroundColor": "#1e1e2f",
            "border": f"1px solid {color}",
            "borderRadius": "8px",
            "marginBottom": "10px",
        },
    )


def category_summary_card(summary: dict) -> dbc.Card:
    """Create a summary card for an asset category."""
    label = summary.get("label", "")
    signal = summary.get("signal", "NEUTRAL")
    color = summary.get("signal_color", "#ffd740")
    avg_score = summary.get("avg_score", 0)

    return dbc.Card(
        dbc.CardBody(
            [
                html.H5(label, style={"color": "white", "marginBottom": "5px"}),
                html.H3(
                    signal,
                    style={"color": color, "fontWeight": "bold"},
                ),
                html.P(
                    f"Avg Score: {avg_score:+.3f}",
                    style={"color": "#aaa", "margin": 0},
                ),
            ],
            className="text-center",
        ),
        style={
            "backgroundColor": "#1e1e2f",
            "border": f"2px solid {color}",
            "borderRadius": "10px",
        },
    )


def price_chart(df, ticker: str, name: str, show_ma: bool = True) -> dcc.Graph:
    """Create a candlestick chart with optional moving average overlays."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "white"},
        )
        return dcc.Graph(figure=fig, config={"displayModeBar": False})

    fig = go.Figure()

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color="#00c853",
            decreasing_line_color="#ff1744",
        )
    )

    # Moving averages
    if show_ma and len(df) >= 20:
        from sentiment.technical import get_sma_series

        sma20 = get_sma_series(df, 20)
        if not sma20.empty:
            fig.add_trace(go.Scatter(x=df.index, y=sma20, name="SMA 20",
                                     line=dict(color="#42a5f5", width=1)))
        if len(df) >= 50:
            sma50 = get_sma_series(df, 50)
            if not sma50.empty:
                fig.add_trace(go.Scatter(x=df.index, y=sma50, name="SMA 50",
                                         line=dict(color="#ffa726", width=1)))
        if len(df) >= 200:
            sma200 = get_sma_series(df, 200)
            if not sma200.empty:
                fig.add_trace(go.Scatter(x=df.index, y=sma200, name="SMA 200",
                                         line=dict(color="#ab47bc", width=1)))

    fig.update_layout(
        title=f"{name} ({ticker})",
        height=450,
        xaxis_rangeslider_visible=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#1a1a2e",
        font={"color": "white"},
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=40, b=40, l=50, r=20),
    )

    return dcc.Graph(figure=fig)


def rsi_chart(df, ticker: str) -> dcc.Graph:
    """Create an RSI subplot chart."""
    from sentiment.technical import get_rsi_series

    fig = go.Figure()

    if not df.empty and len(df) >= 15:
        rsi = get_rsi_series(df)
        if not rsi.empty:
            fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI(14)",
                                     line=dict(color="#42a5f5")))
            # Overbought/oversold lines
            fig.add_hline(y=70, line_dash="dash", line_color="#ff1744", opacity=0.5)
            fig.add_hline(y=30, line_dash="dash", line_color="#00c853", opacity=0.5)
            fig.add_hline(y=50, line_dash="dot", line_color="#666", opacity=0.3)

    fig.update_layout(
        title=f"RSI (14) — {ticker}",
        height=200,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#1a1a2e",
        font={"color": "white"},
        yaxis=dict(range=[0, 100], gridcolor="#333"),
        xaxis=dict(gridcolor="#333"),
        margin=dict(t=35, b=30, l=50, r=20),
        showlegend=False,
    )

    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def news_panel(articles: list[dict]) -> dbc.Card:
    """Create a scrollable news panel with sentiment-colored headlines."""
    if not articles:
        return dbc.Card(
            dbc.CardBody(html.P("No recent news", style={"color": "#888"})),
            style={"backgroundColor": "#1e1e2f"},
        )

    items = []
    for art in articles[:10]:
        score = art.get("normalized_score") or art.get("tone", 0)
        if isinstance(score, (int, float)):
            if score > 0.1:
                color = "#69f0ae"
            elif score < -0.1:
                color = "#ff8a65"
            else:
                color = "#aaa"
        else:
            color = "#aaa"

        items.append(
            html.Div(
                [
                    html.A(
                        art.get("title", "Untitled"),
                        href=art.get("url", "#"),
                        target="_blank",
                        style={"color": color, "textDecoration": "none", "fontSize": "0.85rem"},
                    ),
                    html.Span(
                        f" — {art.get('source', '')}",
                        style={"color": "#666", "fontSize": "0.75rem"},
                    ),
                ],
                style={"marginBottom": "8px"},
            )
        )

    return dbc.Card(
        [
            dbc.CardHeader("Latest News", style={"backgroundColor": "#16162a", "color": "#aaa"}),
            dbc.CardBody(
                items,
                style={"maxHeight": "300px", "overflowY": "auto"},
            ),
        ],
        style={"backgroundColor": "#1e1e2f", "border": "1px solid #333"},
    )


def indicators_table(tech_data: dict) -> dbc.Table:
    """Create a table of technical indicators."""
    rows = []

    indicators = [
        ("RSI (14)", tech_data.get("rsi", {})),
        ("MACD", tech_data.get("macd", {})),
        ("Moving Avgs", tech_data.get("moving_averages", {})),
        ("Bollinger", tech_data.get("bollinger", {})),
        ("Volume", tech_data.get("volume", {})),
    ]

    for name, data in indicators:
        score = data.get("score", 0)
        label = data.get("label", "N/A")
        raw = data.get("raw", "")

        if score > 0.2:
            color = "#69f0ae"
        elif score < -0.2:
            color = "#ff8a65"
        else:
            color = "#ffd740"

        rows.append(
            html.Tr(
                [
                    html.Td(name, style={"color": "#ccc"}),
                    html.Td(str(raw) if raw else "—", style={"color": "#aaa"}),
                    html.Td(label, style={"color": color}),
                    html.Td(f"{score:+.3f}", style={"color": color, "fontWeight": "bold"}),
                ]
            )
        )

    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Indicator", style={"color": "#888"}),
                        html.Th("Value", style={"color": "#888"}),
                        html.Th("Signal", style={"color": "#888"}),
                        html.Th("Score", style={"color": "#888"}),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        bordered=False,
        dark=True,
        hover=True,
        size="sm",
        style={"backgroundColor": "transparent"},
    )


def comparison_chart(
    dataframes: dict[str, tuple[str, "pd.DataFrame"]], title: str, normalize: bool = False
) -> dcc.Graph:
    """Multi-line chart comparing several tickers. dataframes = {ticker: (name, df)}."""
    import pandas as pd

    fig = go.Figure()
    colors = ["#42a5f5", "#ffa726", "#66bb6a", "#ef5350", "#ab47bc", "#26c6da"]

    for i, (ticker, (name, df)) in enumerate(dataframes.items()):
        if df.empty or "Close" not in df.columns:
            continue
        series = df["Close"]
        if normalize and len(series) > 0:
            series = (series / series.iloc[0] - 1) * 100  # % change from start
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=df.index, y=series, name=f"{name} ({ticker})",
            line=dict(color=color, width=2),
        ))

    y_title = "% Change" if normalize else "Price"
    fig.update_layout(
        title=title,
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#1a1a2e",
        font={"color": "white"},
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(gridcolor="#333", title=y_title),
        legend=dict(bgcolor="rgba(0,0,0,0)", font={"size": 10}),
        margin=dict(t=40, b=40, l=60, r=20),
        hovermode="x unified",
    )
    return dcc.Graph(figure=fig)


def price_table(tickers_data: dict, symbols: dict) -> dbc.Table:
    """Table showing price, change, RSI, and signal for each ticker."""
    rows = []
    for ticker, data in tickers_data.items():
        name = symbols.get(ticker, ticker)
        score = data.get("composite_score", 0)
        signal = data.get("signal", "NEUTRAL")
        color = data.get("signal_color", "#ffd740")
        tech = data.get("components", {}).get("technical", {}).get("detail", {})
        rsi_data = tech.get("rsi", {})
        rsi_val = rsi_data.get("raw", "—")
        ma_data = tech.get("moving_averages", {})
        ma_label = ma_data.get("label", "—")
        macd_data = tech.get("macd", {})
        macd_label = macd_data.get("label", "—")

        # Color RSI
        rsi_color = "#69f0ae" if isinstance(rsi_val, (int, float)) and rsi_val < 40 else \
                    "#ff8a65" if isinstance(rsi_val, (int, float)) and rsi_val > 60 else "#aaa"

        rows.append(
            html.Tr([
                html.Td(ticker, style={"color": "#ccc", "fontWeight": "bold"}),
                html.Td(name, style={"color": "#888"}),
                html.Td(str(rsi_val), style={"color": rsi_color}),
                html.Td(macd_label, style={"color": "#aaa", "fontSize": "0.8rem"}),
                html.Td(ma_label, style={"color": "#aaa", "fontSize": "0.8rem"}),
                html.Td(signal, style={"color": color, "fontWeight": "bold"}),
                html.Td(f"{score:+.3f}", style={"color": color}),
            ])
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Ticker", style={"color": "#888"}),
                html.Th("Name", style={"color": "#888"}),
                html.Th("RSI", style={"color": "#888"}),
                html.Th("MACD", style={"color": "#888"}),
                html.Th("Trend", style={"color": "#888"}),
                html.Th("Signal", style={"color": "#888"}),
                html.Th("Score", style={"color": "#888"}),
            ])),
            html.Tbody(rows),
        ],
        bordered=False, dark=True, hover=True, responsive=True, size="sm",
        style={"backgroundColor": "transparent"},
    )


def fx_rate_table(tickers_data: dict, symbols: dict, quotes: dict) -> dbc.Table:
    """FX-specific table showing rate, daily change, and signal."""
    rows = []
    for ticker, data in tickers_data.items():
        name = symbols.get(ticker, ticker)
        signal = data.get("signal", "NEUTRAL")
        color = data.get("signal_color", "#ffd740")
        score = data.get("composite_score", 0)

        quote = quotes.get(ticker, {})
        rate = quote.get("price")
        change_pct = quote.get("change_pct", 0)

        rate_str = f"{rate:.4f}" if rate and rate < 10 else f"{rate:.2f}" if rate else "—"
        chg_color = "#69f0ae" if change_pct > 0 else "#ff8a65" if change_pct < 0 else "#aaa"

        rows.append(
            html.Tr([
                html.Td(name, style={"color": "#ccc", "fontWeight": "bold"}),
                html.Td(rate_str, style={"color": "white", "fontSize": "1.05rem"}),
                html.Td(f"{change_pct:+.2f}%", style={"color": chg_color, "fontWeight": "bold"}),
                html.Td(signal, style={"color": color, "fontWeight": "bold"}),
                html.Td(f"{score:+.3f}", style={"color": color}),
            ])
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Pair", style={"color": "#888"}),
                html.Th("Rate", style={"color": "#888"}),
                html.Th("Daily Chg", style={"color": "#888"}),
                html.Th("Signal", style={"color": "#888"}),
                html.Th("Score", style={"color": "#888"}),
            ])),
            html.Tbody(rows),
        ],
        bordered=False, dark=True, hover=True, responsive=True, size="sm",
        style={"backgroundColor": "transparent"},
    )


def daily_change_heatmap(quotes: dict, symbols: dict) -> dcc.Graph:
    """Heatmap of daily % changes for a set of tickers."""
    tickers = list(quotes.keys())
    names = [symbols.get(t, t) for t in tickers]
    changes = [quotes[t].get("change_pct", 0) or 0 for t in tickers]

    # Single-row heatmap
    fig = go.Figure(go.Heatmap(
        z=[changes],
        x=names,
        y=["Daily Change"],
        text=[[f"{c:+.2f}%" for c in changes]],
        texttemplate="%{text}",
        textfont={"size": 12, "color": "white"},
        colorscale=[
            [0, "#ff1744"],
            [0.4, "#ff8a65"],
            [0.5, "#333"],
            [0.6, "#69f0ae"],
            [1, "#00c853"],
        ],
        zmid=0,
        showscale=False,
    ))

    fig.update_layout(
        height=100,
        margin=dict(t=10, b=30, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        xaxis=dict(side="bottom"),
        yaxis=dict(visible=False),
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


# ── Educational Components ───────────────────────────────────────────────────

def learn_tip(title: str, content: str) -> dbc.AccordionItem:
    """A single expandable learning tip."""
    return dbc.AccordionItem(
        html.Div(content, style={"color": "#ccc", "fontSize": "0.9rem", "lineHeight": "1.6"}),
        title=title,
        style={"backgroundColor": "#1a1a2e"},
    )


def education_section(title: str, intro: str, tips: list[tuple[str, str]]) -> dbc.Card:
    """Full educational section with intro text and expandable tips."""
    accordion_items = [learn_tip(t, c) for t, c in tips]

    return dbc.Card(
        [
            dbc.CardHeader(
                html.Div([
                    html.Span("Learn", style={
                        "backgroundColor": "#42a5f5", "color": "#000", "padding": "2px 8px",
                        "borderRadius": "4px", "fontSize": "0.75rem", "fontWeight": "bold",
                        "marginRight": "10px", "verticalAlign": "middle",
                    }),
                    html.Span(title, style={"color": "white", "fontSize": "1rem"}),
                ]),
                style={"backgroundColor": "#12122a", "borderBottom": "1px solid #333"},
            ),
            dbc.CardBody([
                html.P(
                    intro,
                    style={"color": "#bbb", "fontSize": "0.95rem", "lineHeight": "1.7", "marginBottom": "15px"},
                ),
                dbc.Accordion(
                    accordion_items,
                    flush=True,
                    start_collapsed=True,
                    style={"backgroundColor": "transparent"},
                ),
            ]),
        ],
        style={"backgroundColor": "#1e1e2f", "border": "1px solid #42a5f5", "borderRadius": "10px", "marginBottom": "20px"},
    )


# ── Educational Content per Tab ──────────────────────────────────────────────

EDUCATION = {
    "overview": {
        "title": "How to Read This Dashboard",
        "intro": (
            "This dashboard tracks 32 assets across 5 categories and gives each one a sentiment "
            "signal from STRONG BEARISH to STRONG BULLISH. Think of it like a weather forecast for "
            "financial markets: it combines technical patterns in price data, broad market mood "
            "(fear vs. greed), and what the news is saying to help you decide whether conditions "
            "favor buying, selling, or staying on the sidelines."
        ),
        "tips": [
            ("What do the colored cards at the top mean?",
             "Each card represents an asset category (like S&P 500 or Gold). The color and label "
             "tell you the overall mood: green = bullish (prices likely to rise), red = bearish "
             "(prices likely to fall), yellow = neutral (no strong direction). The score underneath "
             "ranges from -1.0 (maximum bearish) to +1.0 (maximum bullish)."),

            ("What is the Fear & Greed gauge?",
             "This is a 0-100 scale that measures how emotional the market is. Below 25 = 'Extreme Fear' "
             "(investors are panicking, which can actually be a buying opportunity). Above 75 = 'Extreme "
             "Greed' (everyone is overly optimistic, which often comes before a drop). It's built from 4 "
             "things: the VIX (volatility), put/call ratio (how many people are betting on drops vs rises), "
             "market breadth (are most sectors going up or down?), and momentum (is the S&P above its "
             "long-term average?)."),

            ("How to read the All Signals table",
             "Each row is one asset. RSI is a momentum number (below 30 = oversold/cheap, above 70 = "
             "overbought/expensive). News is the sentiment score from recent headlines (-1 = very negative, "
             "+1 = very positive). Signal is the final verdict, and Score is the raw number behind it. "
             "Look for assets where multiple columns agree - that's a stronger signal."),

            ("What does 'composite' mean?",
             "We blend three types of analysis: (1) Technical indicators (40%) look at price patterns "
             "and math, (2) Market sentiment (30%) measures fear/greed and investor behavior, (3) News "
             "sentiment (20%) reads what journalists are writing. Plus a 10% bonus when all three agree. "
             "No single source is reliable alone, but together they paint a clearer picture."),
        ],
    },

    "sp500": {
        "title": "Understanding the S&P 500 & Market Indices",
        "intro": (
            "The S&P 500 is a list of the 500 biggest US companies. When people say 'the market is "
            "up,' they usually mean the S&P 500 went up. This tab shows you the S&P and related indices "
            "(Dow Jones, NASDAQ, Russell 2000), the VIX 'fear gauge,' and sector ETFs that tell you "
            "which parts of the economy are doing well or struggling."
        ),
        "tips": [
            ("How to read a candlestick chart",
             "Each 'candle' represents one day. The body (thick part) shows the opening and closing "
             "price. Green = the price went up that day (close > open). Red = it went down. The thin "
             "lines (wicks) show the highest and lowest prices that day. A long green candle with no "
             "upper wick = strong buying all day. A long upper wick = buyers tried but sellers pushed "
             "back down."),

            ("What are SMA 20, SMA 50, and SMA 200?",
             "SMA = Simple Moving Average. SMA 20 is the average price over the last 20 days. It "
             "smooths out the noise so you can see the trend. SMA 50 is a medium-term trend, and SMA "
             "200 is the big-picture trend. Key rule: when the price is ABOVE the SMA 200, the overall "
             "trend is bullish. When SMA 50 crosses ABOVE SMA 200, it's called a 'Golden Cross' (very "
             "bullish). When it crosses below, it's a 'Death Cross' (bearish)."),

            ("What is RSI and why does it matter?",
             "RSI (Relative Strength Index) measures momentum on a 0-100 scale. It answers: 'Has this "
             "asset been going up too much or down too much recently?' Below 30 = oversold (it's been "
             "beaten down and might bounce back). Above 70 = overbought (it's been rising fast and might "
             "pull back). Between 40-60 = neutral. RSI doesn't predict the future, but extreme readings "
             "often precede reversals."),

            ("What is VIX and why is it called the 'fear gauge'?",
             "VIX measures how much the market EXPECTS prices to swing over the next 30 days. When "
             "investors are scared, they buy protection (options), which drives VIX up. VIX below 15 = "
             "very calm (maybe too calm). VIX 15-20 = normal. VIX 20-30 = nervous. VIX above 30 = panic. "
             "Historically, VIX spikes are often followed by market rebounds - when everyone is terrified, "
             "that's sometimes the best time to buy. But it can also stay elevated during prolonged "
             "downturns, so don't treat it as a crystal ball."),

            ("What's the difference between SPY, ^GSPC, ^DJI, and ^IXIC?",
             "^GSPC is the actual S&P 500 index (you can't buy it directly). SPY is an ETF that tracks "
             "it (you CAN buy this). ^DJI is the Dow Jones - only 30 stocks, price-weighted, so a $500 "
             "stock matters more than a $50 stock. ^IXIC is the NASDAQ - about 3,000 stocks but dominated "
             "by tech (Apple, Microsoft, Nvidia). ^RUT is the Russell 2000 - small companies that often "
             "move first when the economy is shifting. If the S&P is up but the Russell isn't, the rally "
             "may be fragile."),
        ],
    },

    "oil_gas": {
        "title": "Understanding Oil & Gas Markets",
        "intro": (
            "Oil is one of the most important commodities in the world. Its price affects everything "
            "from gas at the pump to airline tickets to inflation. This tab tracks crude oil prices "
            "(WTI and Brent), energy company stocks (XLE), and natural gas. Oil prices move based on "
            "supply (OPEC decisions, drilling activity) and demand (economic growth, travel, manufacturing)."
        ),
        "tips": [
            ("What's the difference between WTI and Brent crude?",
             "WTI (West Texas Intermediate, ticker CL=F) is the US benchmark - oil produced in Texas. "
             "Brent (BZ=F) is the international benchmark - oil from the North Sea. Brent is usually "
             "$2-5 more expensive because it's the global standard. If the gap between them widens, it "
             "often signals supply disruptions in one region. Most of the world's oil is priced off Brent."),

            ("What is XLE and why track it separately from crude oil?",
             "XLE is an ETF (basket of stocks) containing big oil companies like ExxonMobil and Chevron. "
             "Crude oil price is the raw commodity; XLE is the companies that produce it. They usually "
             "move together, but sometimes diverge. If oil is rising but XLE isn't, the market may think "
             "the oil price increase is temporary. The comparison chart (normalized %) helps you spot "
             "these divergences."),

            ("How does OPEC affect oil prices?",
             "OPEC (Organization of Petroleum Exporting Countries) is a group of oil-producing nations "
             "that coordinate how much oil to pump. When they cut production, supply drops and prices "
             "rise. When they increase production, prices fall. OPEC decisions are some of the biggest "
             "movers of oil prices. Watch the news sentiment panel for OPEC-related headlines."),

            ("What does the % Change comparison chart show?",
             "This normalizes all assets to start at 0% and shows how much each has gained or lost since "
             "the start of the chart period. This makes it easy to compare assets at very different price "
             "levels (oil at $70 vs XLE at $90). If one line is rising faster than others, money is "
             "flowing into that asset disproportionately."),
        ],
    },

    "gold": {
        "title": "Understanding Gold & Precious Metals",
        "intro": (
            "Gold has been a store of value for thousands of years. In modern markets, it serves as a "
            "'safe haven' - when stocks crash or inflation rises, investors often pile into gold. This "
            "tab tracks gold futures (GC=F), gold ETFs (GLD, IAU), and silver (SI=F). The safe-haven "
            "demand indicator compares gold's recent performance against the S&P 500 to tell you whether "
            "investors are seeking safety or taking risks."
        ),
        "tips": [
            ("What is the Safe Haven Demand indicator?",
             "This compares gold's return vs. the S&P 500's return over the last 20 trading days. If "
             "gold is outperforming stocks, investors are likely moving money to safety (fear mode). If "
             "stocks are outperforming gold, investors are in 'risk-on' mode (confident). This is one of "
             "the most intuitive signals: when gold outperforms, it's a warning that people are worried."),

            ("What's the difference between GC=F, GLD, and IAU?",
             "GC=F is the gold futures contract - the 'raw' price of gold per ounce. GLD and IAU are "
             "ETFs that hold physical gold and trade like stocks. GLD is the biggest ($60B+), IAU is "
             "cheaper per share. For tracking price movement they're nearly identical. Futures (GC=F) "
             "trade almost 24 hours, while ETFs only trade during market hours, so futures react to "
             "news faster."),

            ("Why include silver (SI=F)?",
             "Silver and gold usually move together, but silver is more volatile and more tied to "
             "industrial demand (electronics, solar panels). When the gold/silver ratio is high (gold is "
             "expensive relative to silver), some traders see silver as undervalued. Silver also tends to "
             "outperform gold in strong bull markets for precious metals."),

            ("When does gold typically rise?",
             "Gold tends to go up when: (1) Inflation is rising (gold holds value when currency doesn't), "
             "(2) Interest rates are falling (gold doesn't pay interest, so it's more attractive when "
             "bonds pay less), (3) There's geopolitical uncertainty (wars, crises), (4) The US dollar "
             "weakens (gold is priced in dollars, so a weaker dollar makes gold cheaper for foreign "
             "buyers). Check the FX tab's DXY chart alongside gold - they often move in opposite "
             "directions."),
        ],
    },

    "defense": {
        "title": "Understanding European Defense Stocks",
        "intro": (
            "These are the biggest defense companies in Europe: Rheinmetall (Germany, tanks/ammo), BAE "
            "Systems (UK, fighter jets/submarines), Leonardo (Italy, helicopters/electronics), Thales "
            "(France, radar/cybersecurity), and Saab (Sweden, Gripen fighter jet). Defense stocks are "
            "driven by government spending, geopolitical tensions, and NATO decisions. They often move "
            "opposite to the broader market - when the world feels dangerous, defense stocks go up."
        ),
        "tips": [
            ("What does the daily change heatmap show?",
             "The colored bar at the top shows how much each stock moved today. Dark green = big gain, "
             "dark red = big loss. This gives you an instant snapshot. If all 5 are green, defense as a "
             "sector is having a good day. If they're mixed, look at which ones are different and ask why "
             "- maybe there's company-specific news."),

            ("Why are these stocks shown as normalized % change?",
             "These stocks trade in different currencies (EUR, GBP, SEK) at very different price levels. "
             "The OTC tickers we use (RNMBY, BAESY, etc.) are US-traded versions priced in dollars, but "
             "they still have different share prices. Normalizing to % change lets you compare: 'Which "
             "company's stock has grown the most over 6 months?' without being misled by the raw price."),

            ("What drives defense stock prices?",
             "The biggest drivers are: (1) Government defense budgets - NATO countries pledging to spend "
             "2%+ of GDP on defense is huge, (2) Geopolitical events - wars, tensions, threats increase "
             "demand for weapons, (3) Contract wins - when Rheinmetall wins a $10B tank order, its stock "
             "jumps, (4) Earnings reports - quarterly results showing revenue growth. The news panel "
             "below captures these events through GDELT's global news monitoring."),

            ("What are OTC/ADR tickers?",
             "These European companies trade on their home exchanges (Frankfurt, London, etc.), but the "
             "tickers we use (RNMBY, BAESY, FINMY, THLLY, SAABY) are 'ADRs' - American Depositary "
             "Receipts - that let Americans trade foreign stocks on US markets. They're priced in USD "
             "and trade during US hours. The prices track the home exchange, but with a slight lag and "
             "currency conversion built in. Lower liquidity means wider bid/ask spreads."),
        ],
    },

    "fx": {
        "title": "Understanding Foreign Exchange (FX) Rates",
        "intro": (
            "FX (forex) is the market where currencies are traded. Every price here is relative: "
            "EUR/USD = 1.10 means 1 Euro buys 1.10 US Dollars. This tab tracks major currency pairs "
            "against the US Dollar, plus the DXY (Dollar Index), which measures the dollar's strength "
            "against a basket of 6 major currencies. FX matters because it affects international trade, "
            "overseas investment returns, and import/export costs."
        ),
        "tips": [
            ("How to read currency pair names",
             "In 'EUR/USD,' the first currency (EUR) is the 'base' and the second (USD) is the 'quote.' "
             "The number tells you how much quote currency you need to buy 1 unit of base currency. "
             "EUR/USD = 1.10 means 1 EUR costs $1.10. If this number goes UP, the Euro is strengthening "
             "(or the Dollar is weakening). USD/JPY works the other way: if it goes UP, the Dollar is "
             "getting stronger against the Yen."),

            ("What is the DXY (Dollar Index)?",
             "The DXY measures the US Dollar against a basket of 6 currencies: Euro (57.6%), Yen (13.6%), "
             "British Pound (11.9%), Canadian Dollar (9.1%), Swedish Krona (4.2%), Swiss Franc (3.6%). "
             "DXY going UP = Dollar is getting stronger overall. A strong Dollar means US exports become "
             "more expensive (bad for US companies that sell overseas) but imports become cheaper. DXY "
             "above 100 generally means a strong dollar."),

            ("What is the USD Strength Summary?",
             "This section shows which currencies are getting stronger or weaker versus the Dollar right "
             "now, based on the composite signal. If EUR/USD and GBP/USD are both 'bullish,' it means "
             "those currencies are strengthening and the Dollar is relatively weak. If most pairs show "
             "bearish signals, the Dollar is dominating - often a sign of global risk aversion (investors "
             "flee to the 'safety' of the Dollar)."),

            ("Why does FX matter for other investments?",
             "FX rates connect everything: (1) A weak Dollar typically boosts gold prices (gold is priced "
             "in dollars), (2) A strong Dollar hurts US companies' overseas earnings (check S&P tab), "
             "(3) Oil is priced in dollars, so Dollar strength affects oil demand from other countries, "
             "(4) The EU Defense stocks we track are European - if the Euro weakens vs Dollar, the ADR "
             "prices are affected. Understanding FX helps you connect the dots across all the other tabs."),

            ("What moves currency prices?",
             "The biggest drivers: (1) Interest rates - if the US Fed raises rates higher than the ECB, "
             "money flows to the Dollar (higher yield), strengthening it. (2) Economic data - strong jobs "
             "reports, GDP growth, etc. strengthen a currency. (3) Trade balances - countries that export "
             "more than they import tend to have stronger currencies. (4) Risk sentiment - in a crisis, "
             "money flows to 'safe haven' currencies (USD, CHF, JPY). Watch for central bank meeting "
             "dates - those are the biggest FX movers."),
        ],
    },
}


def get_education_section(tab_key: str) -> dbc.Card:
    """Get the educational section for a specific tab."""
    content = EDUCATION.get(tab_key, {})
    if not content:
        return html.Div()
    return education_section(content["title"], content["intro"], content["tips"])
