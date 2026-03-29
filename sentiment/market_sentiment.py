"""Market-wide sentiment indicators: VIX, put/call, fear & greed proxy."""

from data.market_data import get_price_history, get_current_quote, get_options_put_call_ratio
from config import VIX_ZONES


def interpret_vix() -> dict:
    """Interpret current VIX level into a sentiment score."""
    quote = get_current_quote("^VIX")
    vix = quote.get("price")

    if vix is None:
        return {"raw": None, "score": 0, "label": "unavailable", "zone": "unknown"}

    # VIX scoring: low VIX = complacent (slightly bearish contrarian), high = fear (bullish contrarian)
    # But for immediate trading: high VIX = danger, low VIX = calm
    # We score from the perspective of "is it safe to be bullish?"
    if vix < 15:
        score = 0.3  # Calm, mildly bullish but watch for complacency
        zone = "complacent"
    elif vix < 20:
        score = 0.1  # Normal
        zone = "normal"
    elif vix < 30:
        score = -0.4  # Elevated fear
        zone = "elevated"
    else:
        score = -0.8  # Extreme fear — contrarian bullish, but dangerous
        zone = "extreme_fear"

    return {
        "raw": round(vix, 2),
        "score": round(score, 3),
        "label": zone.replace("_", " ").title(),
        "zone": zone,
        "change": quote.get("change", 0),
        "change_pct": quote.get("change_pct", 0),
    }


def interpret_put_call() -> dict:
    """Score the SPY put/call volume ratio."""
    ratio = get_options_put_call_ratio("SPY")

    if ratio is None:
        return {"raw": None, "score": 0, "label": "unavailable"}

    # >1.0 = heavy put buying (bearish sentiment, contrarian bullish)
    # <0.7 = heavy call buying (bullish sentiment, contrarian bearish)
    # We blend directional + contrarian: extreme readings = contrarian signal
    if ratio > 1.2:
        score = 0.3  # Extreme bearish sentiment → contrarian bullish
        label = "extreme bearish (contrarian bullish)"
    elif ratio > 1.0:
        score = -0.2  # Bearish
        label = "bearish"
    elif ratio > 0.7:
        score = 0.1  # Neutral-bullish
        label = "neutral"
    else:
        score = -0.3  # Extreme bullish sentiment → contrarian bearish
        label = "extreme bullish (contrarian bearish)"

    return {"raw": ratio, "score": round(score, 3), "label": label}


def compute_breadth() -> dict:
    """Approximate market breadth from sector ETF performance."""
    sector_etfs = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLRE"]
    above_count = 0
    total = 0

    for etf in sector_etfs:
        quote = get_current_quote(etf)
        change_pct = quote.get("change_pct", 0)
        if change_pct is not None:
            total += 1
            if change_pct > 0:
                above_count += 1

    if total == 0:
        return {"raw": None, "score": 0, "label": "unavailable"}

    breadth = above_count / total  # 0 to 1
    score = (breadth - 0.5) * 2  # Map to [-1, 1]

    if breadth > 0.8:
        label = "broad rally"
    elif breadth > 0.5:
        label = "mostly positive"
    elif breadth > 0.2:
        label = "mostly negative"
    else:
        label = "broad selloff"

    return {
        "raw": f"{above_count}/{total} sectors green",
        "score": round(score, 3),
        "label": label,
    }


def compute_fear_greed_proxy() -> dict:
    """Composite fear & greed index (0-100) from available data."""
    components = {}

    # 1. VIX component (inverted: low VIX = high greed)
    vix = interpret_vix()
    if vix["raw"] is not None:
        # Map VIX 10-40 to greed 100-0
        vix_greed = max(0, min(100, (40 - vix["raw"]) / 30 * 100))
        components["vix"] = vix_greed

    # 2. Put/Call ratio (inverted: low ratio = greed)
    pc = interpret_put_call()
    if pc["raw"] is not None:
        # Map ratio 0.5-1.5 to greed 100-0
        pc_greed = max(0, min(100, (1.5 - pc["raw"]) / 1.0 * 100))
        components["put_call"] = pc_greed

    # 3. Market breadth
    breadth = compute_breadth()
    if breadth["score"] != 0 or breadth["raw"] is not None:
        breadth_greed = (breadth["score"] + 1) / 2 * 100  # Map [-1,1] to [0,100]
        components["breadth"] = breadth_greed

    # 4. S&P momentum (price vs 125-day MA)
    try:
        from sentiment.technical import get_sma_series
        df = get_price_history("SPY", period="1y")
        if not df.empty:
            price = float(df["Close"].iloc[-1])
            sma125 = get_sma_series(df, 125)
            if not sma125.empty:
                ma_val = float(sma125.iloc[-1])
                if ma_val and ma_val > 0:
                    pct_above = ((price - ma_val) / ma_val) * 100
                    momentum_greed = max(0, min(100, 50 + pct_above * 5))
                    components["momentum"] = momentum_greed
    except Exception:
        pass

    if not components:
        return {"value": 50, "label": "Neutral", "components": {}}

    # Weighted average
    weights = {"vix": 0.30, "put_call": 0.25, "breadth": 0.25, "momentum": 0.20}
    total_weight = sum(weights.get(k, 0.25) for k in components)
    value = sum(v * weights.get(k, 0.25) for k, v in components.items()) / total_weight

    value = round(value, 1)
    if value < 25:
        label = "Extreme Fear"
    elif value < 45:
        label = "Fear"
    elif value < 55:
        label = "Neutral"
    elif value < 75:
        label = "Greed"
    else:
        label = "Extreme Greed"

    return {"value": value, "label": label, "components": components}


def compute_market_sentiment_score() -> dict:
    """Aggregate market-wide sentiment into a single score."""
    vix = interpret_vix()
    pc = interpret_put_call()
    breadth = compute_breadth()

    # Weighted blend
    score = (
        vix["score"] * 0.40
        + pc["score"] * 0.30
        + breadth["score"] * 0.30
    )

    return {
        "score": round(score, 3),
        "vix": vix,
        "put_call": pc,
        "breadth": breadth,
    }
