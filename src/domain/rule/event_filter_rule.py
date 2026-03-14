from datetime import date, datetime, timedelta, timezone

from domain.model.marathon_event import MarathonEvent

KST = timezone(timedelta(hours=9), name="KST")


def is_actionable_event(event: MarathonEvent, *, today_kst: date | None = None) -> bool:
    if today_kst is None:
        today_kst = datetime.now(KST).date()

    if event.event_date is not None and event.event_date < today_kst:
        return False

    return True


