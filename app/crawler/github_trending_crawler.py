from __future__ import annotations

import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup, Tag

from app.models.article import Article
from app.utils.text_utils import clean_text


TRENDING_URL = "https://github.com/trending?since=daily"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AIBriefingBot/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_stars_today(card: Tag) -> int | None:
    text = clean_text(card.get_text(" ", strip=True))
    if not text:
        return None
    match = re.search(r"([\d,]+)\s+stars?\s+today", text, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def fetch_github_trending(
    window_start: datetime,
    window_end: datetime,
    limit: int = 10,
    timeout: int = 15,
) -> list[Article]:
    response = requests.get(TRENDING_URL, headers=HEADERS, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select("article.Box-row")

    collected_at = datetime.now(timezone.utc)
    published_at = window_end.astimezone(timezone.utc)
    articles: list[Article] = []

    for rank, card in enumerate(cards[:limit], start=1):
        title_anchor = card.select_one("h2 a")
        if title_anchor is None:
            continue

        href = (title_anchor.get("href") or "").strip()
        if not href.startswith("/"):
            continue

        repo_name = href.strip("/")
        description_tag = card.select_one("p")
        language_tag = card.select_one("[itemprop='programmingLanguage']")

        description = (
            clean_text(description_tag.get_text(" ", strip=True))
            if description_tag
            else None
        )
        language = (
            clean_text(language_tag.get_text(" ", strip=True)) if language_tag else None
        )

        articles.append(
            Article(
                source="github",
                source_type="trending",
                title=repo_name,
                url=f"https://github.com/{repo_name}",
                published_at=published_at,
                collected_at=collected_at,
                author=repo_name.split("/", 1)[0] if "/" in repo_name else None,
                summary=description,
                raw_content=description,
                in_window=True,
                metadata={
                    "language": language,
                    "stars_today": parse_stars_today(card),
                    "rank": rank,
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                },
            )
        )

    return articles
