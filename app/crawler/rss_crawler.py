from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
import requests

from app.models.article import Article
from app.utils.text_utils import clean_text, strip_html
from app.utils.time_utils import is_in_window, parse_datetime


LOGGER = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIBriefingBot/1.0)"}


def parse_rss_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)

    for key in ("published", "updated", "created"):
        parsed = parse_datetime(entry.get(key))
        if parsed:
            return parsed

    return None


def fetch_rss_articles(
    window_start: datetime,
    window_end: datetime,
    feed_urls: list[str],
    limit_per_feed: int = 4,
    timeout: int = 15,
) -> list[Article]:
    collected_at = datetime.now(timezone.utc)
    seen_urls: set[str] = set()
    articles: list[Article] = []

    for feed_url in feed_urls:
        try:
            response = requests.get(feed_url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("RSS 피드 실패: %s (%s)", feed_url, exc)
            continue

        feed = feedparser.parse(response.content)
        feed_title = clean_text(feed.feed.get("title")) if getattr(feed, "feed", None) else None

        for entry in feed.entries[:limit_per_feed]:
            title = clean_text(entry.get("title"))
            url = (entry.get("link") or "").strip()
            if not title or not url or url in seen_urls:
                continue

            seen_urls.add(url)
            summary = strip_html(entry.get("summary") or entry.get("description"))
            published_at = parse_rss_datetime(entry)

            articles.append(
                Article(
                    source="rss",
                    source_type="news",
                    title=title,
                    url=url,
                    published_at=published_at,
                    collected_at=collected_at,
                    author=clean_text(entry.get("author")),
                    summary=summary,
                    raw_content=summary,
                    in_window=is_in_window(published_at, window_start, window_end),
                    metadata={"feed_title": feed_title, "feed_url": feed_url},
                )
            )

    return articles
