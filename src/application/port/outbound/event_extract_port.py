from abc import ABC, abstractmethod

from domain.model.marathon_event import MarathonEvent


class EventExtractPort(ABC):
    @abstractmethod
    def extract(self, html: str) -> list[MarathonEvent]:
        """Parse source HTML and return normalized events."""

