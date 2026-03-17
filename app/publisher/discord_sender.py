from __future__ import annotations

import logging

import requests

from app.models.article import Article
from app.utils.text_utils import source_display_name, summarize_article_korean, truncate
from app.utils.time_utils import format_window


LOGGER = logging.getLogger(__name__)


def format_briefing_message(
    window_start,
    window_end,
    main_issue: Article | None,
    highlights: list[Article],
) -> str:
    lines = [
        "📌 오늘의 AI/개발 브리핑",
        f"기준: {format_window(window_start, window_end)}",
        "",
        "🔥 메인 이슈 (Hugging Face)",
    ]

    if main_issue:
        lines.append(f"- {truncate(main_issue.title, 120)}")
        lines.append(f"  {summarize_article_korean(main_issue, max_length=150)}")
        if not main_issue.in_window:
            lines.append("  기준 시간대에 맞는 HF 글이 없어 최신 확보 글을 대신 사용했습니다.")
        lines.append(f"  링크: {main_issue.url}")
    else:
        lines.append("- 오늘은 Hugging Face 메인 이슈를 확보하지 못했습니다.")

    lines.extend(["", "📰 주목할 소식"])
    if highlights:
        for index, article in enumerate(highlights, start=1):
            lines.append(
                f"{index}. [{source_display_name(article)}] {truncate(article.title, 110)}"
            )
            lines.append(f"   {summarize_article_korean(article, max_length=120)}")
            lines.append(f"   링크: {article.url}")
    else:
        lines.append("- 선별 가능한 추가 소식을 확보하지 못했습니다.")

    return "\n".join(lines).strip()


def split_discord_message(message: str, limit: int = 1800) -> list[str]:
    if len(message) <= limit:
        return [message]

    chunks: list[str] = []
    current_lines: list[str] = []

    for line in message.splitlines():
        candidate = "\n".join(current_lines + [line]).strip()
        if current_lines and len(candidate) > limit:
            chunks.append("\n".join(current_lines).strip())
            current_lines = [line]
            continue
        current_lines.append(line)

    if current_lines:
        chunks.append("\n".join(current_lines).strip())

    return chunks


def send_discord_message(
    webhook_url: str,
    message: str,
    timeout: int = 15,
) -> bool:
    chunks = split_discord_message(message)

    try:
        for chunk in chunks:
            response = requests.post(
                webhook_url,
                json={"content": chunk},
                timeout=timeout,
            )
            if response.status_code >= 400:
                LOGGER.error(
                    "Discord 전송 실패: status=%s body=%s",
                    response.status_code,
                    response.text[:500],
                )
                return False
    except requests.RequestException as exc:
        LOGGER.error("Discord webhook 요청 실패: %s", exc)
        return False

    LOGGER.info("Discord 전송 완료: %d chunk", len(chunks))
    return True
