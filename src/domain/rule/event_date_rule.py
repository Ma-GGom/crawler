from datetime import date, datetime, timedelta, timezone
import re

KST = timezone(timedelta(hours=9), name="KST")
MONTH_DAY_PATTERN = re.compile(r"^\s*(\d{1,2})/(\d{1,2})\([^)]+\)\s*$")
FULL_DATE_PATTERNS = (
    re.compile(r"(20\d{2})[./-]\s*(\d{1,2})[./-]\s*(\d{1,2})"),
    re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"),
)
MONTH_DAY_KR_PATTERN = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")


def infer_event_date_from_list_text(date_text: str, *, today_kst: date | None = None) -> date | None:
    full_date = _parse_full_date(date_text)
    if full_date is not None:
        return full_date

    matched = MONTH_DAY_PATTERN.match(date_text)
    if today_kst is None:
        today_kst = datetime.now(KST).date()

    if matched is not None:
        return _resolve_month_day(
            month=int(matched.group(1)),
            day=int(matched.group(2)),
            today_kst=today_kst,
        )

    kr_month_day = MONTH_DAY_KR_PATTERN.search(date_text)
    if kr_month_day is not None:
        return _resolve_month_day(
            month=int(kr_month_day.group(1)),
            day=int(kr_month_day.group(2)),
            today_kst=today_kst,
        )

    return None


def _parse_full_date(date_text: str) -> date | None:
    for pattern in FULL_DATE_PATTERNS:
        matched = pattern.search(date_text)
        if matched is None:
            continue
        year = int(matched.group(1))
        month = int(matched.group(2))
        day = int(matched.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return None


def _resolve_month_day(*, month: int, day: int, today_kst: date) -> date | None:
    year = today_kst.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        return None

    if candidate < today_kst and today_kst.month == 12 and month == 1:
        try:
            return date(year + 1, month, day)
        except ValueError:
            return None

    return candidate
