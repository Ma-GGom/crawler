from datetime import date, datetime, timedelta, timezone
import re

KST = timezone(timedelta(hours=9), name="KST")
MONTH_DAY_PATTERN = re.compile(r"^\s*(\d{1,2})/(\d{1,2})\([^)]+\)\s*$")


def infer_event_date_from_list_text(date_text: str, *, today_kst: date | None = None) -> date | None:
    matched = MONTH_DAY_PATTERN.match(date_text)
    if matched is None:
        return None

    if today_kst is None:
        today_kst = datetime.now(KST).date()

    month = int(matched.group(1))
    day = int(matched.group(2))
    year = today_kst.year

    try:
        candidate = date(year, month, day)
    except ValueError:
        return None

    # Year boundary fallback for list rows around New Year.
    if candidate < today_kst and today_kst.month == 12 and month == 1:
        try:
            return date(year + 1, month, day)
        except ValueError:
            return None

    return candidate

