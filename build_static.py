"""Generate a self-contained static HTML dashboard for GitHub Pages.

Usage: python build_static.py
Output: docs/index.html
"""

import sys
import json
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import plotly

# Ensure project modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from config import TICKERS, NEWS_KEYWORDS, COMPOSITE_WEIGHTS, SIGNAL_THRESHOLDS, VIX_ZONES
from data.market_data import get_price_history, get_current_quote, get_batch_quotes, get_options_put_call_ratio
from sentiment.technical import compute_all_technicals, get_rsi_series, get_sma_series
from sentiment.market_sentiment import interpret_vix, interpret_put_call, compute_breadth, compute_fear_greed_proxy, compute_market_sentiment_score
from sentiment.news_sentiment import get_category_news_sentiment
from sentiment.composite import compute_all_summaries, classify_signal, signal_color


# ── Chart builders (return Plotly figure JSON) ───────────────────────────────

def build_gauge(score, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"size": 28, "color": "white"}},
        gauge={
            "axis": {"range": [-1, 1], "tickvals": [-1, -0.5, 0, 0.5, 1], "tickfont": {"color": "#888"}},
            "bar": {"color": "rgba(255,255,255,0.3)"},
            "bgcolor": "rgba(0,0,0,0)",
            "steps": [
                {"range": [-1, -0.6], "color": "#ff1744"},
                {"range": [-0.6, -0.25], "color": "#ff8a65"},
                {"range": [-0.25, 0.25], "color": "#ffd740"},
                {"range": [0.25, 0.6], "color": "#69f0ae"},
                {"range": [0.6, 1], "color": "#00c853"},
            ],
        },
        title={"text": title, "font": {"size": 13, "color": "#aaa"}},
    ))
    fig.update_layout(height=200, margin=dict(t=40, b=10, l=30, r=30),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "white"})
    return fig


def build_fg_gauge(value, label):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"font": {"size": 36, "color": "white"}},
        gauge={
            "axis": {"range": [0, 100], "tickfont": {"color": "#888"}},
            "bar": {"color": "rgba(255,255,255,0.3)"},
            "bgcolor": "rgba(0,0,0,0)",
            "steps": [
                {"range": [0, 25], "color": "#ff1744"},
                {"range": [25, 45], "color": "#ff8a65"},
                {"range": [45, 55], "color": "#ffd740"},
                {"range": [55, 75], "color": "#69f0ae"},
                {"range": [75, 100], "color": "#00c853"},
            ],
        },
        title={"text": f"Fear & Greed: {label}", "font": {"size": 13, "color": "#aaa"}},
    ))
    fig.update_layout(height=230, margin=dict(t=50, b=10, l=30, r=30),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "white"})
    return fig


def build_candlestick(df, ticker, name):
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False, font={"color": "#888"})
        fig.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#1a1a2e", font={"color": "white"})
        return fig

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name=ticker, increasing_line_color="#00c853", decreasing_line_color="#ff1744",
    ))
    if len(df) >= 20:
        sma20 = get_sma_series(df, 20)
        if not sma20.empty:
            fig.add_trace(go.Scatter(x=df.index, y=sma20, name="SMA 20", line=dict(color="#42a5f5", width=1)))
    if len(df) >= 50:
        sma50 = get_sma_series(df, 50)
        if not sma50.empty:
            fig.add_trace(go.Scatter(x=df.index, y=sma50, name="SMA 50", line=dict(color="#ffa726", width=1)))

    fig.update_layout(
        title=f"{name} ({ticker})", height=420, xaxis_rangeslider_visible=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#1a1a2e", font={"color": "white"},
        xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
        legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(t=40, b=40, l=50, r=20),
    )
    return fig


