from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

from domain.model.source_payload import SourcePayload
from port.outbound.source_fetch_port import SourceFetchPort

SEARCH_TERMS = ("마라톤", "러닝", "트레일런")
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
        source_url: str,
        source_name: str,
        search_terms: tuple[str, ...] = SEARCH_TERMS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._source_url = source_url
        self._search_terms = search_terms
        self._source_name = source_name
        self._timeout_seconds = timeout_seconds
        self._headers = {
            "User-Agent": user_agent,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def fetch_source_payload(self) -> SourcePayload:
        fetched_at_kst = datetime.now(KST)
        pages: list[str] = []

        for term in self._search_terms:
            query = urlencode({"s": term})
            search_url = f"{self._source_url}?{query}"
            response = requests.get(
                search_url,
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            pages.append(
                f"<!-- onoffmix_search={term} url={search_url} -->\n{response.text}"
            )

        return SourcePayload(
            source_name=self._source_name,
            source_url=self._source_url,
            html="\n".join(pages),
            fetched_at_kst=fetched_at_kst,
        )
