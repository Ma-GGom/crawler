from datetime import datetime, timedelta, timezone

import requests

from domain.model.source_payload import SourcePayload
from port.outbound.source_fetch_port import SourceFetchPort

SOURCE_URL = "http://www.run1080.com/new/index.php?sub=sub01_m01_c01"
SOURCE_NAME = "run1080.com"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_SEARCH_YEAR_OFFSETS = (-1, 0, 1)
DEFAULT_ENCODING = "euc-kr"
KST = timezone(timedelta(hours=9), name="KST")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class Run1080Client(SourceFetchPort):
    def __init__(
        self,
        source_url: str = SOURCE_URL,
        source_name: str = SOURCE_NAME,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        search_year_offsets: tuple[int, ...] = DEFAULT_SEARCH_YEAR_OFFSETS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._source_url = source_url
        self._source_name = source_name
        self._timeout_seconds = timeout_seconds
        self._search_year_offsets = search_year_offsets
        self._headers = {
            "User-Agent": user_agent,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def fetch_source_payload(self) -> SourcePayload:
        fetched_at_kst = datetime.now(KST)
        pages: list[str] = []
        errors: list[Exception] = []

        for year in self._target_years(fetched_at_kst):
            params = {"sub": "sub01_m01_c01", "syear": str(year), "smonth": ""}
            try:
                response = requests.get(
                    self._source_url,
                    params=params,
                    headers=self._headers,
                    timeout=self._timeout_seconds,
                )
                response.raise_for_status()
                response.encoding = DEFAULT_ENCODING
                pages.append(
                    f"<!-- run1080_year={year} url={response.url} -->\n{response.text}"
                )
            except requests.RequestException as exc:
                errors.append(exc)

        if not pages:
            if errors:
                raise errors[-1]
            raise RuntimeError("run1080 source page fetch failed")

        return SourcePayload(
            source_name=self._source_name,
            source_url=self._source_url,
            html="\n".join(pages),
            fetched_at_kst=fetched_at_kst,
        )

    def _target_years(self, fetched_at_kst: datetime) -> list[int]:
        years = []
        for offset in self._search_year_offsets:
            years.append(fetched_at_kst.year + offset)
        return years
