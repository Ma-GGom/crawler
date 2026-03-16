import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from port.outbound.event_extract_port import EventExtractPort
from domain.model.marathon_event import MarathonEvent

EVENT_LINK_PREFIX = "/event/"
DATE_PATTERN = re.compile(r"(20\d{2})\.(\d{1,2})\.(\d{1,2})")
RACE_KEYWORDS = ("마라톤", "트레일", "울트라", "레이스")
THEME_RUN_KEYWORDS = (
    "포켓몬런",
    "포켓몬 런",
    "산리오런",
    "산리오 런",
    "컬러런",
    "나이트런",
    "좀비런",
)
NOISE_KEYWORDS = ("런칭", "브런치", "프런트", "런웨이")
LEARNING_NOISE_KEYWORDS = (
    "머신 러닝",
    "머신러닝",
    "딥 러닝",
    "딥러닝",
    "인공지능",
    "chat gpt",
    "챗 gpt",
    "교육",
    "강의",
    "취업",
    "캠프",
)


class OnOffMixParser(EventExtractPort):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def extract(self, html: str) -> list[MarathonEvent]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[MarathonEvent] = []
        seen_links: set[str] = set()

        for article in soup.select("ul.event_lists li article.event_area"):
            link_tag = article.select_one(f"a[href^='{EVENT_LINK_PREFIX}']")
            if link_tag is None:
                continue

            href = link_tag.get("href", "").strip()
            if not href.startswith(EVENT_LINK_PREFIX):
                continue

            title = self._extract_title(article)
            tags = self._extract_tags(article)
            if not self._is_marathon_related(title, tags):
                continue

            date_text = self._extract_date_text(article)
            location = self._extract_location(article)
            event_date = self._extract_event_date(article)
            link_url = urljoin(self._base_url, href)
            if link_url in seen_links:
                continue
            seen_links.add(link_url)

            events.append(
                MarathonEvent(
                    date_text=date_text,
                    title=title,
                    location=location,
                    link_url=link_url,
                    event_date=event_date,
                )
            )

        return events

    @staticmethod
    def _extract_title(article) -> str:
        title_tag = article.select_one("h5.title")
        if title_tag is not None:
            title_text = title_tag.get_text(" ", strip=True)
            if title_text:
                return title_text

        image_tag = article.select_one(".event_thumbnail img[alt]")
        if image_tag is not None:
            alt_text = image_tag.get("alt", "").strip()
            if alt_text:
                return alt_text

        return "제목 없음"

    @staticmethod
    def _extract_tags(article) -> str:
        return " ".join(tag.get_text(" ", strip=True) for tag in article.select(".list_event_tags .tag"))

    @staticmethod
    def _is_marathon_related(title: str, tags_text: str) -> bool:
        haystack = f"{title} {tags_text}".lower()
        if any(keyword in haystack for keyword in NOISE_KEYWORDS):
            return False
        if any(keyword in haystack for keyword in RACE_KEYWORDS):
            return True
        if any(keyword in haystack for keyword in THEME_RUN_KEYWORDS):
            return True
        if "런" in haystack or "러닝" in haystack:
            if any(keyword in haystack for keyword in LEARNING_NOISE_KEYWORDS):
                return False
            return any(
                keyword in haystack
                for keyword in ("대회", "페스타", "페스티벌", "run", "레이스")
            )
        return False

    @staticmethod
    def _extract_date_text(article) -> str:
        short_date = article.select_one(".event_info .date")
        if short_date is not None:
            text = short_date.get_text(" ", strip=True)
            if text:
                return text

        full_date = article.select_one(".list_date_place .date")
        if full_date is not None:
            text = full_date.get_text(" ", strip=True)
            if text:
                return text

        return "일정 미정"

    @staticmethod
    def _extract_location(article) -> str:
        location_tag = article.select_one(".list_date_place .place")
        if location_tag is not None:
            location_text = location_tag.get_text(" ", strip=True)
            if location_text:
                return location_text
        return "장소 미정"

    @staticmethod
    def _extract_event_date(article) -> date | None:
        full_date = article.select_one(".list_date_place .date")
        if full_date is None:
            return None

        text = full_date.get_text(" ", strip=True)
        matched = DATE_PATTERN.search(text)
        if matched is None:
            return None

        try:
            return date(int(matched.group(1)), int(matched.group(2)), int(matched.group(3)))
        except ValueError:
            return None
