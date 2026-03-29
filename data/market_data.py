"""Fetch and cache market data via Yahoo Finance API (no yfinance dependency)."""

import time
import requests
import pandas as pd
import numpy as np
from io import StringIO

from config import CACHE_TTL_SECONDS

# ── In-memory cache ──────────────────────────────────────────────────────────

_price_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_info_cache: dict[str, tuple[float, dict]] = {}

_YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def _yahoo_chart(ticker: str, range_: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV data from Yahoo Finance chart API."""
    url = _YAHOO_CHART_URL.format(ticker=ticker)
    params = {"range": range_, "interval": interval, "includePrePost": "false"}

    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        result = data.get("chart", {}).get("result", [])
        if not result:
            return pd.DataFrame()

        chart = result[0]
        timestamps = chart.get("timestamp", [])
        quote = chart.get("indicators", {}).get("quote", [{}])[0]

        if not timestamps:
            return pd.DataFrame()

        df = pd.DataFrame({
            "Open": quote.get("open", []),
            "High": quote.get("high", []),
            "Low": quote.get("low", []),
            "Close": quote.get("close", []),
            "Volume": quote.get("volume", []),
        }, index=pd.to_datetime(timestamps, unit="s"))

        df.index.name = "Date"
        df = df.dropna(subset=["Close"])
        return df

    except Exception:
        return pd.DataFrame()


def get_price_history(
    ticker: str, period: str = "6mo", interval: str = "1d"
) -> pd.DataFrame:
    """Return OHLCV DataFrame for a ticker, with caching."""
    cache_key = f"{ticker}_{period}_{interval}"
    now = time.time()

    if cache_key in _price_cache:
        ts, df = _price_cache[cache_key]
        if now - ts < CACHE_TTL_SECONDS:
            return df

    df = _yahoo_chart(ticker, range_=period, interval=interval)
    if not df.empty:
        _price_cache[cache_key] = (now, df)
    return df if not df.empty else _price_cache.get(cache_key, (0, pd.DataFrame()))[1]


def get_current_quote(ticker: str) -> dict:
    """Return current price info for a ticker."""
    now = time.time()

    if ticker in _info_cache:
        ts, info = _info_cache[ticker]
        if now - ts < CACHE_TTL_SECONDS:
            return info

    # Use 5-day range to get recent data including current
    df = get_price_history(ticker, period="5d", interval="1d")

    if df.empty:
        return _info_cache.get(ticker, (0, {}))[1]

    price = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else price
    volume = float(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0

    info = {
        "price": price,
        "prev_close": prev_close,
        "open": float(df["Open"].iloc[-1]) if "Open" in df.columns else price,
        "day_high": float(df["High"].iloc[-1]) if "High" in df.columns else price,
        "day_low": float(df["Low"].iloc[-1]) if "Low" in df.columns else price,
        "volume": volume,
        "change": price - prev_close,
        "change_pct": ((price - prev_close) / prev_close * 100) if prev_close else 0,
    }

    _info_cache[ticker] = (now, info)
    return info


def get_batch_quotes(tickers: list[str]) -> dict[str, dict]:
    """Fetch current quotes for multiple tickers."""
    return {ticker: get_current_quote(ticker) for ticker in tickers}


def get_options_put_call_ratio(ticker: str = "SPY") -> float | None:
    """Fetch put/call ratio from Yahoo Finance options data."""
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/options/{ticker}"
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        result = data.get("optionChain", {}).get("result", [])
        if not result:
            return None

        options = result[0].get("options", [])
        if not options:
            return None

        calls = options[0].get("calls", [])
        puts = options[0].get("puts", [])

        call_vol = sum(c.get("volume", 0) or 0 for c in calls)
        put_vol = sum(p.get("volume", 0) or 0 for p in puts)

        if call_vol == 0:
            return None

        return round(put_vol / call_vol, 3)
    except Exception:
        return None
