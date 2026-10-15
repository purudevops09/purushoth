"""
Build a colorful, local HTML reading page from today's news. No API key needed.

Run:  python scripts/build_digest.py                  (DevOps, last 24 hours)
      python scripts/build_digest.py --topic ai
      python scripts/build_digest.py --topic all --hours 48
Output: digests/YYYY-MM-DD-<topic>.html  (opens in your browser automatically)
        digests/index.html               (list of all saved digests)
"""
import argparse
import html
import re
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import fetch_news
from fetch_news import FEEDS_BY_TOPIC, fetch_all

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "digests"

# Source name -> category shown on the page. Unknown sources go to "Other".
CATEGORY_BY_SOURCE = {
    "Kubernetes Blog": "Kubernetes",
    "CNCF Blog": "Cloud native",
    "AWS DevOps Blog": "Cloud",
    "GitHub Changelog": "CI/CD and tooling",
    "Docker Blog": "Containers",
    "HashiCorp Blog": "Infrastructure as code",
    "The New Stack": "Industry",
    "Hacker News (Kubernetes, 50+ points)": "Community",
    "Hacker News (DevOps, 50+ points)": "Community",
    "Hacker News (AI, 100+ points)": "Community",
    "Kubernetes releases": "Releases",
    "Terraform releases": "Releases",
    "Argo CD releases": "Releases",
    "OpenAI": "AI labs",
    "Google AI": "AI labs",
    "Hugging Face": "AI labs",
    "arXiv cs.AI": "Research",
}

# Category -> hue (0-360). The page derives light and dark colors from the hue.
HUE_BY_CATEGORY = {
    "Releases": 212,
    "Kubernetes": 250,
    "Cloud native": 182,
    "Cloud": 28,
    "CI/CD and tooling": 148,
    "Containers": 200,
    "Infrastructure as code": 280,
    "Industry": 46,
    "Community": 335,
    "AI labs": 4,
    "Research": 95,
    "Other": 220,
}


