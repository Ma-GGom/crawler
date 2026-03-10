import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from application.port.outbound.event_extract_port import EventExtractPort
from domain.model.marathon_event import MarathonEvent
from domain.rule.event_row_rule import (
    has_required_fields,
    has_valid_date_shape,
    is_header_row,
)

FALLBACK_LINK_TEXT = "링크 없음"
ROADRUN_BASE_URL = "http://www.roadrun.co.kr/schedule/"
JS_VIEW_PATH_PATTERN = re.compile(r"'(view\.php\?no=\d+)'")


class MarathonPeParser(EventExtractPort):
    def extract(self, html: str) -> list[MarathonEvent]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[MarathonEvent] = []

        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) != 4:
                continue

            date_text = cols[0].get_text(strip=True)
            title = cols[1].get_text(strip=True)
            location = cols[2].get_text(strip=True)

            if is_header_row(date_text):
                continue
            if not has_required_fields(date_text, title, location):
                continue
            if not has_valid_date_shape(date_text):
                continue

            link_tag = cols[1].find("a")
            raw_href = link_tag.get("href", FALLBACK_LINK_TEXT) if link_tag else FALLBACK_LINK_TEXT
            link_url = self._normalize_link(raw_href)

            events.append(
                MarathonEvent(
                    date_text=date_text,
                    title=title,
                    location=location,
                    link_url=link_url,
                )
            )

        return events

    def _normalize_link(self, raw_href: str) -> str:
        href = raw_href.strip()
        if not href or href == FALLBACK_LINK_TEXT:
            return FALLBACK_LINK_TEXT

        if href.startswith("javascript:"):
            matched = JS_VIEW_PATH_PATTERN.search(href)
            if matched:
                return urljoin(ROADRUN_BASE_URL, matched.group(1))
            return FALLBACK_LINK_TEXT

        return urljoin(ROADRUN_BASE_URL, href)

