import json
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

from app.models.article import Article


HF_BLOG_URL = "https://huggingface.co/blog"
BASE_URL = "https://huggingface.co"
OUTPUT_PATH = Path("data/raw/hf_articles.json")


def fetch_hf_articles(limit: int = 10) -> List[Article]:
    """
    Fetch latest articles from Hugging Face blog page.
    """

    response = requests.get(HF_BLOG_URL, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("article")

    articles: List[Article] = []

    for card in cards[:limit]:
        title_tag = card.find("h4")
        link_tag = card.find("a", href=True)

        if not title_tag or not link_tag:
            continue

        title = title_tag.get_text(strip=True)
        href = link_tag["href"].strip()

        if href.startswith("/"):
            url = f"{BASE_URL}{href}"
        else:
            url = href

        article = Article(
            source="huggingface",
            source_type="blog",
            title=title,
            url=url,
            published_at=None,
            author=None,
            summary=None,
            raw_content=None,
        )

        articles.append(article)

    return articles


def save_articles_to_json(articles: List[Article], output_path: Path = OUTPUT_PATH) -> None:
    """
    Save Article objects to JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [article.model_dump(mode="json") for article in articles]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    results = fetch_hf_articles(limit=10)
    save_articles_to_json(results)

    print(f"saved {len(results)} articles to {OUTPUT_PATH}")

    for article in results:
        print(article.title)
        print(article.url)
        print("-" * 40)