from datetime import datetime, timedelta, timezone

import requests

from port.outbound.source_fetch_port import SourceFetchPort
from domain.model.source_payload import SourcePayload

DEFAULT_TIMEOUT_SECONDS = 10
KST = timezone(timedelta(hours=9), name="KST")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class JtbcMarathonClient(SourceFetchPort):
    def __init__(
        self,
        source_url: str,
        source_name: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._source_url = source_url
        self._source_name = source_name
        self._timeout_seconds = timeout_seconds
        self._headers = {
            "User-Agent": user_agent,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
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
        response.encoding = response.apparent_encoding

        return SourcePayload(
            source_name=self._source_name,
            source_url=self._source_url,
            html=response.text,
            fetched_at_kst=fetched_at_kst,
        )
