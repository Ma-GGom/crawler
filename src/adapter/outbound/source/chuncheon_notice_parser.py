import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from port.outbound.event_extract_port import EventExtractPort
from domain.model.marathon_event import MarathonEvent

LIST_URL = "https://board.chosun.com/nbrd/bbs/list.html?b_bbs_id=10005&branch=&pn=1"
DATE_PATTERN = re.compile(r"^20\d{2}\.\d{1,2}\.\d{1,2}$")
TARGET_KEYWORDS = ("접수", "참가", "신청", "일정")
LOCATION = "춘천"
MAX_NOTICE_EVENTS = 5


class ChuncheonNoticeParser(EventExtractPort):
    def extract(self, html: str) -> list[MarathonEvent]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[MarathonEvent] = []

        for row in soup.select("table tr"):
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            title = cols[1].get_text(" ", strip=True)
            if not self._is_target_notice(title):
                continue

            posted_at = cols[3].get_text(" ", strip=True)
            if not DATE_PATTERN.match(posted_at):
                continue

            link = cols[1].find("a", href=True)
            if link is None:
                continue

            detail_url = urljoin(LIST_URL, link.get("href", "").strip())
            if not detail_url:
                continue

            events.append(
                MarathonEvent(
                    date_text=posted_at,
                    title=title.replace("공지", "").strip(),
                    location=LOCATION,
                    link_url=detail_url,
                )
            )
            if len(events) >= MAX_NOTICE_EVENTS:
                break

        return events

    @staticmethod
    def _is_target_notice(title: str) -> bool:
        text = title.strip()
        if not text:
            return False
        return any(keyword in text for keyword in TARGET_KEYWORDS)
