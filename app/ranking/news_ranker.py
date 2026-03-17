from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.models.article import Article
from app.utils.text_utils import article_topic_text, extract_topics, primary_topic


def _hours_since(article: Article, now: datetime) -> float:
    delta = now.astimezone(timezone.utc) - article.sort_time.astimezone(timezone.utc)
    return max(delta.total_seconds() / 3600, 0.0)


def _keyword_boost(article: Article) -> int:
    return len(extract_topics(article_topic_text(article))) * 6


def _score_main_issue(article: Article, now: datetime) -> float:
    recency_bonus = max(0.0, 72.0 - _hours_since(article, now))
    return (
        (100.0 if article.in_window else 0.0)
        + recency_bonus
        + _keyword_boost(article)
        + max(0, 20 - int(article.metadata.get("rank", 99)))
    )


def _score_news(article: Article, now: datetime) -> float:
    recency_bonus = max(0.0, 48.0 - _hours_since(article, now))
    source_bonus = {"rss": 18.0, "github": 14.0}.get(article.source, 8.0)
    richness_bonus = min(len(article.summary or ""), 180) / 20
    github_bonus = min(int(article.metadata.get("stars_today") or 0) / 200, 12.0)
    return (
        (60.0 if article.in_window else 0.0)
        + recency_bonus
        + source_bonus
        + richness_bonus
        + github_bonus
        + _keyword_boost(article)
    )


def select_main_issue(articles: list[Article]) -> Article | None:
    if not articles:
        return None

    now = datetime.now(timezone.utc)
    in_window_articles = [article for article in articles if article.in_window]
    pool = in_window_articles or articles
    return max(pool, key=lambda article: _score_main_issue(article, now))


def select_briefing_items(articles: list[Article], limit: int = 3) -> list[Article]:
    if not articles:
        return []

    now = datetime.now(timezone.utc)
    ranked = sorted(
        articles,
        key=lambda article: (_score_news(article, now), article.sort_time),
        reverse=True,
    )

    selected: list[Article] = []
    selected_urls: set[str] = set()
    used_topics: set[str] = set()
    source_counts: Counter[str] = Counter()

    for enforce_topic_diversity in (True, False):
        for article in ranked:
            if article.url in selected_urls:
                continue

            if source_counts[article.source] >= 2 and len(ranked) > limit:
                continue

            topic = primary_topic(article)
            if enforce_topic_diversity and topic in used_topics and len(ranked) > len(selected):
                continue

            selected.append(article)
            selected_urls.add(article.url)
            source_counts[article.source] += 1
            if topic:
                used_topics.add(topic)

            if len(selected) == limit:
                return selected

    return selected
