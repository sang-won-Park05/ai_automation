from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

try:
    from dateutil import parser as date_parser
except ImportError:  # pragma: no cover
    date_parser = None


KST = ZoneInfo("Asia/Seoul")


def ensure_timezone(
    value: datetime | None,
    default_tz=timezone.utc,
) -> datetime:
    if value is None:
        raise ValueError("datetime value is required")
    if value.tzinfo is None:
        return value.replace(tzinfo=default_tz)
    return value


def parse_datetime(value) -> datetime | None:
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return ensure_timezone(value)

    text = str(value).strip()
    if not text:
        return None

    iso_text = text[:-1] + "+00:00" if text.endswith("Z") else text

    try:
        return ensure_timezone(datetime.fromisoformat(iso_text))
    except ValueError:
        pass

    try:
        return ensure_timezone(parsedate_to_datetime(text))
    except (TypeError, ValueError, IndexError):
        pass

    if date_parser is not None:
        try:
            return ensure_timezone(date_parser.parse(text))
        except (TypeError, ValueError, OverflowError):
            return None

    return None


def briefing_window(reference: datetime | None = None) -> tuple[datetime, datetime]:
    now_kst = ensure_timezone(reference, KST).astimezone(KST) if reference else datetime.now(KST)
    window_end = now_kst.replace(hour=7, minute=50, second=0, microsecond=0)
    window_start = window_end - timedelta(days=1)
    return window_start, window_end


def is_in_window(
    value: datetime | None,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    if value is None:
        return False
    localized = ensure_timezone(value).astimezone(KST)
    return window_start <= localized < window_end


def format_window(window_start: datetime, window_end: datetime) -> str:
    return (
        f"{window_start.astimezone(KST):%Y-%m-%d %H:%M} ~ "
        f"{window_end.astimezone(KST):%Y-%m-%d %H:%M} KST"
    )
