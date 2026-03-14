import re
from datetime import date

import requests
from bs4 import BeautifulSoup

from port.outbound.event_detail_fetch_port import EventDetailFetchPort
from domain.model.event_detail import MarathonEventDetail

DEFAULT_TIMEOUT_SECONDS = 10
OFFICIAL_WEBSITE_URL = "https://www.chuncheonmarathon.com/"
INFO_URL = "https://www.chuncheonmarathon.com/rally/info.html"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
WHITESPACE_PATTERN = re.compile(r"\s+")
EVENT_DATE_PATTERN = re.compile(
    r"(?:출발일시|대회일(?:시)?)\s*(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"
)
REG_RANGE_PATTERN = re.compile(
    r"(?:접수|신청|참가|기간)[^0-9]{0,20}(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일[^~]{0,40}~\s*"
    r"(?:(20\d{2})\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일"
)
REG_START_PATTERN = re.compile(
    r"(?:참가신청|접수하기|신청일정)\s*(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"
)


class ChuncheonNoticeDetailClient(EventDetailFetchPort):
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
        self._fallback_info_cache: MarathonEventDetail | None = None

    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        if not detail_url.startswith(("http://", "https://")):
            return self._get_fallback_info_detail()

        try:
            response = requests.get(
                detail_url,
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException:
            return self._get_fallback_info_detail()

        response.encoding = response.apparent_encoding
        detail = self.parse_detail_html(response.text)
        if detail.event_date is None:
            fallback = self._get_fallback_info_detail()
            if fallback is None:
                return detail
            return MarathonEventDetail(
                registration_period=detail.registration_period or fallback.registration_period,
                official_website_url=OFFICIAL_WEBSITE_URL,
                registration_start_date=detail.registration_start_date or fallback.registration_start_date,
                registration_end_date=detail.registration_end_date or fallback.registration_end_date,
                event_date=detail.event_date or fallback.event_date,
            )
        return detail

    def parse_detail_html(self, html: str) -> MarathonEventDetail:
        text = self._extract_text(html)
        event_date = self._extract_event_date(text)
        registration_period, reg_start_date, reg_end_date = self._extract_registration_period(text)
        return MarathonEventDetail(
            registration_period=registration_period,
            official_website_url=OFFICIAL_WEBSITE_URL,
            registration_start_date=reg_start_date,
            registration_end_date=reg_end_date,
            event_date=event_date,
        )

    def _get_fallback_info_detail(self) -> MarathonEventDetail | None:
        if self._fallback_info_cache is not None:
            return self._fallback_info_cache

        try:
            response = requests.get(
                INFO_URL,
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        response.encoding = response.apparent_encoding
        text = self._extract_text(response.text)
        event_date = self._extract_event_date(text)
        registration_period, reg_start_date, reg_end_date = self._extract_registration_period(text)
        if reg_start_date is None:
            reg_start_date = self._extract_registration_start(text)

        self._fallback_info_cache = MarathonEventDetail(
            registration_period=registration_period,
            official_website_url=OFFICIAL_WEBSITE_URL,
            registration_start_date=reg_start_date,
            registration_end_date=reg_end_date,
            event_date=event_date,
        )
        return self._fallback_info_cache

    @staticmethod
    def _extract_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        board_body = soup.select_one(".board_body")
        if board_body is not None:
            text = board_body.get_text(" ", strip=True)
        else:
            text = soup.get_text(" ", strip=True)
        return WHITESPACE_PATTERN.sub(" ", text)

    @staticmethod
    def _extract_event_date(text: str) -> date | None:
        matched = EVENT_DATE_PATTERN.search(text)
        if matched is None:
            return None
        return _to_date(matched.group(1), matched.group(2), matched.group(3))

    @staticmethod
    def _extract_registration_period(text: str) -> tuple[str | None, date | None, date | None]:
        matched = REG_RANGE_PATTERN.search(text)
        if matched is None:
            return None, None, None

        start_date = _to_date(matched.group(1), matched.group(2), matched.group(3))
        end_year = matched.group(4) or matched.group(1)
        end_date = _to_date(end_year, matched.group(5), matched.group(6))
        return matched.group(0), start_date, end_date

    @staticmethod
    def _extract_registration_start(text: str) -> date | None:
        matched = REG_START_PATTERN.search(text)
        if matched is None:
            return None
        return _to_date(matched.group(1), matched.group(2), matched.group(3))


def _to_date(year: str, month: str, day: str) -> date | None:
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None
