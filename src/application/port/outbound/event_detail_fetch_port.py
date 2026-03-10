from abc import ABC, abstractmethod

from domain.model.event_detail import MarathonEventDetail


class EventDetailFetchPort(ABC):
    @abstractmethod
    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        """Fetch detail page and return extracted detail fields."""


