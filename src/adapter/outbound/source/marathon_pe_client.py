from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from port.outbound.source_fetch_port import SourceFetchPort
from domain.model.source_payload import SourcePayload

SOURCE_URL = "http://www.marathon.pe.kr/schedule_index.html"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_ENCODING = "euc-kr"
SOURCE_NAME = "marathon.pe.kr"
KST = timezone(timedelta(hours=9), name="KST")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class MarathonPeClient(SourceFetchPort):
    def __init__(
        self,
        source_url: str = SOURCE_URL,
        source_name: str = SOURCE_NAME,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._source_url = source_url
        self._source_name = source_name
        self._timeout_seconds = timeout_seconds
        self._headers = {
            "User-Agent": user_agent,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def fetch_source_payload(self) -> SourcePayload:
        fetched_at_kst = datetime.now(KST)
        root_html = self._fetch_html_with_encoding(self._source_url)
        frame_url = self._extract_target_frame_url(root_html, self._source_url)
        target_url = frame_url if frame_url else self._source_url

        if frame_url:
            html = self._fetch_html_with_encoding(frame_url)
        else:
            html = root_html

        return SourcePayload(
            source_name=self._source_name,
            source_url=target_url,
            html=html,
            fetched_at_kst=fetched_at_kst,
        )

    def _fetch_html_with_encoding(self, url: str) -> str:
        response = requests.get(
            url,
            headers=self._headers,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        response.encoding = DEFAULT_ENCODING
        return response.text

    @staticmethod
    def _extract_target_frame_url(html: str, base_url: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        frame = soup.find("frame", attrs={"name": "right"})
        if frame is None:
            frames = soup.find_all("frame")
            if frames:
                frame = frames[-1]
        if frame is None:
            return None

        src = frame.get("src")
        if not src:
            return None
        return urljoin(base_url, src)

