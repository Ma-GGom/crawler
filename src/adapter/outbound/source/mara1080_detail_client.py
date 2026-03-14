from datetime import date, datetime
import re

import requests

from domain.model.event_detail import MarathonEventDetail
from port.outbound.event_detail_fetch_port import EventDetailFetchPort

MARA1080_EVENT_PATTERN = re.compile(
    r"https?://mara1080\.com/event/([0-9a-fA-F\-]{36})"
)
API_URL_TEMPLATE = "https://user-api.mara1080.com/api/v1/public/event/{event_id}"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class Mara1080DetailClient(EventDetailFetchPort):
    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._headers = {
            "User-Agent": user_agent,
            "Accept": "application/json,text/plain,*/*",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        event_id = self._extract_event_id(detail_url)
        if event_id is None:
            return None

        api_url = API_URL_TEMPLATE.format(event_id=event_id)
        try:
            response = requests.get(
                api_url,
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return None

        return self.parse_detail_payload(payload, fallback_url=detail_url)

    def parse_detail_payload(
        self, payload: dict[str, object], *, fallback_url: str
    ) -> MarathonEventDetail | None:
        event_info = payload.get("eventInfo")
        if not isinstance(event_info, dict):
            return None

        event_date = self._parse_iso_date(event_info.get("startDate"))
        reg_end = self._parse_iso_date(event_info.get("registDeadline"))
        reg_start = self._parse_iso_date(event_info.get("registStartDate"))
        official_url = self._extract_text(event_info.get("eventsPageUrl")) or fallback_url
        registration_period = self._build_registration_period(reg_start, reg_end)

        return MarathonEventDetail(
            registration_period=registration_period,
            official_website_url=official_url,
            registration_start_date=reg_start,
            registration_end_date=reg_end,
            event_date=event_date,
        )

    @staticmethod
    def _extract_event_id(detail_url: str) -> str | None:
        matched = MARA1080_EVENT_PATTERN.search(detail_url)
        if matched is None:
            return None
        return matched.group(1).lower()

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

    @staticmethod
    def _extract_text(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _build_registration_period(
        reg_start: date | None, reg_end: date | None
    ) -> str | None:
        if reg_start is not None and reg_end is not None:
            return f"{reg_start.isoformat()}~{reg_end.isoformat()}"
        if reg_end is not None:
            return f"~{reg_end.isoformat()}"
        return None
