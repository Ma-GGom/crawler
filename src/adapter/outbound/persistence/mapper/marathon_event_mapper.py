from datetime import date, datetime, time, timedelta, timezone

from adapter.outbound.persistence.entity.marathon_event_row import MarathonEventRow
from domain.model.marathon_event import MarathonEvent
from domain.rule.url_rule import normalize_url

KST = timezone(timedelta(hours=9), name="KST")


class MarathonEventMapper:
    @staticmethod
    def to_row(event: MarathonEvent) -> MarathonEventRow:
        reg_start_at = event.registration_start_date or event.event_date
        normalized_link = normalize_url(event.official_website_url or event.link_url)
        link_url = normalized_link or event.official_website_url or event.link_url

        return MarathonEventRow(
            title=event.title.strip() or None,
            event_date=event.event_date,
            region=MarathonEventMapper._normalize_region(event.location),
            distances=MarathonEventMapper._extract_distances(event.title),
            reg_start_date=MarathonEventMapper._to_kst_datetime(reg_start_at),
            reg_end_date=MarathonEventMapper._to_kst_datetime(event.registration_end_date),
            is_major=False,
            link_url=link_url,
            status=MarathonEventMapper._derive_status(event),
            source_name=event.source_name or None,
            source_url=event.source_url or None,
            crawled_at_kst=event.crawled_at_kst,
        )

    @staticmethod
    def _normalize_region(location: str) -> str:
        normalized = location.strip()
        if not normalized:
            return "UNKNOWN"
        return normalized.split()[0]

    @staticmethod
    def _extract_distances(title: str) -> list[str]:
        normalized = title.upper()
        distances: list[str] = []
        if "5K" in normalized:
            distances.append("5K")
        if "10K" in normalized or "10KM" in normalized:
            distances.append("10K")
        if "HALF" in normalized or "하프" in title:
            distances.append("HALF")
        if "FULL" in normalized or "풀코스" in title:
            distances.append("FULL")
        return distances

    @staticmethod
    def _to_kst_datetime(value: date | None) -> datetime | None:
        if value is None:
            return None
        return datetime.combine(value, time.min, tzinfo=KST)

    @staticmethod
    def _derive_status(event: MarathonEvent) -> str:
        today = datetime.now(KST).date()
        reg_start = event.registration_start_date
        reg_end = event.registration_end_date

        if reg_end is not None and today > reg_end:
            return "CLOSED"
        if reg_start is not None and today < reg_start:
            return "UPCOMING"
        if reg_start is not None and (reg_end is None or today <= reg_end):
            return "OPEN"
        if reg_end is not None and today <= reg_end:
            return "OPEN"
        return "UPCOMING"
