from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.persistence.multi_store import (
    MultiEventStore,
    MultiEventWatchStore,
    MultiRawDataStore,
    MultiSourceRegistryStore,
)
from domain.model.marathon_event import MarathonEvent
from domain.model.recurrence_watch import RecurrenceWatchSeed
from domain.model.source_registry import SourceCrawlResult, SourceRegistrySeed
from port.outbound.event_store_port import EventStorePort
from port.outbound.event_watch_port import EventWatchPort
from port.outbound.raw_data_store_port import RawDataStorePort
from port.outbound.source_registry_port import SourceRegistryPort

KST = timezone(timedelta(hours=9), name="KST")


class FakeEventStore(EventStorePort):
    def __init__(self, count: int) -> None:
        self.count = count
        self.calls = 0

    def upsert_events(self, events: list[MarathonEvent]) -> int:
        self.calls += 1
        return self.count


class FakeRawDataStore(RawDataStorePort):
    def __init__(self) -> None:
        self.saved = 0
        self.pruned = 0

    def save(
        self,
        *,
        source: str,
        payload: dict[str, object],
        parsed_status: str,
    ) -> None:
        self.saved += 1

    def prune(
        self,
        *,
        parsed_status: str,
        older_than_days: int,
    ) -> int:
        self.pruned += 1
        return 3


class FakeEventWatchStore(EventWatchPort):
    def __init__(self, seed_count: int) -> None:
        self.seed_count = seed_count
        self.seed_calls = 0
        self.refresh_calls = 0

    def save_seeds(self, seeds: list[RecurrenceWatchSeed]) -> int:
        self.seed_calls += 1
        return self.seed_count

    def refresh_watchlist(self, *, today_kst: date) -> dict[str, int]:
        self.refresh_calls += 1
        return {
            "watch_total_count": 10,
            "watch_pending_count": 8,
            "watch_detected_count": 2,
        }


class FakeSourceRegistryStore(SourceRegistryPort):
    def __init__(self, upsert_count: int) -> None:
        self.upsert_count = upsert_count
        self.upsert_calls = 0
        self.record_calls = 0

    def upsert_sources(self, sources: list[SourceRegistrySeed]) -> int:
        self.upsert_calls += 1
        return self.upsert_count

    def record_crawl_result(self, result: SourceCrawlResult) -> None:
        self.record_calls += 1


class MultiStoreTest(unittest.TestCase):
    def test_event_store_writes_all_and_returns_primary_count(self) -> None:
        primary = FakeEventStore(count=5)
        backup = FakeEventStore(count=4)
        store = MultiEventStore([primary, backup])

        saved_count = store.upsert_events(
            [
                MarathonEvent(
                    date_text="12/31",
                    title="테스트 대회",
                    location="서울",
                    link_url="https://example.com",
                )
            ]
        )

        self.assertEqual(5, saved_count)
        self.assertEqual(1, primary.calls)
        self.assertEqual(1, backup.calls)

    def test_raw_data_store_writes_all(self) -> None:
        primary = FakeRawDataStore()
        backup = FakeRawDataStore()
        store = MultiRawDataStore([primary, backup])

        store.save(
            source="source-a",
            payload={"event_count": 1},
            parsed_status="DONE",
        )
        deleted = store.prune(parsed_status="DONE", older_than_days=30)

        self.assertEqual(3, deleted)
        self.assertEqual(1, primary.saved)
        self.assertEqual(1, backup.saved)
        self.assertEqual(1, primary.pruned)
        self.assertEqual(1, backup.pruned)

    def test_event_watch_store_writes_all_and_returns_primary_summary(self) -> None:
        primary = FakeEventWatchStore(seed_count=2)
        backup = FakeEventWatchStore(seed_count=1)
        store = MultiEventWatchStore([primary, backup])

        saved = store.save_seeds(
            [
                RecurrenceWatchSeed(
                    title="테스트 대회",
                    event_date=date(2026, 10, 1),
                )
            ]
        )
        summary = store.refresh_watchlist(today_kst=date(2026, 3, 17))

        self.assertEqual(2, saved)
        self.assertEqual(10, summary["watch_total_count"])
        self.assertEqual(1, primary.seed_calls)
        self.assertEqual(1, backup.seed_calls)
        self.assertEqual(1, primary.refresh_calls)
        self.assertEqual(1, backup.refresh_calls)

    def test_source_registry_store_writes_all(self) -> None:
        primary = FakeSourceRegistryStore(upsert_count=8)
        backup = FakeSourceRegistryStore(upsert_count=8)
        store = MultiSourceRegistryStore([primary, backup])

        upserted = store.upsert_sources(
            [
                SourceRegistrySeed(
                    source_name="source-a",
                    source_url="https://example.com",
                    source_kind="OFFICIAL",
                )
            ]
        )
        store.record_crawl_result(
            SourceCrawlResult(
                source_name="source-a",
                source_url="https://example.com",
                crawled_at_kst=datetime.now(KST),
                success=True,
                event_count=3,
            )
        )

        self.assertEqual(8, upserted)
        self.assertEqual(1, primary.upsert_calls)
        self.assertEqual(1, backup.upsert_calls)
        self.assertEqual(1, primary.record_calls)
        self.assertEqual(1, backup.record_calls)


if __name__ == "__main__":
    unittest.main()
