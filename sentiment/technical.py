"""Technical indicator computation — pure pandas/numpy, no external TA library."""

import pandas as pd
import numpy as np


# ── Indicator Computations ───────────────────────────────────────────────────

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI from a price series."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _sma(series: pd.Series, length: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=length).mean()


def _ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=length, adjust=False).mean()


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, histogram."""
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger_bands(series: pd.Series, length: int = 20, std: float = 2.0):
    """Upper band, middle band, lower band."""
    mid = _sma(series, length)
    rolling_std = series.rolling(window=length).std()
    upper = mid + std * rolling_std
    lower = mid - std * rolling_std
    return upper, mid, lower


# ── Scored Indicators ────────────────────────────────────────────────────────

def compute_rsi(df: pd.DataFrame, period: int = 14) -> dict:
    """Compute RSI and return score + raw value."""
    if df.empty or len(df) < period + 1:
        return {"raw": None, "score": 0, "label": "insufficient data"}

    rsi_series = _rsi(df["Close"], period)
    rsi = rsi_series.iloc[-1]

    if pd.isna(rsi):
        return {"raw": None, "score": 0, "label": "N/A"}

    score = max(-1.0, min(1.0, (50 - rsi) / 40))

    if rsi < 30:
        label = "oversold"
    elif rsi > 70:
        label = "overbought"
    elif rsi < 45:
        label = "leaning bullish"
    elif rsi > 55:
        label = "leaning bearish"
    else:
        label = "neutral"

    return {"raw": round(float(rsi), 2), "score": round(score, 3), "label": label}


def compute_macd(df: pd.DataFrame) -> dict:
    """Compute MACD (12/26/9) and return signal."""
    if df.empty or len(df) < 35:
        return {"raw": None, "score": 0, "label": "insufficient data"}

    macd_line, signal_line, histogram = _macd(df["Close"])
    h = float(histogram.iloc[-1])
    m = float(macd_line.iloc[-1])
    s = float(signal_line.iloc[-1])

    if pd.isna(h) or pd.isna(m):
        return {"raw": None, "score": 0, "label": "N/A"}

    price = float(df["Close"].iloc[-1])
    if price == 0:
        return {"raw": round(h, 4), "score": 0, "label": "N/A"}

    norm_hist = h / price * 100
    score = max(-1.0, min(1.0, norm_hist * 10))

    if m > s and h > 0:
        label = "bullish crossover"
    elif m < s and h < 0:
        label = "bearish crossover"
    elif h > 0:
        label = "bullish"
    else:
        label = "bearish"

    return {"raw": round(h, 4), "score": round(score, 3), "label": label}


def compute_moving_averages(df: pd.DataFrame) -> dict:
    """Compute SMA 20/50/200 and trend signals."""
    result = {"score": 0, "label": "insufficient data", "sma20": None, "sma50": None, "sma200": None}

    if df.empty:
        return result

    price = float(df["Close"].iloc[-1])
    scores = []

    if len(df) >= 20:
        val = float(_sma(df["Close"], 20).iloc[-1])
        if not pd.isna(val):
            result["sma20"] = round(val, 2)
            scores.append(1.0 if price > val else -1.0)

    if len(df) >= 50:
        val = float(_sma(df["Close"], 50).iloc[-1])
        if not pd.isna(val):
            result["sma50"] = round(val, 2)
            scores.append(1.0 if price > val else -1.0)

    if len(df) >= 200:
        val = float(_sma(df["Close"], 200).iloc[-1])
        if not pd.isna(val):
            result["sma200"] = round(val, 2)
            scores.append(1.0 if price > val else -1.0)

    if scores:
        result["score"] = round(sum(scores) / len(scores), 3)
        if result["score"] > 0.5:
            result["label"] = "bullish trend"
        elif result["score"] < -0.5:
            result["label"] = "bearish trend"
        else:
            result["label"] = "mixed"

    if result["sma50"] and result["sma200"]:
        result["cross"] = "golden cross" if result["sma50"] > result["sma200"] else "death cross"

    return result


def compute_bollinger(df: pd.DataFrame) -> dict:
    """Compute Bollinger Bands position."""
    if df.empty or len(df) < 20:
        return {"score": 0, "label": "insufficient data", "position": None}

    upper, mid, lower = _bollinger_bands(df["Close"])
    price = float(df["Close"].iloc[-1])
    u = float(upper.iloc[-1])
    l = float(lower.iloc[-1])

    if pd.isna(u) or pd.isna(l) or u == l:
        return {"score": 0, "label": "N/A", "position": None}

    position = (price - l) / (u - l)
    score = max(-1.0, min(1.0, (0.5 - position) * 2))

    if position < 0.1:
        label = "below lower band"
    elif position < 0.3:
        label = "near lower band"
    elif position > 0.9:
        label = "above upper band"
    elif position > 0.7:
        label = "near upper band"
    else:
        label = "mid-range"

    return {"score": round(score, 3), "label": label, "position": round(position, 3)}


def compute_volume_signal(df: pd.DataFrame) -> dict:
    """Compare current volume to 20-day average."""
    if df.empty or len(df) < 21 or "Volume" not in df.columns:
        return {"score": 0, "label": "no volume data", "ratio": None}

    current_vol = float(df["Volume"].iloc[-1])
    avg_vol = float(df["Volume"].iloc[-21:-1].mean())

    if pd.isna(avg_vol) or avg_vol == 0:
        return {"score": 0, "label": "N/A", "ratio": None}

    ratio = current_vol / avg_vol
    price_change = float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2]) if len(df) >= 2 else 0
    direction = 1 if price_change >= 0 else -1

    if ratio > 1.5:
        score = 0.5 * direction
        label = f"high volume ({ratio:.1f}x avg)"
    elif ratio > 1.0:
        score = 0.2 * direction
        label = f"above average ({ratio:.1f}x)"
    else:
        score = 0
        label = f"below average ({ratio:.1f}x)"

    return {"score": round(score, 3), "label": label, "ratio": round(ratio, 2)}


def compute_all_technicals(df: pd.DataFrame) -> dict:
    """Compute all technical indicators for a given OHLCV DataFrame."""
    rsi = compute_rsi(df)
    macd = compute_macd(df)
    ma = compute_moving_averages(df)
    bb = compute_bollinger(df)
    vol = compute_volume_signal(df)

    weights = {"rsi": 0.25, "macd": 0.25, "ma": 0.25, "bb": 0.15, "volume": 0.10}
    total_score = (
        rsi["score"] * weights["rsi"]
        + macd["score"] * weights["macd"]
        + ma["score"] * weights["ma"]
        + bb["score"] * weights["bb"]
        + vol["score"] * weights["volume"]
    )

    return {
        "score": round(total_score, 3),
        "rsi": rsi,
        "macd": macd,
        "moving_averages": ma,
        "bollinger": bb,
        "volume": vol,
    }


# ── Helpers for Charts ───────────────────────────────────────────────────────

def get_rsi_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Return the full RSI series for charting."""
    if df.empty or len(df) < period + 1:
        return pd.Series(dtype=float)
    return _rsi(df["Close"], period)


def get_sma_series(df: pd.DataFrame, length: int) -> pd.Series:
    """Return a full SMA series for charting."""
    if df.empty or len(df) < length:
        return pd.Series(dtype=float)
    return _sma(df["Close"], length)
