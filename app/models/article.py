from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from app.utils.time_utils import ensure_timezone, parse_datetime


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dump_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class Article:
    source: Literal["github", "rss", "huggingface"]
    source_type: str
    title: str
    url: str
    published_at: datetime | None = None
    collected_at: datetime = field(default_factory=_utc_now)
    author: str | None = None
    summary: str | None = None
    raw_content: str | None = None
    in_window: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def sort_time(self) -> datetime:
        return self.published_at or self.collected_at

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["published_at"] = _dump_datetime(self.published_at)
        data["collected_at"] = _dump_datetime(self.collected_at)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Article":
        return cls(
            source=data.get("source", "rss"),
            source_type=data.get("source_type", "news"),
            title=str(data.get("title", "")).strip(),
            url=str(data.get("url", "")).strip(),
            published_at=parse_datetime(data.get("published_at")),
            collected_at=ensure_timezone(
                parse_datetime(data.get("collected_at")) or _utc_now()
            ),
            author=data.get("author"),
            summary=data.get("summary"),
            raw_content=data.get("raw_content"),
            in_window=bool(data.get("in_window", False)),
            metadata=data.get("metadata") or {},
        )
