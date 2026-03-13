from datetime import datetime, timedelta, timezone

import requests

from port.outbound.source_fetch_port import SourceFetchPort
from domain.model.source_payload import SourcePayload

SOURCE_URL = "https://www.onoffmix.com/event?s=%EB%A7%88%EB%9D%BC%ED%86%A4"
SOURCE_NAME = "onoffmix.com"
DEFAULT_TIMEOUT_SECONDS = 10
KST = timezone(timedelta(hours=9), name="KST")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class OnOffMixClient(SourceFetchPort):
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
        response = requests.get(
            self._source_url,
            headers=self._headers,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()

        return SourcePayload(
            source_name=self._source_name,
            source_url=self._source_url,
            html=response.text,
            fetched_at_kst=fetched_at_kst,
        )
