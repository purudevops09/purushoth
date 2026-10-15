"""
Step 2: Fetch AI news from RSS feeds published in the last 24 hours.

Run:  python scripts/fetch_news.py
"""
import calendar
from datetime import datetime, timedelta, timezone

import feedparser

# Source name -> RSS feed URL. Add or remove feeds here.
FEEDS = {
    "OpenAI": "https://openai.com/news/rss.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "Hacker News (AI, 100+ points)": "https://hnrss.org/newest?q=AI&points=100",
    "arXiv cs.AI": "https://rss.arxiv.org/rss/cs.AI",
}

LOOKBACK_HOURS = 24
MAX_PER_FEED = 5
USER_AGENT = "daily-ai-updates-bot/0.1 (+https://purudevops09.github.io)"


def published_time(entry):
    """Return the entry's publish time as a UTC datetime, or None if missing."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    # feedparser gives UTC struct_time; timegm keeps it in UTC (mktime would not).
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def fetch_all():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items = []

    for source, url in FEEDS.items():
        feed = feedparser.parse(url, agent=USER_AGENT)

        # bozo = feed was malformed or unreachable. Report it, but keep going.
        if feed.bozo and not feed.entries:
            print(f"[WARN] {source}: could not read feed ({feed.bozo_exception})")
            continue

        count = 0
        for entry in feed.entries:
            when = published_time(entry)
            if when is None or when < cutoff:
                continue
            items.append({
                "source": source,
                "title": entry.get("title", "(no title)").strip(),
                "link": entry.get("link", ""),
                "published": when.isoformat(),
            })
            count += 1
            if count >= MAX_PER_FEED:
                break

        print(f"[OK]   {source}: {count} new item(s)")

    return items


def main():
    items = fetch_all()
    print(f"\nFound {len(items)} item(s) from the last {LOOKBACK_HOURS} hours:\n")
    for i, item in enumerate(items, start=1):
        print(f"{i}. [{item['source']}] {item['title']}")
        print(f"   {item['link']}")


if __name__ == "__main__":
    main()