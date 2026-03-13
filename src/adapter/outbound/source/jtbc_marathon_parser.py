import re
from datetime import date

from bs4 import BeautifulSoup

from port.outbound.event_extract_port import EventExtractPort
from domain.model.marathon_event import MarathonEvent

LOCATION_FALLBACK = "\uc11c\uc6b8"
WHITESPACE_PATTERN = re.compile(r"\s+")
TITLE_PATTERN = re.compile(r"NAME\s*(20\d{2}\s*JTBC\s*\uc11c\uc6b8\ub9c8\ub77c\ud1a4)")
EVENT_DATE_PATTERN = re.compile(
    r"(20\d{2})\ub144\s*(\d{1,2})\uc6d4\s*(\d{1,2})\uc77c"
)
PLACE_PATTERN = re.compile(r"PLACE\s*([^\s]+)")


class JtbcMarathonParser(EventExtractPort):
    def extract(self, html: str) -> list[MarathonEvent]:
        text = self._extract_normalized_text(html)
        title = self._extract_title(text)
        event_date = self._extract_event_date(text)
        if title is None or event_date is None:
            return []

        location = self._extract_location(text) or LOCATION_FALLBACK
        return [
            MarathonEvent(
                date_text=event_date.isoformat(),
                title=title,
                location=location,
                link_url="https://marathon.jtbc.com/",
                official_website_url="https://marathon.jtbc.com/",
                event_date=event_date,
            )
        ]

    @staticmethod
    def _extract_normalized_text(html: str) -> str:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        return WHITESPACE_PATTERN.sub(" ", text)

    @staticmethod
    def _extract_title(text: str) -> str | None:
        matched = TITLE_PATTERN.search(text)
        if matched is None:
            return None
        title = matched.group(1).strip()
        return title or None

    @staticmethod
    def _extract_event_date(text: str) -> date | None:
        matched = EVENT_DATE_PATTERN.search(text)
        if matched is None:
            return None

        try:
            return date(
                int(matched.group(1)),
                int(matched.group(2)),
                int(matched.group(3)),
            )
        except ValueError:
            return None

    @staticmethod
    def _extract_location(text: str) -> str | None:
        matched = PLACE_PATTERN.search(text)
        if matched is None:
            return None
        location = matched.group(1).strip()
        return location or None

