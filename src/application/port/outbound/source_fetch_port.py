from abc import ABC, abstractmethod

from domain.model.source_payload import SourcePayload


class SourceFetchPort(ABC):
    @abstractmethod
    def fetch_source_payload(self) -> SourcePayload:
        """Return fetched source payload with crawl metadata."""

