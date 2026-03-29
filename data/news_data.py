"""Fetch news headlines from GDELT and RSS feeds."""

import time
import requests
from bs4 import BeautifulSoup
from config import RSS_FEEDS, NEWS_KEYWORDS, NEWS_CACHE_TTL_SECONDS

# ── Cache ────────────────────────────────────────────────────────────────────

_news_cache: dict[str, tuple[float, list[dict]]] = {}
_gdelt_tone_cache: dict[str, tuple[float, float | None]] = {}


def fetch_gdelt_articles(query: str, max_records: int = 25) -> list[dict]:
    """Fetch articles from GDELT DOC API with pre-scored tone."""
    cache_key = f"gdelt_{query}"
    now = time.time()

    if cache_key in _news_cache:
        ts, articles = _news_cache[cache_key]
        if now - ts < NEWS_CACHE_TTL_SECONDS:
            return articles

    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": f"{query} sourcelang:English",
            "mode": "artlist",
            "maxrecords": str(max_records),
            "format": "json",
            "sort": "datedesc",
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for art in data.get("articles", []):
            articles.append({
                "title": art.get("title", ""),
                "url": art.get("url", ""),
                "source": art.get("domain", ""),
                "date": art.get("seendate", ""),
                "tone": art.get("tone", 0),
                "language": art.get("language", "English"),
            })

        _news_cache[cache_key] = (now, articles)
        return articles
    except Exception:
        return _news_cache.get(cache_key, (0, []))[1]


def fetch_gdelt_tone(query: str) -> float | None:
    """Get average tone for a query from GDELT timeline."""
    cache_key = f"tone_{query}"
    now = time.time()

    if cache_key in _gdelt_tone_cache:
        ts, tone = _gdelt_tone_cache[cache_key]
        if now - ts < NEWS_CACHE_TTL_SECONDS:
            return tone

    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": f"{query} sourcelang:English",
            "mode": "timelinetone",
            "format": "json",
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        timeline = data.get("timeline", [])
        if not timeline or not timeline[0].get("data"):
            return None

        points = timeline[0]["data"]
        tones = [p.get("value", 0) for p in points[-10:]]
        avg_tone = sum(tones) / len(tones) if tones else 0
        _gdelt_tone_cache[cache_key] = (now, avg_tone)
        return avg_tone
    except Exception:
        return _gdelt_tone_cache.get(cache_key, (0, None))[1]


def fetch_rss_headlines(max_per_feed: int = 10) -> list[dict]:
    """Fetch latest headlines from RSS feeds using requests + BeautifulSoup."""
    cache_key = "rss_all"
    now = time.time()

    if cache_key in _news_cache:
        ts, headlines = _news_cache[cache_key]
        if now - ts < NEWS_CACHE_TTL_SECONDS:
            return headlines

    headlines = []
    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SentimentTracker/1.0)"
            })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "xml" if "xml" in resp.headers.get("content-type", "") else "html.parser")

            items = soup.find_all("item")[:max_per_feed]
            feed_title = ""
            channel = soup.find("channel")
            if channel:
                title_tag = channel.find("title")
                if title_tag:
                    feed_title = title_tag.get_text(strip=True)

            for item in items:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                headlines.append({
                    "title": title.get_text(strip=True) if title else "",
                    "url": link.get_text(strip=True) if link else "",
                    "source": feed_title or feed_url,
                    "date": pub_date.get_text(strip=True) if pub_date else "",
                    "tone": None,
                })
        except Exception:
            continue

    _news_cache[cache_key] = (now, headlines)
    return headlines


def get_news_for_category(category: str) -> list[dict]:
    """Get news articles for a specific asset category using GDELT."""
    query = NEWS_KEYWORDS.get(category, "financial markets")
    return fetch_gdelt_articles(query)
