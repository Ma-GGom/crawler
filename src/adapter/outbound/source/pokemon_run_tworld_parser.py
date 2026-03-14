from datetime import date
import re

from bs4 import BeautifulSoup

from domain.model.marathon_event import MarathonEvent
from port.outbound.event_extract_port import EventExtractPort

TITLE_PATTERN = re.compile(r"(포켓몬\s*런\s*20\d{2})")
KOREAN_DATE_PATTERN = re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일")
EVENT_DATE_PATTERN = re.compile(
    r"(?:일시/장소|일정\s*및\s*장소\s*날짜)\s*(20\d{2}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일)"
)
REGISTRATION_RANGE_PATTERN = re.compile(
    r"예매\s*기간\s*(20\d{2}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일)[^~]{0,24}~\s*"
    r"(?:(20\d{2}\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일)"
)
LOCATION_PATTERN = re.compile(
    r"(?:일시/장소|일정\s*및\s*장소)\s*20\d{2}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일"
    r"[^/]{0,24}/\s*([가-힣A-Za-z0-9\s]+)"
)
LOCATION_FALLBACK = "서울"
LOCATION_TERMINATORS = ("포켓몬", "티켓", "갤럭시", "예매", "일정", "프로그램")


class PokemonRunTworldParser(EventExtractPort):
    def extract(self, html: str) -> list[MarathonEvent]:
        text = self._extract_normalized_text(html)
        title = self._extract_title(text)
        event_date = self._extract_event_date(text)
        if title is None or event_date is None:
            return []

        registration_start, registration_end = self._extract_registration_range(
            text,
            event_date.year,
        )
        location = self._extract_location(text)

        return [
            MarathonEvent(
                date_text=event_date.isoformat(),
                title=title,
                location=location,
                link_url="https://shop.tworld.co.kr/exhibition/view?exhibitionId=P00000498",
                official_website_url="https://pokemonkorea.co.kr/PokemonRUN2026/menu715",
                registration_period=self._build_registration_period(
                    registration_start,
                    registration_end,
                ),
                registration_start_date=registration_start,
                registration_end_date=registration_end,
                event_date=event_date,
            )
        ]

    @staticmethod
    def _extract_normalized_text(html: str) -> str:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text)

    @staticmethod
    def _extract_title(text: str) -> str | None:
        matched = TITLE_PATTERN.search(text)
        if matched is None:
            return None
        return matched.group(1).replace("  ", " ").strip()

    @staticmethod
    def _extract_event_date(text: str) -> date | None:
        matched = EVENT_DATE_PATTERN.search(text)
        if matched is None:
            return None
        return PokemonRunTworldParser._parse_korean_date(matched.group(1))

    @staticmethod
    def _extract_registration_range(
        text: str,
        default_year: int,
    ) -> tuple[date | None, date | None]:
        matched = REGISTRATION_RANGE_PATTERN.search(text)
        if matched is None:
            return None, None

        start_date = PokemonRunTworldParser._parse_korean_date(matched.group(1))
        if start_date is None:
            return None, None

        end_year = default_year
        if matched.group(2) is not None:
            year_matched = re.search(r"20\d{2}", matched.group(2))
            if year_matched is not None:
                end_year = int(year_matched.group(0))

        try:
            end_date = date(end_year, int(matched.group(3)), int(matched.group(4)))
        except ValueError:
            return start_date, None

        return start_date, end_date

    @staticmethod
    def _extract_location(text: str) -> str:
        matched = LOCATION_PATTERN.search(text)
        if matched is None:
            return LOCATION_FALLBACK
        location = matched.group(1)
        for token in LOCATION_TERMINATORS:
            index = location.find(token)
            if index >= 0:
                location = location[:index]
        location = location.strip()
        return location or LOCATION_FALLBACK

    @staticmethod
    def _parse_korean_date(value: str) -> date | None:
        matched = KOREAN_DATE_PATTERN.search(value)
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
    def _build_registration_period(
        start_date: date | None,
        end_date: date | None,
    ) -> str | None:
        if start_date is not None and end_date is not None:
            return f"{start_date.isoformat()}~{end_date.isoformat()}"
        return None
