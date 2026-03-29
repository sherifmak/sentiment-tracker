"""Central configuration for the Sentiment Trading Tracker."""

# ── Ticker Universe ──────────────────────────────────────────────────────────

TICKERS = {
    "sp500": {
        "label": "S&P & Indices",
        "symbols": {
            "^GSPC": "S&P 500",
            "SPY": "S&P 500 ETF",
            "^DJI": "Dow Jones",
            "^IXIC": "NASDAQ",
            "^RUT": "Russell 2000",
            "^VIX": "VIX",
            "XLK": "Tech Sector",
            "XLF": "Financials",
            "XLV": "Healthcare",
            "XLE": "Energy Sector",
            "XLI": "Industrials",
            "XLRE": "Real Estate",
        },
    },
    "oil_gas": {
        "label": "Oil & Gas",
        "symbols": {
            "XLE": "Energy ETF",
            "CL=F": "WTI Crude",
            "USO": "US Oil Fund",
            "BZ=F": "Brent Crude",
            "NG=F": "Natural Gas",
        },
    },
    "gold": {
        "label": "Gold",
        "symbols": {
            "GC=F": "Gold Futures",
            "GLD": "SPDR Gold ETF",
            "IAU": "iShares Gold",
            "SI=F": "Silver Futures",
        },
    },
    "defense": {
        "label": "EU Defense",
        "symbols": {
            "RNMBY": "Rheinmetall",
            "BAESY": "BAE Systems",
            "FINMY": "Leonardo",
            "THLLY": "Thales",
            "SAABY": "Saab",
        },
    },
    "fx": {
        "label": "FX Rates",
        "symbols": {
            "EURUSD=X": "EUR/USD",
            "GBPUSD=X": "GBP/USD",
            "JPY=X": "USD/JPY",
            "CHFUSD=X": "CHF/USD",
            "AUDUSD=X": "AUD/USD",
            "CADUSD=X": "CAD/USD",
            "DX-Y.NYB": "US Dollar Index",
        },
    },
}

# Flat list of all unique tickers
ALL_TICKERS = list(
    {sym for cat in TICKERS.values() for sym in cat["symbols"]}
)

# ── News Keywords per Category ───────────────────────────────────────────────

NEWS_KEYWORDS = {
    "sp500": "S&P 500 stock market Wall Street",
    "oil_gas": "oil prices crude OPEC energy",
    "gold": "gold prices bullion safe haven inflation",
    "defense": "European defense military spending NATO",
    "fx": "dollar exchange rate forex currency",
}

# ── Scoring Weights ──────────────────────────────────────────────────────────

COMPOSITE_WEIGHTS = {
    "technical": 0.40,
    "market_sentiment": 0.30,
    "news_sentiment": 0.20,
    "alignment_bonus": 0.10,
}

# ── Signal Thresholds ────────────────────────────────────────────────────────

SIGNAL_THRESHOLDS = {
    "strong_bullish": 0.6,
    "bullish": 0.25,
    "neutral": -0.25,
    "bearish": -0.6,
    # below -0.6 = strong_bearish
}

# ── VIX Zones ────────────────────────────────────────────────────────────────

VIX_ZONES = {
    "complacent": (0, 15),
    "normal": (15, 20),
    "elevated": (20, 30),
    "extreme_fear": (30, 100),
}

# ── Dashboard Settings ───────────────────────────────────────────────────────

REFRESH_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes
SLOW_REFRESH_INTERVAL_MS = 60 * 60 * 1000  # 1 hour
CACHE_TTL_SECONDS = 300  # 5 minutes
NEWS_CACHE_TTL_SECONDS = 1800  # 30 minutes

# ── RSS Feeds ────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
]
