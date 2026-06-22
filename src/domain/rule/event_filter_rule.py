from datetime import date, datetime, timedelta, timezone

from domain.model.marathon_event import MarathonEvent

KST = timezone(timedelta(hours=9), name="KST")


def is_actionable_event(event: MarathonEvent, *, today_kst: date | None = None) -> bool:
    if event.event_date is None:
        return True

    if today_kst is None:
        today_kst = datetime.now(KST).date()

    oldest_allowed_date = date(today_kst.year - 1, 1, 1)
    if event.event_date < oldest_allowed_date:
        return False

    return True
