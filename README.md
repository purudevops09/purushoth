# Daily DevOps & AI Updates

Collects the latest DevOps and AI news from RSS feeds and publishes a
colorful reading page every morning to GitHub Pages. No API key needed.

Live site: https://purudevops09.github.io/purushoth/digests/

## Folder structure

    devops-repo/
    ├── .github/workflows/daily-digest.yml   GitHub Actions: runs daily, deploys site
    ├── _config.yml                          Jekyll site settings
    ├── index.md                             Home page
    ├── _posts/                              Blog posts (Markdown)
    ├── digests/                             Generated daily pages (one per day)
    ├── scripts/
    │   ├── fetch_news.py                    Reads RSS feeds (edit FEEDS_BY_TOPIC here)
    │   └── build_digest.py                  Builds the HTML reading page
    ├── requirements.txt                     Python dependencies
    └── .gitignore

## Run locally (Windows cmd)

    python -m venv .venv
    .venv\Scripts\activate.bat
    pip install -r requirements.txt
    python scripts\build_digest.py                 DevOps, last 24 hours
    python scripts\build_digest.py --topic all     DevOps + AI
    python scripts\build_digest.py --hours 72      look back 3 days

## Automation

The workflow runs every day at 02:30 UTC (08:00 IST), builds the digest,
commits it to `digests/`, and deploys the site. Run it manually from the
Actions tab with "Run workflow".
