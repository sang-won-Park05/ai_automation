from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_RSS_FEEDS = [
    "https://www.marktechpost.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://machinelearningmastery.com/blog/feed/",
    "https://www.unite.ai/feed/",
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
]


def load_env_file(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def split_env_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[\n,]", value) if item.strip()]


@dataclass(slots=True)
class Settings:
    discord_webhook_url: str | None
    rss_feeds: list[str] = field(default_factory=lambda: list(DEFAULT_RSS_FEEDS))
    request_timeout: int = 15
    github_limit: int = 10
    rss_limit_per_feed: int = 4
    hf_limit: int = 6
    output_dir: Path = Path("data/raw")


def load_settings() -> Settings:
    load_env_file()

    rss_feeds = split_env_list(os.getenv("RSS_FEEDS")) or list(DEFAULT_RSS_FEEDS)
    output_dir = Path(os.getenv("OUTPUT_DIR", "data/raw"))
    output_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        rss_feeds=rss_feeds,
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "15")),
        github_limit=int(os.getenv("GITHUB_LIMIT", "10")),
        rss_limit_per_feed=int(os.getenv("RSS_LIMIT_PER_FEED", "4")),
        hf_limit=int(os.getenv("HF_LIMIT", "6")),
        output_dir=output_dir,
    )
