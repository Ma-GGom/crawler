from __future__ import annotations

from datetime import date
import re
from typing import Callable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from domain.model.marathon_event import MarathonEvent
from port.outbound.event_extract_port import EventExtractPort

IMAGE_URL_PATTERN = re.compile(
    r"https?://[^\s\"'<>]+?\.(?:png|jpe?g|webp|gif|bmp)(?:\?[^\s\"'<>]*)?",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"(20\d{2})\s*(?:[./-]|년)\s*(\d{1,2})\s*(?:[./-]|월)\s*(\d{1,2})",
    re.IGNORECASE,
)
LOCATION_KEYWORDS = ("장소", "집결", "집결지", "출발", "도착", "venue", "location")
REGISTRATION_KEYWORDS = ("접수", "신청", "등록", "entry", "registration")
EVENT_DATE_KEYWORDS = ("대회일", "개최일", "race day", "event date", "date")
TITLE_KEYWORDS = ("마라톤", "울트라", "트레일", "레이스", "런")
DEFAULT_LOCATION = "unknown"
INVALID_LOCATION_TOKENS = (
    "date",
    "venue",
    "vision",
    "race info",
    "대회 개요",
    "race introduction",
    "코스",
    "cp",
    "<>",
)
LOCATION_ADMIN_HINTS = (
    "특별시",
    "광역시",
    "특별자치시",
    "특별자치도",
    "도 ",
    "시 ",
    "군 ",
    "구 ",
)


