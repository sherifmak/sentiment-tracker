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
