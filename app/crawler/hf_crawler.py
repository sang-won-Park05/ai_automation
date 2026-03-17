from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup, Tag

from app.models.article import Article
from app.utils.text_utils import clean_text, strip_html, truncate
from app.utils.time_utils import KST, ensure_timezone, is_in_window, parse_datetime


LOGGER = logging.getLogger(__name__)
HF_BLOG_URL = "https://huggingface.co/blog"
BASE_URL = "https://huggingface.co"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIBriefingBot/1.0)"}

DATE_PATTERNS = [
    r"\babout \d+ hours? ago\b",
    r"\b\d+ hours? ago\b",
    r"\b\d+ minutes? ago\b",
    r"\b\d+ days? ago\b",
    r"\b[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4}\b",
    r"\b[A-Z][a-z]{2,8}\s+\d{1,2}\b",
]


def parse_hf_date(raw_value: str | None, reference: datetime | None = None) -> datetime | None:
    if not raw_value:
        return None

    text = raw_value.strip()
    if not text:
        return None

    lower = text.lower()
    reference = ensure_timezone(reference or datetime.now(KST), KST).astimezone(KST)

    relative_patterns = (
        (r"about\s+(\d+)\s+hours?\s+ago", "hours"),
        (r"(\d+)\s+hours?\s+ago", "hours"),
        (r"(\d+)\s+minutes?\s+ago", "minutes"),
        (r"(\d+)\s+days?\s+ago", "days"),
    )

    for pattern, unit in relative_patterns:
        match = re.search(pattern, lower)
        if match:
            value = int(match.group(1))
            return reference - timedelta(**{unit: value})

    if "just now" in lower:
        return reference

    parsed = parse_datetime(text)
    if parsed and parsed.year == 1900:
        parsed = parsed.replace(year=reference.year)
    if parsed and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed


def extract_blog_link(card: Tag) -> str | None:
    for anchor in card.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith("/blog/"):
            return f"{BASE_URL}{href}"
        if href.startswith(f"{BASE_URL}/blog/"):
            return href
    return None


def extract_title_from_card(card: Tag) -> str | None:
    for tag_name in ("h1", "h2", "h3", "h4"):
        heading = card.find(tag_name)
        if heading:
            return clean_text(heading.get_text(" ", strip=True))
    return None


def extract_date_from_card(card: Tag) -> datetime | None:
    time_tag = card.find("time")
    if time_tag:
        parsed = parse_hf_date(time_tag.get("datetime") or time_tag.get_text(" ", strip=True))
        if parsed:
            return parsed

    text = clean_text(card.get_text(" ", strip=True))
    if not text:
        return None
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return parse_hf_date(match.group(0))
    return None


def extract_published_at(soup: BeautifulSoup) -> datetime | None:
    selectors = [
        ("meta", {"property": "article:published_time"}, "content"),
        ("meta", {"name": "date"}, "content"),
        ("time", {}, "datetime"),
    ]

    for tag_name, attrs, attribute in selectors:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get(attribute):
            parsed = parse_hf_date(tag.get(attribute))
            if parsed:
                return parsed

    time_tag = soup.find("time")
    if time_tag:
        parsed = parse_hf_date(time_tag.get_text(" ", strip=True))
        if parsed:
            return parsed

    full_text = clean_text(soup.get_text(" ", strip=True))
    if not full_text:
        return None
    match = re.search(r"Published\s+([A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})", full_text)
    if match:
        return parse_hf_date(match.group(1))
    return None


def extract_summary(soup: BeautifulSoup) -> str | None:
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return clean_text(meta_desc["content"])

    article_tag = soup.find("article")
    if article_tag:
        paragraph = article_tag.find("p")
        if paragraph:
            return clean_text(paragraph.get_text(" ", strip=True))
    return None


def extract_author(soup: BeautifulSoup) -> str | None:
    meta_author = soup.find("meta", attrs={"name": "author"})
    if meta_author and meta_author.get("content"):
        return clean_text(meta_author["content"])

    author_tag = soup.find(attrs={"data-testid": "author-name"})
    if author_tag:
        return clean_text(author_tag.get_text(" ", strip=True))
    return None


def extract_raw_content(soup: BeautifulSoup) -> str | None:
    article_tag = soup.find("article")
    candidates = article_tag.find_all("p") if article_tag else soup.find_all("p")

    blocks: list[str] = []
    seen: set[str] = set()
    for paragraph in candidates:
        text = clean_text(paragraph.get_text(" ", strip=True))
        if not text or len(text) < 40 or text in seen:
            continue
        seen.add(text)
        blocks.append(text)
        if len(blocks) >= 6:
            break

    if not blocks:
        return None

    return "\n\n".join(blocks)


def fetch_article_detail(
    url: str,
    timeout: int,
) -> tuple[datetime | None, str | None, str | None, str | None]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("HF 상세 페이지 실패: %s (%s)", url, exc)
        return None, None, None, None

    soup = BeautifulSoup(response.text, "html.parser")
    return (
        extract_published_at(soup),
        extract_author(soup),
        extract_summary(soup),
        extract_raw_content(soup),
    )


def fetch_hf_articles(
    window_start: datetime,
    window_end: datetime,
    limit: int = 6,
    timeout: int = 15,
) -> list[Article]:
    response = requests.get(HF_BLOG_URL, headers=HEADERS, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("article")
    collected_at = datetime.now(timezone.utc)

    seen_urls: set[str] = set()
    articles: list[Article] = []

    for index, card in enumerate(cards, start=1):
        url = extract_blog_link(card)
        title = extract_title_from_card(card)
        if not title or not url or url in seen_urls:
            continue

        seen_urls.add(url)
        card_published_at = extract_date_from_card(card)
        detail_published_at, author, summary, raw_content = fetch_article_detail(
            url, timeout
        )
        published_at = detail_published_at or card_published_at or collected_at
        card_summary = strip_html(card.get_text(" ", strip=True))

        articles.append(
            Article(
                source="huggingface",
                source_type="blog",
                title=title,
                url=url,
                published_at=published_at.astimezone(timezone.utc),
                collected_at=collected_at,
                author=author,
                summary=summary or truncate(card_summary, 280),
                raw_content=raw_content or summary or truncate(card_summary, 500),
                in_window=is_in_window(published_at, window_start, window_end),
                metadata={"rank": index},
            )
        )

        if len(articles) >= limit:
            break

    return articles
