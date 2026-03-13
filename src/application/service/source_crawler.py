from dataclasses import dataclass

from port.outbound.event_detail_fetch_port import EventDetailFetchPort
from port.outbound.event_extract_port import EventExtractPort
from port.outbound.source_fetch_port import SourceFetchPort


@dataclass(frozen=True, slots=True)
class SourceCrawler:
    source_fetcher: SourceFetchPort
    event_extractor: EventExtractPort
    detail_fetcher: EventDetailFetchPort | None = None
