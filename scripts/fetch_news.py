"""
Fetch recent news from RSS/Atom feeds, grouped by topic.

Run:  python scripts/fetch_news.py            (AI feeds, default)
      python scripts/fetch_news.py devops     (DevOps feeds)
"""
import calendar
import sys
from datetime import datetime, timedelta, timezone

import feedparser

# Topic -> {source name: feed URL}. Add or remove feeds here.
FEEDS_BY_TOPIC = {
    "ai": {
        "OpenAI": "https://openai.com/news/rss.xml",
        "Google AI": "https://blog.google/technology/ai/rss/",
        "Hugging Face": "https://huggingface.co/blog/feed.xml",
        "Hacker News (AI, 100+ points)": "https://hnrss.org/newest?q=AI&points=100",
        "arXiv cs.AI": "https://rss.arxiv.org/rss/cs.AI",
    },
    "devops": {
        # Official project and vendor blogs
        "Kubernetes Blog": "https://kubernetes.io/feed.xml",
        "CNCF Blog": "https://www.cncf.io/feed/",
        "AWS DevOps Blog": "https://aws.amazon.com/blogs/devops/feed/",
        "GitHub Changelog": "https://github.blog/changelog/feed/",
        "Docker Blog": "https://www.docker.com/blog/feed/",
        "HashiCorp Blog": "https://www.hashicorp.com/blog/feed.xml",
        # Industry news
        "The New Stack": "https://thenewstack.io/feed/",
        # What engineers are discussing
        "Hacker News (Kubernetes, 50+ points)": "https://hnrss.org/newest?q=kubernetes&points=50",
        "Hacker News (DevOps, 50+ points)": "https://hnrss.org/newest?q=devops&points=50",
        # Tool releases (every GitHub repo has a releases.atom feed)
        "Kubernetes releases": "https://github.com/kubernetes/kubernetes/releases.atom",
        "Terraform releases": "https://github.com/hashicorp/terraform/releases.atom",
        "Argo CD releases": "https://github.com/argoproj/argo-cd/releases.atom",
    },
}

LOOKBACK_HOURS = 24
MAX_PER_FEED = 5
USER_AGENT = "daily-updates-bot/0.2 (+https://purudevops09.github.io/purushoth/)"


def published_time(entry):
    """Return the entry's publish time as a UTC datetime, or None if missing."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    # feedparser gives UTC struct_time; timegm keeps it in UTC (mktime would not).
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def fetch_all(feeds):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items = []

    for source, url in feeds.items():
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
                "summary": entry.get("summary", "")[:600],
            })
            count += 1
            if count >= MAX_PER_FEED:
                break

        print(f"[OK]   {source}: {count} new item(s)")

    return items


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "ai"
    if topic not in FEEDS_BY_TOPIC:
        print(f"Unknown topic '{topic}'. Choose from: {', '.join(FEEDS_BY_TOPIC)}")
        return 1

    items = fetch_all(FEEDS_BY_TOPIC[topic])
    print(f"\nFound {len(items)} {topic} item(s) from the last {LOOKBACK_HOURS} hours:\n")
    for i, item in enumerate(items, start=1):
        print(f"{i}. [{item['source']}] {item['title']}")
        print(f"   {item['link']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
