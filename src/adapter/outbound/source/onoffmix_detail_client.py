import re
from datetime import date
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from port.outbound.event_detail_fetch_port import EventDetailFetchPort
from domain.model.event_detail import MarathonEventDetail

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
DATE_PATTERN = re.compile(r"(20\d{2})-(\d{1,2})-(\d{1,2})")
OUT_LINK_URL_PATTERN = re.compile(r'"outLinkUrl":"(https?://[^"\\]+)"')


class OnOffMixDetailClient(EventDetailFetchPort):
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

        return self.parse_detail_html(response.text)

    def parse_detail_html(self, html: str) -> MarathonEventDetail:
        event_date = self._extract_event_date(html)
        official_website_url = self._extract_out_link_url(html)

        if official_website_url is None:
            official_website_url = self._extract_external_url_from_submit_button(html)

        return MarathonEventDetail(
            registration_period=None,
            official_website_url=official_website_url,
            registration_start_date=None,
            registration_end_date=None,
            event_date=event_date,
        )

    @staticmethod
    def _extract_event_date(html: str) -> date | None:
        matched = re.search(r'"eventStartDate":"(20\d{2}-\d{1,2}-\d{1,2})', html)
        if matched is None:
            return None

        date_match = DATE_PATTERN.match(matched.group(1))
        if date_match is None:
            return None

        try:
            return date(
                int(date_match.group(1)),
                int(date_match.group(2)),
                int(date_match.group(3)),
            )
        except ValueError:
            return None

    @staticmethod
    def _extract_out_link_url(html: str) -> str | None:
        matched = OUT_LINK_URL_PATTERN.search(html)
        if matched is None:
            return None

        candidate = matched.group(1).replace("\\/", "/").strip()
        if OnOffMixDetailClient._is_valid_external_url(candidate):
            return candidate
        return None

    @staticmethod
    def _extract_external_url_from_submit_button(html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        submit_link = soup.select_one("a.btn_submit[href]")
        if submit_link is None:
            return None

        href = submit_link.get("href", "").strip()
        if OnOffMixDetailClient._is_valid_external_url(href):
            return href
        return None

    @staticmethod
    def _is_valid_external_url(url: str) -> bool:
        if not url.startswith(("http://", "https://")):
            return False

        hostname = urlparse(url).hostname or ""
        if hostname.endswith("onoffmix.com"):
            return False
        return True
