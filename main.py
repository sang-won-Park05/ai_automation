from __future__ import annotations

import argparse
from typing import Callable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discord AI/development briefing pipeline"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="디스코드 전송 없이 콘솔 출력과 캐시 파일만 생성합니다.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from app.config.settings import load_settings
        from app.crawler.github_trending_crawler import fetch_github_trending
        from app.crawler.hf_crawler import fetch_hf_articles
        from app.crawler.rss_crawler import fetch_rss_articles
        from app.processor.deduplicator import deduplicate_articles
        from app.processor.normalize import normalize_articles
        from app.publisher.discord_sender import (
            format_briefing_message,
            send_discord_message,
        )
        from app.ranking.news_ranker import select_briefing_items, select_main_issue
        from app.utils.io_utils import load_articles, save_articles, save_text
        from app.utils.logger import configure_logging
        from app.utils.time_utils import briefing_window, format_window
    except ModuleNotFoundError as exc:
        print(
            "필수 패키지가 없습니다. "
            "먼저 `python3 -m pip install -r requirements.txt`를 실행하세요.\n"
            f"누락 모듈: {exc.name}"
        )
        return 1

    settings = load_settings()
    logger = configure_logging()

    window_start, window_end = briefing_window()
    logger.info("브리핑 대상 구간(KST): %s", format_window(window_start, window_end))

    def collect_source(
        name: str,
        cache_name: str,
        fetcher: Callable[[], list],
    ) -> list:
        cache_path = settings.output_dir / cache_name

        try:
            articles = normalize_articles(fetcher())
        except Exception:
            logger.exception("%s 수집 중 예외가 발생했습니다.", name)
            articles = []

        if articles:
            save_articles(cache_path, articles)
            logger.info("%s 수집 완료: %d건", name, len(articles))
            return articles

        cached_articles = normalize_articles(load_articles(cache_path))
        if cached_articles:
            logger.warning(
                "%s 실시간 결과가 비어 있어 캐시를 사용합니다: %d건",
                name,
                len(cached_articles),
            )
            return cached_articles

        logger.warning("%s에서 확보된 항목이 없습니다.", name)
        return []

    github_articles = collect_source(
        "GitHub Trending",
        "github_trending.json",
        lambda: fetch_github_trending(
            window_start=window_start,
            window_end=window_end,
            limit=settings.github_limit,
            timeout=settings.request_timeout,
        ),
    )
    rss_articles = collect_source(
        "RSS",
        "rss_articles.json",
        lambda: fetch_rss_articles(
            window_start=window_start,
            window_end=window_end,
            feed_urls=settings.rss_feeds,
            limit_per_feed=settings.rss_limit_per_feed,
            timeout=settings.request_timeout,
        ),
    )
    hf_articles = collect_source(
        "Hugging Face",
        "hf_articles.json",
        lambda: fetch_hf_articles(
            window_start=window_start,
            window_end=window_end,
            limit=settings.hf_limit,
            timeout=settings.request_timeout,
        ),
    )

    main_issue = select_main_issue(deduplicate_articles(hf_articles))
    highlights = select_briefing_items(
        deduplicate_articles(github_articles + rss_articles),
        limit=3,
    )

    message = format_briefing_message(
        window_start=window_start,
        window_end=window_end,
        main_issue=main_issue,
        highlights=highlights,
    )

    preview_path = settings.output_dir / "briefing_preview.txt"
    save_text(preview_path, message)
    logger.info("브리핑 미리보기 저장: %s", preview_path)

    print()
    print(message)
    print()

    if args.dry_run:
        logger.info("--dry-run 활성화: 디스코드 전송을 건너뜁니다.")
        return 0

    if not settings.discord_webhook_url:
        logger.warning(
            "DISCORD_WEBHOOK_URL이 없어 콘솔/파일 미리보기만 수행했습니다."
        )
        return 0

    success = send_discord_message(
        webhook_url=settings.discord_webhook_url,
        message=message,
        timeout=settings.request_timeout,
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