def build_rsi(df, ticker):
    fig = go.Figure()
    if not df.empty and len(df) >= 15:
        rsi = get_rsi_series(df)
        if not rsi.empty:
            fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI(14)", line=dict(color="#42a5f5")))
            fig.add_hline(y=70, line_dash="dash", line_color="#ff1744", opacity=0.5)
            fig.add_hline(y=30, line_dash="dash", line_color="#00c853", opacity=0.5)
    fig.update_layout(
        title=f"RSI (14) - {ticker}", height=180,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#1a1a2e", font={"color": "white"},
        yaxis=dict(range=[0, 100], gridcolor="#333"), xaxis=dict(gridcolor="#333"),
        margin=dict(t=30, b=25, l=50, r=20), showlegend=False,
    )
    return fig


def build_comparison(data_dict, title, normalize=True):
    colors = ["#42a5f5", "#ffa726", "#66bb6a", "#ef5350", "#ab47bc", "#26c6da"]
    fig = go.Figure()
    for i, (ticker, (name, df)) in enumerate(data_dict.items()):
        if df.empty or "Close" not in df.columns:
            continue
        s = df["Close"]
        if normalize and len(s) > 0:
            s = (s / s.iloc[0] - 1) * 100
        fig.add_trace(go.Scatter(x=df.index, y=s, name=f"{name}", line=dict(color=colors[i % len(colors)], width=2)))
    fig.update_layout(
        title=title, height=350,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#1a1a2e", font={"color": "white"},
        xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333", title="% Change" if normalize else "Price"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font={"size": 10}),
        margin=dict(t=40, b=40, l=60, r=20), hovermode="x unified",
    )
    return fig


def fig_to_div(fig, uid=""):
    return plotly.io.to_html(fig, full_html=False, include_plotlyjs=False, div_id=uid if uid else None)


# ── HTML template ────────────────────────────────────────────────────────────

def signal_badge_html(signal, color):
    return f'<span class="signal-badge" style="background:{color};color:#000;padding:3px 10px;border-radius:4px;font-weight:bold;font-size:0.85rem">{signal}</span>'


