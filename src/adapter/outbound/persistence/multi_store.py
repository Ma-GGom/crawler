from __future__ import annotations

from datetime import date

from domain.model.marathon_event import MarathonEvent
from domain.model.recurrence_watch import RecurrenceWatchSeed
from domain.model.source_registry import SourceCrawlResult, SourceRegistrySeed
from port.outbound.event_store_port import EventStorePort
from port.outbound.event_watch_port import EventWatchPort
from port.outbound.raw_data_store_port import RawDataStorePort
from port.outbound.source_registry_port import SourceRegistryPort


class MultiEventStore(EventStorePort):
    def __init__(self, stores: list[EventStorePort]) -> None:
        self._stores = stores

    def upsert_events(self, events: list[MarathonEvent]) -> int:
        if not self._stores:
            return 0
        counts = [store.upsert_events(events) for store in self._stores]
        return counts[0]


class MultiRawDataStore(RawDataStorePort):
    def __init__(self, stores: list[RawDataStorePort]) -> None:
        self._stores = stores

    def save(
        self,
        *,
        source: str,
        payload: dict[str, object],
        parsed_status: str,
    ) -> None:
        for store in self._stores:
            store.save(
                source=source,
                payload=payload,
                parsed_status=parsed_status,
            )

    def prune(
        self,
        *,
        parsed_status: str,
        older_than_days: int,
    ) -> int:
        if not self._stores:
            return 0
        counts = [
            store.prune(
                parsed_status=parsed_status,
                older_than_days=older_than_days,
            )
            for store in self._stores
        ]
        return counts[0]


class MultiEventWatchStore(EventWatchPort):
    def __init__(self, stores: list[EventWatchPort]) -> None:
        self._stores = stores

    def save_seeds(self, seeds: list[RecurrenceWatchSeed]) -> int:
        if not self._stores:
            return 0
        counts = [store.save_seeds(seeds) for store in self._stores]
        return counts[0]

    def refresh_watchlist(self, *, today_kst: date) -> dict[str, int]:
        if not self._stores:
            return {
                "watch_total_count": 0,
                "watch_pending_count": 0,
                "watch_detected_count": 0,
            }
        summaries = [store.refresh_watchlist(today_kst=today_kst) for store in self._stores]
        return summaries[0]


class MultiSourceRegistryStore(SourceRegistryPort):
    def __init__(self, stores: list[SourceRegistryPort]) -> None:
        self._stores = stores

    def upsert_sources(self, sources: list[SourceRegistrySeed]) -> int:
        if not self._stores:
            return 0
        counts = [store.upsert_sources(sources) for store in self._stores]
        return counts[0]

    def record_crawl_result(self, result: SourceCrawlResult) -> None:
        for store in self._stores:
            store.record_crawl_result(result)
