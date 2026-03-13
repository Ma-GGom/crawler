from abc import ABC, abstractmethod

from domain.model.marathon_event import MarathonEvent


class CrawlSourceUseCase(ABC):
    @abstractmethod
    def crawl(self) -> list[MarathonEvent]:
        """Fetch and parse events from a source."""

