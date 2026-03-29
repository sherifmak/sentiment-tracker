"""Composite scoring: blend technical, market, and news signals."""

import statistics

from data.market_data import get_price_history
from sentiment.technical import compute_all_technicals
from sentiment.market_sentiment import compute_market_sentiment_score
from sentiment.news_sentiment import get_category_news_sentiment
from config import COMPOSITE_WEIGHTS, SIGNAL_THRESHOLDS, TICKERS


def classify_signal(score: float) -> str:
    """Map composite score to a signal label."""
    if score >= SIGNAL_THRESHOLDS["strong_bullish"]:
        return "STRONG BULLISH"
    elif score >= SIGNAL_THRESHOLDS["bullish"]:
        return "BULLISH"
    elif score >= SIGNAL_THRESHOLDS["neutral"]:
        return "NEUTRAL"
    elif score >= SIGNAL_THRESHOLDS["bearish"]:
        return "BEARISH"
    else:
        return "STRONG BEARISH"


def signal_color(signal: str) -> str:
    """Return a color for the signal."""
    return {
        "STRONG BULLISH": "#00c853",
        "BULLISH": "#69f0ae",
        "NEUTRAL": "#ffd740",
        "BEARISH": "#ff8a65",
        "STRONG BEARISH": "#ff1744",
    }.get(signal, "#ffd740")


def compute_composite(ticker: str, category: str) -> dict:
    """Compute the composite sentiment signal for a single ticker."""
    # Technical indicators
    df = get_price_history(ticker, period="1y")
    tech = compute_all_technicals(df) if not df.empty else {"score": 0}

    # Market-wide sentiment
    market = compute_market_sentiment_score()

    # News sentiment for the category
    news = get_category_news_sentiment(category)

    # Component scores
    tech_score = tech["score"]
    market_score = market["score"]
    news_score = news["score"]

    # Alignment bonus: if all three agree on direction, add confidence
    all_scores = [tech_score, market_score, news_score]
    all_same_sign = all(s > 0 for s in all_scores) or all(s < 0 for s in all_scores)
    alignment = 1.0 if all_same_sign else -0.5

    # Weighted blend
    w = COMPOSITE_WEIGHTS
    composite_score = (
        tech_score * w["technical"]
        + market_score * w["market_sentiment"]
        + news_score * w["news_sentiment"]
        + alignment * w["alignment_bonus"]
    )
    composite_score = max(-1.0, min(1.0, composite_score))

    # Confidence: based on agreement among components
    try:
        stdev = statistics.stdev(all_scores) if len(all_scores) > 1 else 0
        confidence = max(0.0, min(1.0, 1.0 - stdev))
    except Exception:
        confidence = 0.5

    signal = classify_signal(composite_score)

    return {
        "ticker": ticker,
        "category": category,
        "composite_score": round(composite_score, 3),
        "signal": signal,
        "signal_color": signal_color(signal),
        "confidence": round(confidence, 2),
        "components": {
            "technical": {"score": round(tech_score, 3), "detail": tech},
            "market_sentiment": {"score": round(market_score, 3), "detail": market},
            "news_sentiment": {"score": round(news_score, 3), "detail": news},
        },
    }


def compute_category_summary(category: str) -> dict:
    """Compute composite signals for all tickers in a category."""
    cat_info = TICKERS.get(category, {})
    symbols = cat_info.get("symbols", {})

    results = {}
    for ticker in symbols:
        results[ticker] = compute_composite(ticker, category)

    # Category-level aggregate
    if results:
        avg_score = sum(r["composite_score"] for r in results.values()) / len(results)
        signal = classify_signal(avg_score)
    else:
        avg_score = 0
        signal = "NEUTRAL"

    return {
        "category": category,
        "label": cat_info.get("label", category),
        "avg_score": round(avg_score, 3),
        "signal": signal,
        "signal_color": signal_color(signal),
        "tickers": results,
    }


def compute_all_summaries() -> dict[str, dict]:
    """Compute summaries for all asset categories."""
    return {cat: compute_category_summary(cat) for cat in TICKERS}
