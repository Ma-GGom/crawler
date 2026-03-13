import re
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from port.outbound.event_detail_fetch_port import EventDetailFetchPort
from domain.model.event_detail import MarathonEventDetail

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_ENCODING = "euc-kr"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
URL_PATTERN = re.compile(r"https?://[^\s)]+")
KOREAN_DATE_PATTERN = re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일")


class MarathonPeDetailClient(EventDetailFetchPort):
    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._headers = {
            "User-Agent": user_agent,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        if not detail_url.startswith(("http://", "https://")):
            return None

        try:
            response = requests.get(
                detail_url,
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        response.encoding = DEFAULT_ENCODING
        return self.parse_detail_html(response.text, base_url=detail_url)

    def parse_detail_html(self, html: str, *, base_url: str) -> MarathonEventDetail:
        soup = BeautifulSoup(html, "html.parser")
        registration_period: str | None = None
        official_website_url: str | None = None
        registration_start_date: date | None = None
        registration_end_date: date | None = None
        event_date: date | None = None

        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) != 2:
                continue

            label = cols[0].get_text(strip=True)
            value_td = cols[1]
            value_text = value_td.get_text(" ", strip=True)

            if label == "접수기간" and value_text:
                registration_period = value_text
                registration_start_date, registration_end_date = self._parse_registration_period(value_text)
                continue

            if label == "홈페이지":
                official_website_url = self._extract_homepage_url(value_td, value_text, base_url)
                continue

            if label == "대회일시" and value_text:
                event_date = self._extract_first_date(value_text)
                continue

        return MarathonEventDetail(
            registration_period=registration_period,
            official_website_url=official_website_url,
            registration_start_date=registration_start_date,
            registration_end_date=registration_end_date,
            event_date=event_date,
        )

    @staticmethod
    def _extract_homepage_url(value_td: Tag, value_text: str, base_url: str) -> str | None:
        anchor = value_td.find("a")
        if anchor is not None:
            href = anchor.get("href", "").strip()
            if href:
                return urljoin(base_url, href)

        matched = URL_PATTERN.search(value_text)
        if matched:
            return matched.group(0)

        return None

    @staticmethod
    def _parse_registration_period(value_text: str) -> tuple[date | None, date | None]:
        found = KOREAN_DATE_PATTERN.findall(value_text)
        if not found:
            return None, None

        parsed_dates = []
        for year_text, month_text, day_text in found:
            try:
                parsed_dates.append(date(int(year_text), int(month_text), int(day_text)))
            except ValueError:
                continue

        if not parsed_dates:
            return None, None
        if len(parsed_dates) == 1:
            return parsed_dates[0], parsed_dates[0]
        return parsed_dates[0], parsed_dates[-1]

    @staticmethod
    def _extract_first_date(value_text: str) -> date | None:
        matched = KOREAN_DATE_PATTERN.search(value_text)
        if matched is None:
            return None

        try:
            return date(int(matched.group(1)), int(matched.group(2)), int(matched.group(3)))
        except ValueError:
            return None

