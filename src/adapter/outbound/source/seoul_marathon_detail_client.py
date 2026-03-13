import re
from datetime import date

import requests
from bs4 import BeautifulSoup

from port.outbound.event_detail_fetch_port import EventDetailFetchPort
from domain.model.event_detail import MarathonEventDetail

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_DETAIL_URL = "https://seoul-marathon.com/90"
DEFAULT_OFFICIAL_WEBSITE_URL = "https://seoul-marathon.com/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
WHITESPACE_PATTERN = re.compile(r"\s+")
YEAR_PATTERN = re.compile(r"(20\d{2})\s*\uc11c\uc6b8\s*\ub9c8\ub77c\ud1a4")
RANGE_PATTERN = re.compile(
    r"(\d{1,2})\uc6d4\s*(\d{1,2})\uc77c[^~]{0,24}~\s*(?:(\d{1,2})\uc6d4\s*)?"
    r"(\d{1,2})\uc77c"
)


class SeoulMarathonDetailClient(EventDetailFetchPort):
    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._headers = {
            "User-Agent": user_agent,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        target_url = (
            detail_url
            if detail_url.startswith(("http://", "https://"))
            else DEFAULT_DETAIL_URL
        )
        try:
            response = requests.get(
                target_url,
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        response.encoding = response.apparent_encoding
        return self.parse_detail_html(response.text)

    def parse_detail_html(self, html: str) -> MarathonEventDetail:
        text = self._extract_normalized_text(html)
        registration_period, registration_start_date, registration_end_date = (
            self._extract_registration_period(text)
        )

        return MarathonEventDetail(
            registration_period=registration_period,
            official_website_url=DEFAULT_OFFICIAL_WEBSITE_URL,
            registration_start_date=registration_start_date,
            registration_end_date=registration_end_date,
            event_date=None,
        )

    @staticmethod
    def _extract_normalized_text(html: str) -> str:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        return WHITESPACE_PATTERN.sub(" ", text)

    @staticmethod
    def _extract_registration_period(
        text: str,
    ) -> tuple[str | None, date | None, date | None]:
        year = SeoulMarathonDetailClient._extract_year(text)
        if year is None:
            return None, None, None

        matched = RANGE_PATTERN.search(text)
        if matched is None:
            return None, None, None

        start_month = int(matched.group(1))
        start_day = int(matched.group(2))
        end_month = int(matched.group(3)) if matched.group(3) is not None else start_month
        end_day = int(matched.group(4))

        try:
            start_date = date(year, start_month, start_day)
            end_date = date(year, end_month, end_day)
        except ValueError:
            return None, None, None

        return matched.group(0), start_date, end_date

    @staticmethod
    def _extract_year(text: str) -> int | None:
        matched = YEAR_PATTERN.search(text)
        if matched is None:
            return None
        return int(matched.group(1))

