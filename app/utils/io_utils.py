from __future__ import annotations

import json
from pathlib import Path

from app.models.article import Article


def save_articles(path: str | Path, articles: list[Article]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [article.to_dict() for article in articles]
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_articles(path: str | Path) -> list[Article]:
    file_path = Path(path)
    if not file_path.exists():
        return []

    try:
        raw_data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(raw_data, list):
        return []

    articles: list[Article] = []
    for item in raw_data:
        if not isinstance(item, dict):
            continue
        try:
            articles.append(Article.from_dict(item))
        except Exception:
            continue
    return articles


def save_text(path: str | Path, content: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
