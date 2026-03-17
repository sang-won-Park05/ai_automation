from __future__ import annotations

from app.models.article import Article
from app.utils.text_utils import canonicalize_url, normalize_title, title_similarity


def _quality_score(article: Article) -> tuple[int, int, int, float]:
    stars_today = int(article.metadata.get("stars_today") or 0)
    source_priority = {"rss": 3, "huggingface": 2, "github": 1}.get(article.source, 0)
    summary_length = len(article.summary or "") + len(article.raw_content or "")
    return (
        1 if article.in_window else 0,
        source_priority,
        summary_length,
        float(stars_today),
    )


def deduplicate_articles(
    articles: list[Article],
    fuzzy_threshold: float = 0.92,
) -> list[Article]:
    deduplicated: list[Article] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for article in sorted(articles, key=_quality_score, reverse=True):
        url_key = canonicalize_url(article.url)
        title_key = normalize_title(article.title)
        if not url_key or not title_key:
            continue

        if url_key in seen_urls or title_key in seen_titles:
            continue

        if any(title_similarity(title_key, existing) >= fuzzy_threshold for existing in seen_titles):
            continue

        seen_urls.add(url_key)
        seen_titles.append(title_key)
        deduplicated.append(article)

    deduplicated.sort(key=lambda article: article.sort_time, reverse=True)
    return deduplicated
