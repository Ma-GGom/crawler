from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import html
import json
import re
from urllib.parse import unquote, urlparse

from port.outbound.event_extract_port import EventExtractPort
from domain.model.marathon_event import MarathonEvent

KST = timezone(timedelta(hours=9), name="KST")
MARATHON_KEYWORDS = (
    "마라톤",
    "런",
    "러닝",
    "레이스",
    "트레일",
    "산리오런",
    "포켓몬런",
    "동아마라톤",
    "서울마라톤",
    "춘천마라톤",
    "제마",
    "jtbc",
)
NOISE_KEYWORDS = (
    "머신러닝",
    "머신 러닝",
    "딥러닝",
    "딥 러닝",
    "강의",
    "취업",
    "교육",
    "주식",
    "게임",
)
DATE_PATTERNS = (
    re.compile(r"(20\d{2})[./-]\s*(\d{1,2})[./-]\s*(\d{1,2})"),
    re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"),
)
MONTH_DAY_PATTERNS = (
    re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일"),
    re.compile(r"\b(\d{1,2})/(\d{1,2})(?:\([^)]*\))?"),
)
LOCATION_PATTERN = re.compile(
    r"(서울(?:특별시|시)?|부산(?:광역시|시)?|대구(?:광역시|시)?|인천(?:광역시|시)?|광주(?:광역시|시)?|"
    r"대전(?:광역시|시)?|울산(?:광역시|시)?|세종(?:특별자치시|시)?|경기도|강원(?:특별자치도|도)|"
    r"충청북도|충청남도|전북(?:특별자치도|도)?|전라남도|경상북도|경상남도|제주(?:특별자치도|도)?)"
    r"\s*([가-힣]{1,15}(?:시|군|구))?"
)
TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


class NaverSearchParser(EventExtractPort):
    def extract(self, html_text: str) -> list[MarathonEvent]:
        try:
            payload = json.loads(html_text)
        except json.JSONDecodeError:
            return []

        if not isinstance(payload, dict):
            return []

        results = payload.get("results")
        if not isinstance(results, list):
            return []

        events: list[MarathonEvent] = []
        seen_links: set[str] = set()
        for result in results:
            if not isinstance(result, dict):
                continue
            for item in result.get("items", []):
                event = self._to_event(item)
                if event is None:
                    continue
                normalized_link = self._normalize_link(event.link_url)
                if normalized_link in seen_links:
                    continue
                seen_links.add(normalized_link)
                events.append(event)
        return events

    def _to_event(self, item: object) -> MarathonEvent | None:
        if not isinstance(item, dict):
            return None

        title = self._clean_text(item.get("title"))
        if title is None:
            return None

        description = self._clean_text(item.get("description")) or ""
        search_text = f"{title} {description}".lower()
        if not self._is_marathon_candidate(search_text):
            return None

        link_url = self._extract_link(item)
        if link_url is None:
            return None

        event_date = self._extract_event_date(f"{title} {description}")
        date_text = event_date.isoformat() if event_date is not None else "일정 미정"
        location = self._extract_location(f"{title} {description}")

        return MarathonEvent(
            date_text=date_text,
            title=title,
            location=location,
            link_url=link_url,
            official_website_url=link_url,
            event_date=event_date,
        )

    @staticmethod
    def _clean_text(raw: object) -> str | None:
        if not isinstance(raw, str):
            return None
        stripped = raw.strip()
        if not stripped:
            return None
        without_tags = TAG_PATTERN.sub(" ", stripped)
        unescaped = html.unescape(without_tags)
        normalized = WHITESPACE_PATTERN.sub(" ", unescaped).strip()
        return normalized or None

    @staticmethod
    def _extract_link(item: dict[str, object]) -> str | None:
        for key in ("originallink", "link"):
            value = item.get(key)
            if not isinstance(value, str):
                continue
            candidate = value.strip()
            if candidate:
                return candidate
        return None

    @staticmethod
    def _normalize_link(raw_url: str) -> str:
        try:
            parsed = urlparse(raw_url)
            if parsed.netloc.endswith("search.naver.com"):
                query = unquote(parsed.query)
                return query or raw_url
        except Exception:
            return raw_url
        return raw_url

    @staticmethod
    def _is_marathon_candidate(text: str) -> bool:
        if any(keyword in text for keyword in NOISE_KEYWORDS):
            return False
        return any(keyword in text for keyword in MARATHON_KEYWORDS)

    @staticmethod
    def _extract_event_date(text: str) -> date | None:
        normalized = WHITESPACE_PATTERN.sub(" ", text)
        for pattern in DATE_PATTERNS:
            matched = pattern.search(normalized)
            if matched is None:
                continue
            year = int(matched.group(1))
            month = int(matched.group(2))
            day = int(matched.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                continue

        today_kst = datetime.now(KST).date()
        for pattern in MONTH_DAY_PATTERNS:
            matched = pattern.search(normalized)
            if matched is None:
                continue
            month = int(matched.group(1))
            day = int(matched.group(2))
            candidate = NaverSearchParser._safe_date(today_kst.year, month, day)
            if candidate is None:
                continue
            if candidate < today_kst and today_kst.month == 12 and month == 1:
                next_year = NaverSearchParser._safe_date(today_kst.year + 1, month, day)
                if next_year is not None:
                    return next_year
            return candidate
        return None

    @staticmethod
    def _safe_date(year: int, month: int, day: int) -> date | None:
        try:
            return date(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def _extract_location(text: str) -> str:
        fallback_province = ""
        for matched in LOCATION_PATTERN.finditer(text):
            province = (matched.group(1) or "").strip()
            city_or_district = (matched.group(2) or "").strip()
            if province and city_or_district:
                return f"{province} {city_or_district}"
            if not fallback_province and province:
                fallback_province = province

        if fallback_province:
            return fallback_province
        return "unknown"