class DtrailParser(EventExtractPort):
    def __init__(
        self,
        *,
        source_url: str,
        link_url: str | None = None,
        official_website_url: str | None = None,
        image_text_reader: Callable[[str], str | None] | None = None,
        max_images: int = 20,
    ) -> None:
        self._source_url = source_url
        self._link_url = link_url or source_url
        self._official_website_url = official_website_url or self._link_url
        self._image_text_reader = image_text_reader
        self._max_images = max_images

    def extract(self, html: str) -> list[MarathonEvent]:
        soup = BeautifulSoup(html, "html.parser")
        fallback_title = self._extract_fallback_title(soup)

        ocr_text = self._extract_ocr_text(soup=soup, html=html)
        combined_text = self._join_texts(
            [
                ocr_text,
                self._extract_html_text(soup),
            ]
        )

        title = self._extract_title(combined_text) or fallback_title
        if not title:
            return []

        event_date = self._extract_event_date(combined_text)
        reg_start, reg_end = self._extract_registration_range(combined_text, event_date)
        location = self._extract_location(combined_text) or DEFAULT_LOCATION
        date_text = event_date.isoformat() if event_date is not None else self._extract_date_text(combined_text)

        event = MarathonEvent(
            date_text=date_text or title,
            title=title,
            location=location,
            link_url=self._link_url,
            official_website_url=self._official_website_url,
            registration_period=self._build_registration_period(reg_start, reg_end),
            registration_start_date=reg_start,
            registration_end_date=reg_end,
            event_date=event_date,
        )
        return [event]

    def _extract_ocr_text(self, *, soup: BeautifulSoup, html: str) -> str:
        if self._image_text_reader is None:
            return ""
        texts: list[str] = []
        for image_url in self._extract_image_urls(soup=soup, html=html)[: self._max_images]:
            text = self._image_text_reader(image_url)
            if text:
                texts.append(text)
        return "\n".join(texts)

    def _extract_image_urls(self, *, soup: BeautifulSoup, html: str) -> list[str]:
        candidates: list[str] = []

        for image in soup.find_all("img"):
            for attribute in ("src", "data-src", "data-original", "data-lazy-src"):
                raw = image.get(attribute)
                if isinstance(raw, str) and raw.strip():
                    candidates.append(urljoin(self._source_url, raw.strip()))

        for raw_url in IMAGE_URL_PATTERN.findall(html):
            candidates.append(urljoin(self._source_url, raw_url.strip()))

        deduped: list[str] = []
        seen: set[str] = set()
        for url in candidates:
            normalized = url.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    @staticmethod
    def _extract_html_text(soup: BeautifulSoup) -> str:
        text = soup.get_text("\n", strip=True)
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())

    @staticmethod
    def _extract_fallback_title(soup: BeautifulSoup) -> str:
        og_title = soup.select_one("meta[property='og:title']")
        if og_title is not None:
            content = og_title.get("content")
            if isinstance(content, str) and content.strip():
                return DtrailParser._normalize_title(content)

        title_tag = soup.title.string if soup.title is not None else ""
        if isinstance(title_tag, str) and title_tag.strip():
            return DtrailParser._normalize_title(title_tag)
        return ""

    @staticmethod
    def _extract_title(text: str) -> str:
        lines = DtrailParser._to_lines(text)
        for line in lines:
            compact = line.replace(" ", "")
            if not any(keyword in compact for keyword in TITLE_KEYWORDS):
                continue
            if 3 <= len(line) <= 80:
                return DtrailParser._normalize_title(line)
        return ""

    @staticmethod
    def _normalize_title(raw_title: str) -> str:
        title = " ".join(raw_title.split())
        title = title.replace("Dtrail", "").replace("dtrail", "").strip(" -|")
        return title.strip()

    @staticmethod
    def _extract_event_date(text: str) -> date | None:
        lines = DtrailParser._to_lines(text)
        for line in lines:
            lowered = line.lower()
            if any(keyword in lowered for keyword in EVENT_DATE_KEYWORDS):
                parsed = DtrailParser._extract_first_date(line)
                if parsed is not None:
                    return parsed

        # 키워드 라인에서 못 찾으면 페이지 전체 날짜 중 가장 늦은 날짜를 대회일로 본다.
        all_dates = DtrailParser._extract_all_dates(text)
        if not all_dates:
            return None
        return max(all_dates)

    @staticmethod
    def _extract_registration_range(
        text: str,
        event_date: date | None,
    ) -> tuple[date | None, date | None]:
        lines = DtrailParser._to_lines(text)

        for line in lines:
            lowered = line.lower()
            if not any(keyword in lowered for keyword in REGISTRATION_KEYWORDS):
                continue
            dates = DtrailParser._extract_all_dates(line)
            if len(dates) >= 2:
                return dates[0], dates[1]
            if len(dates) == 1:
                return dates[0], None

        all_dates = DtrailParser._extract_all_dates(text)
        if not all_dates:
            return None, None

        if event_date is not None:
            before_event = [parsed for parsed in all_dates if parsed <= event_date]
            if len(before_event) >= 2:
                ordered = sorted(before_event)
                return ordered[0], ordered[1]
            if len(before_event) == 1:
                return before_event[0], None

        ordered = sorted(all_dates)
        if len(ordered) >= 2:
            return ordered[0], ordered[1]
        return ordered[0], None

    @staticmethod
    def _extract_location(text: str) -> str:
        lines = DtrailParser._to_lines(text)
        for line in lines:
            lowered = line.lower()
            if not any(keyword in lowered for keyword in LOCATION_KEYWORDS):
                continue

            cleaned = line
            cleaned = re.sub(
                r"^(장소|집결지|집결|출발|도착|venue|location)\s*[:：]?\s*",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            if "/" in cleaned:
                parts = [part.strip() for part in cleaned.split("/") if part.strip()]
                if parts:
                    cleaned = parts[-1]
            cleaned = " ".join(cleaned.split())
            if cleaned and DtrailParser._is_plausible_location(cleaned):
                return cleaned
        return ""

    @staticmethod
    def _extract_date_text(text: str) -> str:
        first = DtrailParser._extract_first_date(text)
        if first is None:
            return ""
        return first.isoformat()

    @staticmethod
    def _extract_first_date(text: str) -> date | None:
        dates = DtrailParser._extract_all_dates(text)
        if not dates:
            return None
        return dates[0]

    @staticmethod
    def _extract_all_dates(text: str) -> list[date]:
        dates: list[date] = []
        for matched in DATE_PATTERN.finditer(text):
            try:
                parsed = date(
                    int(matched.group(1)),
                    int(matched.group(2)),
                    int(matched.group(3)),
                )
            except ValueError:
                continue
            dates.append(parsed)
        return dates

    @staticmethod
    def _to_lines(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    @staticmethod
    def _build_registration_period(
        start_date: date | None,
        end_date: date | None,
    ) -> str | None:
        if start_date is not None and end_date is not None:
            return f"{start_date.isoformat()}~{end_date.isoformat()}"
        if start_date is not None:
            return start_date.isoformat()
        return None

    @staticmethod
    def _join_texts(parts: list[str]) -> str:
        filtered = [part.strip() for part in parts if part and part.strip()]
        return "\n".join(filtered)

    @staticmethod
    def _looks_like_placeholder_location(value: str) -> bool:
        lowered = value.lower()
        return any(token in lowered for token in INVALID_LOCATION_TOKENS)

    @staticmethod
    def _is_plausible_location(value: str) -> bool:
        if DtrailParser._looks_like_placeholder_location(value):
            return False
        lowered = value.lower()
        if any(token in lowered for token in ("<>", "cp", "코스", "출발", "골인")):
            return False
        compact = " ".join(value.split())
        if len(compact) > 42:
            return False
        if any(hint in compact for hint in LOCATION_ADMIN_HINTS):
            return True
        return False
