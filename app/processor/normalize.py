from __future__ import annotations

from app.models.article import Article
from app.utils.text_utils import canonicalize_url, clean_text, strip_html, truncate
from app.utils.time_utils import ensure_timezone


def normalize_article(article: Article) -> Article:
    article.title = clean_text(article.title)
    article.url = canonicalize_url(article.url)
    article.author = clean_text(article.author)

    if article.summary:
        article.summary = truncate(strip_html(article.summary), 420)
    if article.raw_content:
        article.raw_content = truncate(strip_html(article.raw_content), 2400)

    if article.published_at:
        article.published_at = ensure_timezone(article.published_at)
    article.collected_at = ensure_timezone(article.collected_at)
    return article


def normalize_articles(articles: list[Article]) -> list[Article]:
    normalized = [
        normalize_article(article)
        for article in articles
        if clean_text(article.title) and canonicalize_url(article.url)
    ]
    normalized.sort(key=lambda article: article.sort_time, reverse=True)
    return normalized
