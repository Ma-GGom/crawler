import re
from datetime import date

from bs4 import BeautifulSoup

from domain.model.marathon_event import MarathonEvent
from port.outbound.event_extract_port import EventExtractPort

MARA1080_EVENT_PATTERN = re.compile(
    r"https?://mara1080\.com/event/([0-9a-fA-F\-]{36})"
)
MINI_OPEN_PATTERN = re.compile(r"miniOpen\((\d+)\)")
YEAR_PATTERN = re.compile(r"(20\d{2})")
TARGET_KEYWORDS = ("마라톤", "런", "레이스", "트레일")
EXCLUDED_KEYWORDS = (
    "공동구매",
    "전사모",
    "회원",
    "무료",
    "훈련",
    "교실",
    "취소",
)
REGION_KEYWORDS = (
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "제주",
    "수원",
    "춘천",
    "청주",
    "삼척",
    "금산",
    "보성",
    "아산",
    "보은",
    "이천",
    "거제",
    "무주",
    "대전",
)
LOCATION_FALLBACK = "전국"


class Run1080Parser(EventExtractPort):
    def extract(self, html: str) -> list[MarathonEvent]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[MarathonEvent] = []
        seen_links: set[str] = set()

        for anchor in soup.select("a[href]"):
            title = anchor.get_text(" ", strip=True)
            if not self._is_target_title(title):
                continue

            link_url = self._normalize_mara1080_link(anchor.get("href", ""))
            if link_url is None or link_url in seen_links:
                continue
            seen_links.add(link_url)
            event_date = self._extract_year_date(title)

            events.append(
                MarathonEvent(
                    date_text=self._extract_date_text(title),
                    title=title,
                    location=self._infer_location(title),
                    link_url=link_url,
                    official_website_url=link_url,
                    event_date=event_date,
                )
            )

        return events

    @staticmethod
    def _normalize_mara1080_link(raw_href: str) -> str | None:
        href = raw_href.strip()
        if not href:
            return None

        mini_open_matched = MINI_OPEN_PATTERN.search(href)
        if mini_open_matched is not None:
            code = mini_open_matched.group(1)
            return f"http://www.run1080.com/new/mini/index.php?code={code}"

        matched = MARA1080_EVENT_PATTERN.search(href)
        if matched is None:
            return None

        event_id = matched.group(1).lower()
        return f"https://mara1080.com/event/{event_id}"

    @staticmethod
    def _is_target_title(title: str) -> bool:
        normalized = title.strip()
        if not normalized:
            return False
        if any(keyword in normalized for keyword in EXCLUDED_KEYWORDS):
            return False
        return any(keyword in normalized for keyword in TARGET_KEYWORDS)

    @staticmethod
    def _extract_date_text(title: str) -> str:
        matched = YEAR_PATTERN.search(title)
        if matched is None:
            return "일정 미정"
        return f"{matched.group(1)}년"

    @staticmethod
    def _extract_year_date(title: str) -> date | None:
        matched = YEAR_PATTERN.search(title)
        if matched is None:
            return None
        return date(int(matched.group(1)), 1, 1)

    @staticmethod
    def _infer_location(title: str) -> str:
        for keyword in REGION_KEYWORDS:
            if keyword in title:
                return keyword
        return LOCATION_FALLBACK
