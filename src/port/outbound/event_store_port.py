from abc import ABC, abstractmethod

from domain.model.marathon_event import MarathonEvent


class EventStorePort(ABC):
    @abstractmethod
    def upsert_events(self, events: list[MarathonEvent]) -> int:
        """Insert or update crawled events and return processed row count."""