def clean_summary(raw, limit=280):
    """Strip HTML tags and entities, collapse whitespace, trim to a readable length."""
    text = re.sub(r"<[^>]*>?", " ", raw or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text


def time_ago(iso, now):
    hours = int((now - datetime.fromisoformat(iso)).total_seconds() // 3600)
    if hours < 1:
        return "just now"
    return f"{hours}h ago" if hours < 48 else f"{hours // 24}d ago"


def render(items, topic, hours, now):
    # Count per category, biggest first, for the mix bar and filters.
    counts = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    order = sorted(counts, key=lambda c: (-counts[c], c))

    segments = "".join(
        f'<span class="seg" style="--h:{HUE_BY_CATEGORY[c]};flex:{counts[c]}"></span>'
        for c in order
    )
    chips = '<button class="chip active" data-cat="all">All <b>{}</b></button>'.format(len(items))
    chips += "".join(
        f'<button class="chip" data-cat="{html.escape(c)}" style="--h:{HUE_BY_CATEGORY[c]}">'
        f'<i></i>{html.escape(c)} <b>{counts[c]}</b></button>'
        for c in order
    )

    rows = []
    for item in sorted(items, key=lambda i: i["published"], reverse=True):
        cat = item["category"]
        summary = clean_summary(item.get("summary", ""))
        rows.append(f"""
      <article class="item" data-cat="{html.escape(cat)}" data-link="{html.escape(item['link'])}" style="--h:{HUE_BY_CATEGORY[cat]}">
        <div class="meta"><span class="cat">{html.escape(cat)}</span><span>{html.escape(item['source'])}</span><span>{time_ago(item['published'], now)}</span></div>
        <h2><a href="{html.escape(item['link'])}" target="_blank" rel="noopener">{html.escape(item['title'])}</a></h2>
        {f'<p>{html.escape(summary)}</p>' if summary else ''}
        <button class="read-btn" type="button">Mark as read</button>
      </article>""")

    empty = "" if items else (
        '<p class="empty">No new stories in the last {} hours. Try <code>--hours 48</code> '
        "for a wider window.</p>".format(hours)
    )
    title = {"devops": "DevOps reading list", "ai": "AI reading list"}.get(topic, "Daily reading list")

    return (PAGE
            .replace("__TITLE__", title)
            .replace("__DATE__", f"{now:%A, %d %B %Y}")
            .replace("__SUB__", f"{len(items)} stories from the last {hours} hours, fetched {now:%H:%M} UTC")
            .replace("__SEGMENTS__", segments)
            .replace("__CHIPS__", chips)
            .replace("__ROWS__", "".join(rows) + empty))


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #f5f7fb; --surface: #ffffff; --ink: #1a2130; --muted: #5a6476;
    --line: #dfe4ee; --l: 42%; --s: 62%;
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #121620; --surface: #1a1f2b; --ink: #e7eaf0; --muted: #9aa3b5;
            --line: #2a3142; --l: 70%; --s: 70%; color-scheme: dark; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font: 16px/1.6 "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }

  header h1 { font-size: 2.6rem; line-height: 1.1; margin: 0 0 6px; font-weight: 700; letter-spacing: -0.02em; }
  header .date { font-size: 1.15rem; font-weight: 500; margin: 0; }
  header .sub { color: var(--muted); margin: 4px 0 28px; font-size: 0.95rem; }

  .mix { display: flex; height: 14px; border-radius: 7px; overflow: hidden; gap: 3px; margin-bottom: 18px; }
  .seg { background: hsl(var(--h) var(--s) var(--l)); min-width: 6px; }

  .controls { position: sticky; top: 0; z-index: 2; background: var(--bg);
              padding: 12px 0; border-bottom: 1px solid var(--line); margin-bottom: 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .chip { font: inherit; font-size: 0.85rem; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
          padding: 4px 12px; border-radius: 999px; border: 1px solid var(--line);
          background: var(--surface); color: var(--ink); }
  .chip i { width: 9px; height: 9px; border-radius: 50%; background: hsl(var(--h) var(--s) var(--l)); }
  .chip b { font-weight: 600; color: var(--muted); }
  .chip.active { border-color: var(--ink); box-shadow: inset 0 0 0 1px var(--ink); }
  .chip:focus-visible, .read-btn:focus-visible, a:focus-visible, input:focus-visible { outline: 2px solid hsl(212 80% 55%); outline-offset: 2px; }
  .tools { display: flex; gap: 10px; align-items: center; }
  input[type=search] { flex: 1; font: inherit; padding: 8px 12px; border-radius: 8px;
                       border: 1px solid var(--line); background: var(--surface); color: var(--ink); }
  label.hide { font-size: 0.85rem; color: var(--muted); display: flex; gap: 6px; align-items: center; white-space: nowrap; }

  .item { position: relative; padding: 20px 0 20px 20px; border-bottom: 1px solid var(--line); }
  .item::before { content: ""; position: absolute; left: 0; top: 22px; bottom: 22px; width: 4px;
                  border-radius: 2px; background: hsl(var(--h) var(--s) var(--l)); }
  .meta { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 0.82rem; color: var(--muted); }
  .meta .cat { color: hsl(var(--h) var(--s) var(--l)); font-weight: 600; }
  .item h2 { font-size: 1.18rem; line-height: 1.35; margin: 4px 0 6px; font-weight: 600; }
  .item h2 a { color: var(--ink); text-decoration: none; }
  .item h2 a:hover { text-decoration: underline; text-decoration-color: hsl(var(--h) var(--s) var(--l)); text-underline-offset: 3px; }
  .item p { margin: 0 0 8px; color: var(--muted); max-width: 68ch; }
  .read-btn { font: inherit; font-size: 0.8rem; background: none; border: 0; padding: 0;
              color: var(--muted); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
  .item.read { opacity: 0.45; }
  .item.read .read-btn::after { content: " (undo)"; }
  .hidden { display: none; }
  .empty { color: var(--muted); padding: 32px 0; }
  @media (max-width: 520px) { header h1 { font-size: 2rem; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>__TITLE__</h1>
    <p class="date">__DATE__</p>
    <p class="sub">__SUB__</p>
    <div class="mix" aria-hidden="true">__SEGMENTS__</div>
  </header>
  <div class="controls">
    <div class="chips">__CHIPS__</div>
    <div class="tools">
      <input type="search" id="q" placeholder="Search titles and summaries" aria-label="Search">
      <label class="hide"><input type="checkbox" id="hideRead"> Hide read</label>
    </div>
  </div>
  <main id="list">__ROWS__
  </main>
</div>
<script>
  const KEY = "digest-read-links";
  let read = new Set();
  try { read = new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); } catch (e) {}
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify([...read])); } catch (e) {} };

  const items = [...document.querySelectorAll(".item")];
  const q = document.getElementById("q");
  const hideRead = document.getElementById("hideRead");
  let cat = "all";

  function apply() {
    const term = q.value.trim().toLowerCase();
    for (const el of items) {
      const isRead = read.has(el.dataset.link);
      el.classList.toggle("read", isRead);
      el.querySelector(".read-btn").textContent = isRead ? "Read" : "Mark as read";
      const show = (cat === "all" || el.dataset.cat === cat)
        && (!term || el.textContent.toLowerCase().includes(term))
        && !(hideRead.checked && isRead);
      el.classList.toggle("hidden", !show);
    }
  }

  document.querySelectorAll(".chip").forEach(chip => chip.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    cat = chip.dataset.cat;
    apply();
  }));

  for (const el of items) {
    el.querySelector(".read-btn").addEventListener("click", () => {
      const link = el.dataset.link;
      read.has(link) ? read.delete(link) : read.add(link);
      save(); apply();
    });
    el.querySelector("h2 a").addEventListener("click", () => { read.add(el.dataset.link); save(); apply(); });
  }
  q.addEventListener("input", apply);
  hideRead.addEventListener("change", apply);
  apply();
