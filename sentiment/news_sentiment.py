"""News sentiment scoring using GDELT tone + TextBlob fallback."""

from textblob import TextBlob

from data.news_data import get_news_for_category, fetch_gdelt_tone, fetch_rss_headlines
from config import NEWS_KEYWORDS


def score_headline_textblob(text: str) -> float:
    """Score a headline using TextBlob polarity (-1 to +1)."""
    try:
        blob = TextBlob(text)
        return round(blob.sentiment.polarity, 3)
    except Exception:
        return 0.0


def normalize_gdelt_tone(tone: float) -> float:
    """Normalize GDELT tone (-100 to +100, typical -10 to +10) to -1 to +1."""
    return max(-1.0, min(1.0, tone / 10.0))


def get_category_news_sentiment(category: str) -> dict:
    """Get blended news sentiment score for an asset category."""
    scores = []
    articles = []

    # 1. GDELT articles (pre-scored)
    gdelt_articles = get_news_for_category(category)
    for art in gdelt_articles:
        tone = art.get("tone", 0)
        if tone is not None and tone != 0:
            normalized = normalize_gdelt_tone(tone)
            scores.append(normalized)
            art["normalized_score"] = normalized
            articles.append(art)

    # 2. GDELT timeline tone (aggregate)
    query = NEWS_KEYWORDS.get(category, "financial markets")
    timeline_tone = fetch_gdelt_tone(query)
    if timeline_tone is not None:
        scores.append(normalize_gdelt_tone(timeline_tone))

    # 3. RSS headlines (scored with TextBlob as fallback)
    rss = fetch_rss_headlines()
    # Filter RSS by category keywords
    keywords = NEWS_KEYWORDS.get(category, "").lower().split()
    for headline in rss:
        title = headline.get("title", "").lower()
        if any(kw in title for kw in keywords):
            tb_score = score_headline_textblob(headline["title"])
            scores.append(tb_score)
            headline["normalized_score"] = tb_score
            articles.append(headline)

    if not scores:
        return {
            "score": 0,
            "label": "no data",
            "num_sources": 0,
            "articles": [],
        }

    avg_score = sum(scores) / len(scores)

    if avg_score > 0.3:
        label = "positive"
    elif avg_score > 0.1:
        label = "slightly positive"
    elif avg_score > -0.1:
        label = "neutral"
    elif avg_score > -0.3:
        label = "slightly negative"
    else:
        label = "negative"

    return {
        "score": round(avg_score, 3),
        "label": label,
        "num_sources": len(scores),
        "articles": articles[:10],  # Top 10 for display
    }


def get_all_categories_sentiment() -> dict[str, dict]:
    """Get news sentiment for all asset categories."""
    results = {}
    for category in NEWS_KEYWORDS:
        results[category] = get_category_news_sentiment(category)
    return results
