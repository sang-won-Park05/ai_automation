# AI/개발 아침 브리핑

매일 아침 Discord webhook으로 한국어 AI/개발 브리핑을 보내는 프로젝트다.

수집 소스는 3개만 사용한다.

- GitHub Trending
- RSS
- Hugging Face Blog

기존 블로그/노션/DB 자동화는 제거했다. 현재 코드는 `python3 -m main` 기준으로 바로 실행되는 브리핑 파이프라인만 남긴 상태다.

## 동작 방식

1. GitHub Trending, RSS, Hugging Face Blog를 수집한다.
2. 공통 `Article` 스키마로 정규화한다.
3. 제목/링크/유사 제목 기준으로 중복 제거한다.
4. Hugging Face에서 메인 이슈 1개를 선정한다.
5. GitHub Trending + RSS에서 주목할 소식 2~3개를 고른다.
6. 한국어 디스코드 메시지로 포맷한다.
7. Discord webhook으로 전송한다.

## 시간 기준

브리핑 대상 구간은 항상 한국 시간 기준으로 계산한다.

- 시작: 전날 `07:50:00`
- 종료: 당일 `07:50:00`
- 시간대: `Asia/Seoul`

예를 들어 실행 시점이 `2026-03-17 08:10 KST`이면 대상 구간은 `2026-03-16 07:50:00 ~ 2026-03-17 07:50:00`이다.

참고:

- RSS/HF는 `published_at` 기준으로 이 구간 포함 여부를 판단한다.
- GitHub Trending은 공개 시간 정보가 명확하지 않아 해당 날짜의 daily trending 스냅샷으로 취급한다.
- HF는 날짜 완전 일치보다 최신 확보 가능 항목을 우선한다. 구간 내 글이 없으면 최신 글을 메인 이슈 후보로 사용한다.

## 설치

```bash
python3 -m pip install -r requirements.txt
cp env.example .env
```

`.env`에 최소한 Discord webhook URL만 넣으면 된다.

## 실행

실제 전송:

```bash
python3 -m main
```

디스코드 전송 없이 미리보기만:

```bash
python3 -m main --dry-run
```

실행 결과:

- 콘솔에 브리핑 메시지를 출력한다.
- `data/raw/briefing_preview.txt`에 마지막 메시지를 저장한다.
- 각 소스의 최신 수집 결과를 `data/raw/*.json` 캐시에 저장한다.

## 환경변수

`env.example`

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
# 선택: 쉼표(,)로 구분한 RSS 피드 목록
RSS_FEEDS=https://www.marktechpost.com/feed/,https://venturebeat.com/category/ai/feed/,https://machinelearningmastery.com/blog/feed/,https://www.unite.ai/feed/,https://aws.amazon.com/blogs/machine-learning/feed/,https://blogs.nvidia.com/blog/category/deep-learning/feed/
```

## 디렉토리

```text
.
├── app
│   ├── config
│   │   └── settings.py
│   ├── crawler
│   │   ├── github_trending_crawler.py
│   │   ├── hf_crawler.py
│   │   └── rss_crawler.py
│   ├── models
│   │   └── article.py
│   ├── processor
│   │   ├── deduplicator.py
│   │   └── normalize.py
│   ├── publisher
│   │   └── discord_sender.py
│   ├── ranking
│   │   └── news_ranker.py
│   └── utils
│       ├── io_utils.py
│       ├── logger.py
│       ├── text_utils.py
│       └── time_utils.py
├── data
│   └── raw
├── env.example
├── main.py
└── requirements.txt
```
