"""RSS headline fetching — returns title + URL pairs."""
import concurrent.futures
import feedparser
from urllib.parse import urlencode


GOOGLE_NEWS_GENERAL_QUERIES = [
    "India",
    "World",
    "India politics",
]

GOOGLE_NEWS_ECONOMIC_QUERIES = [
    "India economy market",
    "Global markets",
    "crude oil gold commodity",
]

GENERAL_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.thehindu.com/news/national/feeder/default.rss",
]

INVESTMENT_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
]


def _build_google_news_url(query, hl="en-IN", gl="IN", ceid="IN:en"):
    params = urlencode({"q": query, "hl": hl, "gl": gl, "ceid": ceid})
    return f"https://news.google.com/rss/search?{params}"


def _fetch_one(url, per_feed):
    out = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:per_feed]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if title and link:
                out.append({"title": title, "url": link})
    except Exception:
        pass
    return out


def _fetch_all(feeds, per_feed=6, cap=50):
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(feeds), 8)) as ex:
        for result in ex.map(lambda u: _fetch_one(u, per_feed), feeds):
            items.extend(result)

    seen, unique = set(), []
    for item in items:
        key = item["title"].lower()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:cap]


def get_general_headlines():
    urls = [_build_google_news_url(q) for q in GOOGLE_NEWS_GENERAL_QUERIES]
    return _fetch_all(GENERAL_FEEDS + urls, per_feed=6, cap=50)


def get_investment_headlines():
    urls = [_build_google_news_url(q) for q in GOOGLE_NEWS_ECONOMIC_QUERIES]
    return _fetch_all(INVESTMENT_FEEDS + urls, per_feed=6, cap=50)
