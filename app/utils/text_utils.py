from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.models.article import Article


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "rss",
}

TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "how",
    "in",
    "of",
    "on",
    "the",
    "to",
    "using",
    "via",
    "with",
}

TOPIC_KEYWORDS = [
    ("AI 에이전트", ("agent", "agents", "assistant", "workflow", "orchestration")),
    ("브라우저 자동화", ("browser", "playwright", "puppeteer", "headless", "scraping")),
    ("모델 출시", ("model", "llm", "release", "checkpoint", "foundation model")),
    ("추론 최적화", ("inference", "serving", "quantization", "latency", "throughput")),
    ("학습/파인튜닝", ("training", "fine-tuning", "distillation", "lora", "pretrain")),
    ("RAG/검색", ("rag", "retrieval", "vector", "embedding", "search")),
    ("멀티모달", ("multimodal", "vision", "image", "video", "audio", "speech")),
    ("개발 도구", ("framework", "sdk", "tool", "library", "api", "cli", "developer")),
    ("평가/벤치마크", ("benchmark", "eval", "evaluation", "leaderboard", "test")),
    ("데이터셋", ("dataset", "corpus", "data set")),
    ("보안/거버넌스", ("governance", "security", "audit", "compliance", "guardrail", "policy")),
    ("배포/인프라", ("deploy", "deployment", "docker", "gpu", "cloud", "infra", "kubernetes")),
    ("로보틱스", ("robot", "robotics", "simulation")),
]


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def strip_html(value: str | None) -> str | None:
    if not value:
        return None
    soup = BeautifulSoup(value, "html.parser")
    return clean_text(soup.get_text(" ", strip=True))


def truncate(value: str | None, limit: int) -> str | None:
    text = clean_text(value)
    if not text or len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def canonicalize_url(url: str | None) -> str:
    if not url:
        return ""
    split_result = urlsplit(url.strip())
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(split_result.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    path = split_result.path.rstrip("/") or "/"
    return urlunsplit(
        (
            split_result.scheme.lower(),
            split_result.netloc.lower(),
            path,
            urlencode(filtered_query),
            "",
        )
    )


def normalize_title(title: str | None) -> str:
    text = clean_text(title)
    if not text:
        return ""
    lowered = re.sub(r"[^0-9a-zA-Z가-힣/\s]", " ", text.lower())
    tokens = [
        token
        for token in lowered.split()
        if token not in TITLE_STOPWORDS and len(token) > 1
    ]
    return " ".join(tokens)


def title_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    ratio = SequenceMatcher(None, left, right).ratio()
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    union = left_tokens | right_tokens
    overlap = (len(left_tokens & right_tokens) / len(union)) if union else 0.0
    containment = 0.92 if left in right or right in left else 0.0
    return max(ratio, overlap, containment)


def extract_topics(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    topics: list[str] = []
    for label, keywords in TOPIC_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            topics.append(label)
    return topics


def article_topic_text(article: Article) -> str:
    return " ".join(filter(None, [article.title, article.summary]))


def primary_topic(article: Article) -> str:
    topics = extract_topics(article_topic_text(article))
    if topics:
        return topics[0]
    return "일반 AI/개발"


def source_display_name(article: Article) -> str:
    if article.source == "github":
        return "GitHub Trending"
    if article.source == "huggingface":
        return "Hugging Face"
    return "RSS"


def summarize_article_korean(article: Article, max_length: int = 120) -> str:
    topics = extract_topics(article_topic_text(article))
    topic_text = ", ".join(topics[:3]) if topics else "최신 AI/개발 흐름"

    if article.source == "github":
        extras: list[str] = []
        language = article.metadata.get("language")
        stars_today = article.metadata.get("stars_today")
        if language:
            extras.append(f"{language} 기반")
        if stars_today:
            extras.append(f"오늘 {stars_today}개 스타")

        opener = "GitHub Trending 저장소입니다."
        if extras:
            opener = f"GitHub Trending에서 포착된 {' '.join(extras)} 저장소입니다."
        return truncate(f"{opener} 주요 포인트: {topic_text}.", max_length) or ""

    if article.source == "huggingface":
        opener = "기준 시간대에 포착된 Hugging Face 글입니다." if article.in_window else "최신 Hugging Face 글을 보완용 메인 이슈로 사용했습니다."
        return truncate(f"{opener} 주요 포인트: {topic_text}.", max_length) or ""

    opener = "기준 시간대에 수집된 AI/개발 기사입니다." if article.in_window else "최근 확인된 AI/개발 기사입니다."
    return truncate(f"{opener} 주요 포인트: {topic_text}.", max_length) or ""
