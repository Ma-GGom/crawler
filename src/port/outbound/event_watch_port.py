from abc import ABC, abstractmethod
from datetime import date

from domain.model.recurrence_watch import RecurrenceWatchSeed


class EventWatchPort(ABC):
    @abstractmethod
    def save_seeds(self, seeds: list[RecurrenceWatchSeed]) -> int:
        """Persist watch seeds extracted during crawl."""

    @abstractmethod
    def refresh_watchlist(self, *, today_kst: date) -> dict[str, int]:
        """Refresh yearly recurrence watchlist from crawled events."""
