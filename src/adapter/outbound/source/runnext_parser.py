import json
from datetime import date, datetime

from port.outbound.event_extract_port import EventExtractPort
from domain.model.marathon_event import MarathonEvent

CATEGORY_KEYS = (
    "approvedList",
    "openingSoonList",
    "openForRegistrationList",
)
SOURCE_FALLBACK_URL = "https://www.runnext.org/"
LOCATION_FALLBACK = "\uc7a5\uc18c \ubbf8\uc815"


class RunNextParser(EventExtractPort):
    def extract(self, html: str) -> list[MarathonEvent]:
        try:
            payload = json.loads(html)
        except json.JSONDecodeError:
            return []

        data = payload.get("data")
        if not isinstance(data, dict):
            return []

        events: list[MarathonEvent] = []
        seen_ids: set[str] = set()
        for category in CATEGORY_KEYS:
            for item in data.get(category, []):
                if not isinstance(item, dict):
                    continue

                marathon_id = self._extract_item_id(item)
                if marathon_id is not None and marathon_id in seen_ids:
                    continue
                event = self._to_event(item)
                if event is None:
                    continue

                if marathon_id is not None:
                    seen_ids.add(marathon_id)
                events.append(event)

        return events

    @staticmethod
    def _extract_item_id(item: dict[str, object]) -> str | None:
        marathon_id = item.get("id")
        if not isinstance(marathon_id, str):
            return None
        marathon_id = marathon_id.strip()
        return marathon_id or None

    @staticmethod
    def _to_event(item: dict[str, object]) -> MarathonEvent | None:
        title = RunNextParser._extract_text(item.get("name"))
        if title is None:
            return None

        event_date = RunNextParser._parse_iso_date(item.get("date"))
        if event_date is None:
            return None

        location = (
            RunNextParser._extract_text(item.get("location"))
            or RunNextParser._extract_text(item.get("region"))
            or LOCATION_FALLBACK
        )
        link_url = RunNextParser._extract_text(item.get("website")) or SOURCE_FALLBACK_URL
        reg_start = RunNextParser._parse_iso_date(item.get("registrationStart"))
        reg_end = RunNextParser._parse_iso_date(item.get("registrationEnd"))

        registration_period = None
        if reg_start is not None and reg_end is not None:
            registration_period = f"{reg_start.isoformat()}~{reg_end.isoformat()}"

        return MarathonEvent(
            date_text=event_date.isoformat(),
            title=title,
            location=location,
            link_url=link_url,
            registration_period=registration_period,
            official_website_url=link_url,
            registration_start_date=reg_start,
            registration_end_date=reg_end,
            event_date=event_date,
        )

    @staticmethod
    def _extract_text(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _parse_iso_date(value: object) -> date | None:
        if not isinstance(value, str):
            return None

        raw = value.strip()
        if not raw:
            return None

        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            return None