def build_html(summaries, fg, vix):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    fg_val = fg.get("value", 50)
    fg_label = fg.get("label", "Neutral")
    vix_raw = vix.get("raw", "—")
    vix_zone = vix.get("zone", "unknown")

    # ── Overview section ─────────────────────────────────────────────
    # Category cards
    cat_cards_html = ""
    for cat_key in ["sp500", "oil_gas", "gold", "defense", "fx"]:
        cat = summaries.get(cat_key, {})
        label = cat.get("label", cat_key)
        sig = cat.get("signal", "NEUTRAL")
        col = cat.get("signal_color", "#ffd740")
        avg = cat.get("avg_score", 0)
        cat_cards_html += f'''
        <div class="cat-card" style="border-color:{col}">
            <div class="cat-label">{label}</div>
            <div class="cat-signal" style="color:{col}">{sig}</div>
            <div class="cat-score">{avg:+.3f}</div>
        </div>'''

    # Fear & greed gauge
    fg_gauge = fig_to_div(build_fg_gauge(fg_val, fg_label), "fg-gauge")

    # Heatmap table rows
    heatmap_rows = ""
    for cat_key, cat_data in summaries.items():
        tickers = cat_data.get("tickers", {})
        syms = TICKERS.get(cat_key, {}).get("symbols", {})
        for ticker, data in tickers.items():
            score = data.get("composite_score", 0)
            sig = data.get("signal", "NEUTRAL")
            col = data.get("signal_color", "#ffd740")
            tech = data.get("components", {}).get("technical", {})
            rsi_val = tech.get("detail", {}).get("rsi", {}).get("raw", "—")
            news_s = data.get("components", {}).get("news_sentiment", {}).get("score", 0)
            heatmap_rows += f'''
            <tr>
                <td style="color:#ccc;font-weight:bold">{ticker}</td>
                <td style="color:#888">{syms.get(ticker, "")}</td>
                <td style="color:#aaa">{rsi_val}</td>
                <td style="color:#aaa">{news_s:+.2f}</td>
                <td style="color:{col};font-weight:bold">{sig}</td>
                <td style="color:{col}">{score:+.3f}</td>
            </tr>'''

    # ── Per-category sections ────────────────────────────────────────
    sections_html = ""
    for cat_key in ["sp500", "oil_gas", "gold", "defense", "fx"]:
        cat = summaries.get(cat_key, {})
        label = cat.get("label", cat_key)
        tickers_data = cat.get("tickers", {})
        syms = TICKERS.get(cat_key, {}).get("symbols", {})

        # Pick a representative ticker for the main chart
        chart_tickers = {
            "sp500": "SPY", "oil_gas": "CL=F", "gold": "GC=F",
            "defense": "RNMBY", "fx": "DX-Y.NYB",
        }
        main_t = chart_tickers.get(cat_key, next(iter(syms), ""))
        main_name = syms.get(main_t, main_t)

        # Candlestick + RSI
        df = get_price_history(main_t, period="6mo")
        candle_div = fig_to_div(build_candlestick(df, main_t, main_name))
        rsi_div = fig_to_div(build_rsi(df, main_t))

        # Gauge
        gauge_div = fig_to_div(build_gauge(cat.get("avg_score", 0), f"{label} Composite"))

        # Comparison chart
        comp_tickers = {
            "sp500": ["SPY", "^DJI", "^IXIC", "^RUT"],
            "oil_gas": ["XLE", "CL=F", "BZ=F"],
            "gold": ["GC=F", "SI=F", "GLD"],
            "defense": list(syms.keys()),
            "fx": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "CADUSD=X"],
        }
        comp_data = {}
        for t in comp_tickers.get(cat_key, []):
            cdf = get_price_history(t, period="6mo")
            comp_data[t] = (syms.get(t, t), cdf)
        comp_div = fig_to_div(build_comparison(comp_data, f"{label} - Relative Performance"))

        # Signal cards
        sig_cards = ""
        for t, d in tickers_data.items():
            s = d.get("signal", "NEUTRAL")
            c = d.get("signal_color", "#ffd740")
            sc = d.get("composite_score", 0)
            conf = d.get("confidence", 0)
            sig_cards += f'''
            <div class="sig-card" style="border-color:{c}">
                <div style="color:#ccc;font-size:0.85rem">{syms.get(t, t)}</div>
                <div style="color:#888;font-size:0.75rem">{t}</div>
                <div style="color:{c};font-weight:bold;margin-top:5px">{s}</div>
                <div style="color:#aaa;font-size:0.8rem">{sc:+.2f} | {conf:.0%}</div>
            </div>'''

        # Technicals table
        main_data = tickers_data.get(main_t, {})
        tech_detail = main_data.get("components", {}).get("technical", {}).get("detail", {})
        tech_rows = ""
        for ind_name, ind_key in [("RSI (14)", "rsi"), ("MACD", "macd"), ("Moving Avgs", "moving_averages"), ("Bollinger", "bollinger"), ("Volume", "volume")]:
            ind = tech_detail.get(ind_key, {})
            raw = ind.get("raw", "—")
            lbl = ind.get("label", "N/A")
            isc = ind.get("score", 0)
            ic = "#69f0ae" if isc > 0.2 else "#ff8a65" if isc < -0.2 else "#ffd740"
            tech_rows += f'<tr><td style="color:#ccc">{ind_name}</td><td style="color:#aaa">{raw}</td><td style="color:{ic}">{lbl}</td><td style="color:{ic};font-weight:bold">{isc:+.3f}</td></tr>'

        # News
        news_detail = main_data.get("components", {}).get("news_sentiment", {}).get("detail", {})
        articles = news_detail.get("articles", []) if isinstance(news_detail, dict) else []
        news_items = ""
        for art in articles[:8]:
            tone = art.get("normalized_score") or art.get("tone", 0)
            nc = "#69f0ae" if isinstance(tone, (int, float)) and tone > 0.1 else "#ff8a65" if isinstance(tone, (int, float)) and tone < -0.1 else "#aaa"
            title = art.get("title", "Untitled")
            url = art.get("url", "#")
            src = art.get("source", "")
            news_items += f'<div style="margin-bottom:6px"><a href="{url}" target="_blank" style="color:{nc};text-decoration:none;font-size:0.85rem">{title}</a> <span style="color:#666;font-size:0.7rem">- {src}</span></div>'

        sections_html += f'''
        <section class="tab-section" id="section-{cat_key}">
            <h2 class="section-title">{label}</h2>
            <div class="sig-cards-row">{sig_cards}</div>
            <div class="two-col">
                <div class="col-main">
                    {candle_div}
                    {rsi_div}
                </div>
                <div class="col-side">
                    {gauge_div}
                    <h4 class="sub-heading">{main_name} Technicals</h4>
                    <table class="data-table">
                        <thead><tr><th>Indicator</th><th>Value</th><th>Signal</th><th>Score</th></tr></thead>
                        <tbody>{tech_rows}</tbody>
                    </table>
                </div>
            </div>
            {comp_div}
            <div class="news-box">
                <h4 class="sub-heading">Latest News</h4>
                {news_items if news_items else '<p style="color:#888">No recent news</p>'}
            </div>
        </section>'''

    # ── Assemble full HTML ───────────────────────────────────────────
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sentiment Tracker</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0d0d1a; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; padding:20px; max-width:1400px; margin:0 auto; }}
a {{ color:#42a5f5; }}
.header {{ background:#12122a; border:1px solid #333; border-radius:8px; padding:15px 20px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; }}
.header h1 {{ font-size:1.4rem; letter-spacing:2px; }}
.header-stats {{ color:#aaa; font-size:0.9rem; }}
.nav {{ display:flex; gap:0; border-bottom:1px solid #333; margin-bottom:25px; overflow-x:auto; }}
.nav a {{ color:#888; text-decoration:none; padding:10px 20px; font-size:0.9rem; white-space:nowrap; }}
.nav a:hover {{ color:#ccc; border-bottom:2px solid #555; }}
.nav a.active {{ color:#fff; border-bottom:2px solid #42a5f5; }}
.cat-cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:25px; }}
.cat-card {{ background:#1e1e2f; border:2px solid #ffd740; border-radius:10px; padding:15px 20px; text-align:center; min-width:140px; flex:1; }}
.cat-label {{ color:white; font-size:1rem; margin-bottom:3px; }}
.cat-signal {{ font-size:1.3rem; font-weight:bold; }}
.cat-score {{ color:#aaa; font-size:0.85rem; }}
.overview-grid {{ display:grid; grid-template-columns:1fr 2fr; gap:20px; margin-bottom:25px; }}
@media(max-width:768px) {{ .overview-grid {{ grid-template-columns:1fr; }} }}
.heatmap-box {{ background:#1e1e2f; border:1px solid #333; border-radius:8px; overflow:hidden; }}
.heatmap-box h3 {{ background:#16162a; color:#aaa; padding:10px 15px; font-size:0.9rem; }}
.heatmap-box .inner {{ max-height:500px; overflow-y:auto; padding:10px; }}
.data-table {{ width:100%; border-collapse:collapse; }}
.data-table th {{ color:#888; text-align:left; padding:6px 10px; border-bottom:1px solid #2a2a3e; font-size:0.8rem; }}
.data-table td {{ padding:6px 10px; border-bottom:1px solid #1a1a2e; font-size:0.85rem; }}
.data-table tr:hover {{ background:rgba(66,165,245,0.08); }}
.tab-section {{ margin-bottom:40px; padding-top:20px; border-top:1px solid #222; }}
.section-title {{ color:white; font-size:1.3rem; margin-bottom:15px; }}
.sig-cards-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px; }}
.sig-card {{ background:#1e1e2f; border:1px solid #ffd740; border-radius:8px; padding:10px 15px; min-width:130px; flex:1; }}
.two-col {{ display:grid; grid-template-columns:2fr 1fr; gap:20px; margin-bottom:15px; }}
@media(max-width:768px) {{ .two-col {{ grid-template-columns:1fr; }} }}
.col-main {{ min-width:0; }}
.col-side {{ min-width:0; }}
.sub-heading {{ color:#aaa; font-size:0.9rem; margin:10px 0 8px; }}
.news-box {{ background:#1e1e2f; border:1px solid #333; border-radius:8px; padding:15px; margin-top:15px; max-height:300px; overflow-y:auto; }}
.signal-badge {{ display:inline-block; }}
.footer {{ text-align:center; color:#555; font-size:0.75rem; margin-top:30px; padding:15px 0; border-top:1px solid #222; }}
::-webkit-scrollbar {{ width:6px; }}
::-webkit-scrollbar-track {{ background:#1a1a2e; }}
::-webkit-scrollbar-thumb {{ background:#444; border-radius:3px; }}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <h1>SENTIMENT TRACKER</h1>
    <div class="header-stats">
        Fear &amp; Greed: <span style="color:{"#ff1744" if fg_val < 35 else "#00c853" if fg_val > 65 else "#ffd740"}">{fg_val:.0f} ({fg_label})</span>
        &nbsp;|&nbsp; VIX: <span style="color:{"#ff8a65" if vix_zone in ("elevated","extreme_fear") else "#69f0ae"}">{vix_raw}</span>
        &nbsp;|&nbsp; Updated: {now}
    </div>
</div>

<!-- Navigation -->
<nav class="nav">
    <a href="#section-overview" class="active">Overview</a>
    <a href="#section-sp500">S&amp;P &amp; Indices</a>
    <a href="#section-oil_gas">Oil &amp; Gas</a>
    <a href="#section-gold">Gold</a>
    <a href="#section-defense">EU Defense</a>
    <a href="#section-fx">FX Rates</a>
</nav>

<!-- Overview -->
<section id="section-overview">
    <div class="cat-cards">{cat_cards_html}</div>
    <div class="overview-grid">
        <div>{fg_gauge}</div>
        <div class="heatmap-box">
            <h3>All Signals</h3>
            <div class="inner">
                <table class="data-table">
                    <thead><tr><th>Ticker</th><th>Name</th><th>RSI</th><th>News</th><th>Signal</th><th>Score</th></tr></thead>
                    <tbody>{heatmap_rows}</tbody>
                </table>
            </div>
        </div>
    </div>
</section>

<!-- Per-category sections -->
{sections_html}

<div class="footer">
    Data: Yahoo Finance | Sentiment: GDELT + TextBlob | Not financial advice<br>
    Generated {now}
</div>

<script>
// Simple scroll-based nav highlighting
document.querySelectorAll('.nav a').forEach(a => {{
    a.addEventListener('click', e => {{
        document.querySelectorAll('.nav a').forEach(x => x.classList.remove('active'));
        a.classList.add('active');
    }});
}});
</script>
</body>
</html>'''
    return html


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Fetching data and computing signals...")
    summaries = compute_all_summaries()

    print("Computing fear & greed proxy...")
    fg = compute_fear_greed_proxy()

    print("Getting VIX data...")
    vix = interpret_vix()

    print("Building static HTML...")
    html_content = build_html(summaries, fg, vix)

    out_path = Path(__file__).parent / "docs" / "index.html"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print(f"\nDone! Generated {out_path} ({size_kb:.0f} KB)")
    print("To preview: open docs/index.html in a browser")
    print("To deploy: push to GitHub and enable Pages from docs/ folder")


if __name__ == "__main__":
    main()
