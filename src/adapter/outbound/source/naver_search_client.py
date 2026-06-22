from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import requests

from domain.model.source_payload import SourcePayload
from port.outbound.source_fetch_port import SourceFetchPort

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_DISPLAY = 30
KST = timezone(timedelta(hours=9), name="KST")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class NaverSearchClient(SourceFetchPort):
    def __init__(
        self,
        *,
        source_url: str,
        source_name: str,
        client_id: str,
        client_secret: str,
        queries: tuple[str, ...],
        display: int = DEFAULT_DISPLAY,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._source_url = source_url
        self._source_name = source_name
        self._queries = tuple(query.strip() for query in queries if query.strip())
        self._display = max(1, min(display, 100))
        self._timeout_seconds = timeout_seconds
        self._headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

    def fetch_source_payload(self) -> SourcePayload:
        fetched_at_kst = datetime.now(KST)
        results: list[dict[str, object]] = []

        for query in self._queries:
            response = requests.get(
                self._source_url,
                params={
                    "query": query,
                    "display": self._display,
                    "sort": "date",
                },
                headers=self._headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", []) if isinstance(payload, dict) else []
            results.append(
                {
                    "query": query,
                    "items": items if isinstance(items, list) else [],
                }
            )

        return SourcePayload(
            source_name=self._source_name,
            source_url=self._source_url,
            html=json.dumps({"results": results}, ensure_ascii=False),
            fetched_at_kst=fetched_at_kst,
        )
