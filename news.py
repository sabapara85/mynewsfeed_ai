"""RSS headline fetching — parallel, fault-tolerant, with Google News integration."""
import concurrent.futures
import feedparser

# --- Google News Search Queries ---
# These act as a safety net, capturing stories from a wide range of sources.
# We use the 'hl', 'gl', and 'ceid' parameters to focus on India and English.

GOOGLE_NEWS_GENERAL_QUERIES = [
    "India",
    "India politics election",
    "India foreign diplomacy",
    "India technology ai startup",
    "World",
]

GOOGLE_NEWS_ECONOMIC_QUERIES = [
    "India economy market stock",
    "India business corporate",
    "Global markets",
    "crude oil gold commodity",
    "US Federal Reserve inflation",
]

# --- Direct Publisher Feeds ---
# These provide durable, primary-source articles from key outlets.

GENERAL_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.thehindu.com/news/national/feeder/default.rss",
    "https://indianexpress.com/section/india/feed/",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.bbci.co.uk/news/india/rss.xml",
]

INVESTMENT_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.business-standard.com/rss/markets-106.rss",
]

# --- Helper Functions ---

def _build_google_news_url(query: str, hl: str = "en-IN", gl: str = "IN", ceid: str = "IN:en") -> str:
    """Builds a Google News RSS search URL for a given query."""
    from urllib.parse import urlencode
    params = urlencode({
        "q": query,
        "hl": hl,
        "gl": gl,
        "ceid": ceid,
    })
    return f"https://news.google.com/rss/search?{params}"

def _fetch_one(url: str, per_feed: int):
    """Fetches and parses a single RSS feed."""
    out = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:per_feed]:
            title = (entry.get("title") or "").strip()
            if title:
                out.append(title)
    except Exception:
        pass
    return out

def _fetch_all(feeds, per_feed=8, cap=40):
    """Fetches all feeds in parallel and deduplicates the results."""
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(feeds), 1)) as ex:
        for result in ex.map(lambda u: _fetch_one(u, per_feed), feeds):
            items.extend(result)

    seen, unique = set(), []
    for t in items:
        # Basic deduplication based on the first 80 characters of the title
        key = t.lower()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique[:cap]

# --- Public Functions ---

def get_general_headlines():
    """Fetches general news from both Google News and direct publisher feeds."""
    # Build URLs for Google News queries
    google_urls = [
        _build_google_news_url(q) for q in GOOGLE_NEWS_GENERAL_QUERIES
    ]
    all_feeds = GENERAL_FEEDS + google_urls
    return _fetch_all(all_feeds, per_feed=6, cap=50)

def get_investment_headlines():
    """Fetches economic news from both Google News and direct publisher feeds."""
    # Build URLs for Google News queries
    google_urls = [
        _build_google_news_url(q) for q in GOOGLE_NEWS_ECONOMIC_QUERIES
    ]
    all_feeds = INVESTMENT_FEEDS + google_urls
    return _fetch_all(all_feeds, per_feed=6, cap=50)