</script>
</body>
</html>
"""


INDEX_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily reading lists</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root { --bg: #f5f7fb; --ink: #1a2130; --muted: #5a6476; --line: #dfe4ee; color-scheme: light; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #121620; --ink: #e7eaf0; --muted: #9aa3b5; --line: #2a3142; color-scheme: dark; }
  }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font: 16px/1.6 "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }
  h1 { font-size: 2.4rem; line-height: 1.1; margin: 0 0 6px; letter-spacing: -0.02em; }
  .sub { color: var(--muted); margin: 0 0 24px; }
  ul { list-style: none; padding: 0; margin: 0; }
  li { border-bottom: 1px solid var(--line); }
  li a { display: flex; justify-content: space-between; gap: 16px; padding: 14px 0;
         color: var(--ink); text-decoration: none; font-weight: 600; }
  li a span { color: var(--muted); font-weight: 400; }
  li a:hover { text-decoration: underline; text-underline-offset: 3px; }
  a:focus-visible { outline: 2px solid hsl(212 80% 55%); outline-offset: 2px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Daily reading lists</h1>
  <p class="sub">DevOps and AI news, collected every morning. Newest first.</p>
  <ul>__LINKS__</ul>
</div>
</body>
</html>
"""

TOPIC_LABELS = {"devops": "DevOps", "ai": "AI", "all": "DevOps + AI"}


def write_index(out_dir):
    """Write digests/index.html listing every saved digest, newest first."""
    pages = sorted(out_dir.glob("????-??-??-*.html"), reverse=True)
    links = []
    for page in pages:
        date_part, topic = page.stem[:10], page.stem[11:]
        try:
            label = datetime.strptime(date_part, "%Y-%m-%d").strftime("%A, %d %B %Y")
        except ValueError:
            continue
        links.append(
            f'<li><a href="{html.escape(page.name)}">{label}'
            f'<span>{html.escape(TOPIC_LABELS.get(topic, topic))}</span></a></li>'
        )
    (out_dir / "index.html").write_text(
        INDEX_PAGE.replace("__LINKS__", "".join(links)), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="Build a local HTML reading page.")
    parser.add_argument("--topic", choices=["devops", "ai", "all"], default="devops")
    parser.add_argument("--hours", type=int, default=24, help="how far back to look")
    parser.add_argument("--no-open", action="store_true", help="don't open the browser")
    args = parser.parse_args()

    fetch_news.LOOKBACK_HOURS = args.hours
    topics = ["devops", "ai"] if args.topic == "all" else [args.topic]

    items = []
    for t in topics:
        print(f"\nFetching {t} feeds...")
        items += fetch_all(FEEDS_BY_TOPIC[t])

    # Drop duplicates (the same link from two sources) and tag each with a category.
    unique = {}
    for item in items:
        if item["link"] and item["link"] not in unique:
            item["category"] = CATEGORY_BY_SOURCE.get(item["source"], "Other")
            unique[item["link"]] = item
    items = list(unique.values())

    now = datetime.now(timezone.utc)
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{now:%Y-%m-%d}-{args.topic}.html"
    out.write_text(render(items, args.topic, args.hours, now), encoding="utf-8")
    write_index(OUT_DIR)

    print(f"\n[DONE] {len(items)} stories -> {out}")
    if not args.no_open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
