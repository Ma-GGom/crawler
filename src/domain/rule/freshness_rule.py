from datetime import datetime, timedelta, timezone

MAX_FETCH_AGE_SECONDS = 120
KST = timezone(timedelta(hours=9), name="KST")


def is_fresh_payload(
    fetched_at_kst: datetime,
    *,
    now_kst: datetime | None = None,
    max_age_seconds: int = MAX_FETCH_AGE_SECONDS,
) -> bool:
    if now_kst is None:
        now_kst = datetime.now(KST)

    if fetched_at_kst.tzinfo is None:
        return False

    age_seconds = (now_kst - fetched_at_kst).total_seconds()
    return 0 <= age_seconds <= max_age_seconds
