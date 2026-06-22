from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from port.outbound.event_detail_fetch_port import EventDetailFetchPort
from port.outbound.event_extract_port import EventExtractPort
from port.outbound.event_store_port import EventStorePort
from port.outbound.event_watch_port import EventWatchPort
from port.outbound.raw_data_store_port import RawDataStorePort
from port.outbound.source_fetch_port import SourceFetchPort
from port.outbound.source_registry_port import SourceRegistryPort
from application.service.crawl_source_service import CrawlSourceService
from application.service.source_crawler import SourceCrawler
from domain.model.event_detail import MarathonEventDetail
from domain.model.marathon_event import MarathonEvent
from domain.model.source_registry import SourceCrawlResult, SourceRegistrySeed
from domain.model.source_payload import SourcePayload

KST = timezone(timedelta(hours=9), name="KST")


class FakeSourceFetcher(SourceFetchPort):
    def __init__(self, payload: SourcePayload) -> None:
        self._payload = payload

    def fetch_source_payload(self) -> SourcePayload:
        return self._payload


class FakeExtractor(EventExtractPort):
    def __init__(self, events: list[MarathonEvent] | None = None) -> None:
        self._events = events or [
            MarathonEvent(
                date_text="12/31(수)",
                title="테스트 대회",
                location="서울",
                link_url="view.php?no=1",
            )
        ]

    def extract(self, html: str) -> list[MarathonEvent]:
        self._last_html = html
        return self._events


class FakeDetailFetcher(EventDetailFetchPort):
    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        return MarathonEventDetail(
            registration_period="2026년11월1일~2026년12월1일",
            official_website_url="https://example.com/event",
            registration_start_date=date(2026, 11, 1),
            registration_end_date=date(2026, 12, 1),
            event_date=date(2026, 12, 20),
        )


class LocationDetailFetcher(EventDetailFetchPort):
    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        return MarathonEventDetail(
            location="대전엑스포시민광장",
        )


class EmptyDetailFetcher(EventDetailFetchPort):
    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        return MarathonEventDetail(
            registration_period=None,
            official_website_url="https://example.com/event",
            registration_start_date=None,
            registration_end_date=None,
            event_date=None,
        )


class FakeEventStore(EventStorePort):
    def __init__(self) -> None:
        self.saved_batches: list[list[MarathonEvent]] = []

    def upsert_events(self, events: list[MarathonEvent]) -> int:
        self.saved_batches.append(list(events))
        return len(events)


class FakeRawDataStore(RawDataStorePort):
    def __init__(self) -> None:
        self.saved_records: list[dict[str, object]] = []
        self.pruned_records: list[dict[str, object]] = []

    def save(
        self,
        *,
        source: str,
        payload: dict[str, object],
        parsed_status: str,
    ) -> None:
        self.saved_records.append(
            {
                "source": source,
                "payload": payload,
                "parsed_status": parsed_status,
            }
        )

    def prune(
        self,
        *,
        parsed_status: str,
        older_than_days: int,
    ) -> int:
        self.pruned_records.append(
            {
                "parsed_status": parsed_status,
                "older_than_days": older_than_days,
            }
        )
        return 0


class FakeEventWatchStore(EventWatchPort):
    def __init__(self) -> None:
        self.called = False
        self.seed_count = 0

    def save_seeds(self, seeds) -> int:
        self.seed_count += len(seeds)
        return len(seeds)

    def refresh_watchlist(self, *, today_kst: date) -> dict[str, int]:
        self.called = True
        return {
            "watch_total_count": 1,
            "watch_pending_count": 1,
            "watch_detected_count": 0,
        }


class FakeSourceRegistryStore(SourceRegistryPort):
    def __init__(self) -> None:
        self.upserted_sources: list[SourceRegistrySeed] = []
        self.results: list[SourceCrawlResult] = []

    def upsert_sources(self, sources: list[SourceRegistrySeed]) -> int:
        self.upserted_sources.extend(sources)
        return len(sources)

    def record_crawl_result(self, result: SourceCrawlResult) -> None:
        self.results.append(result)


class CrawlSourceServiceTest(unittest.TestCase):
    def test_attach_source_metadata(self) -> None:
        fetched_at = datetime.now(KST)
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=fetched_at,
        )
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(),
        )

        events = service.crawl()

        self.assertEqual(1, len(events))
        self.assertEqual("test-source", events[0].source_name)
        self.assertEqual("https://example.com/list", events[0].source_url)
        self.assertEqual(fetched_at, events[0].crawled_at_kst)

    def test_attach_detail_fields(self) -> None:
        fetched_at = datetime.now(KST)
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=fetched_at,
        )
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(),
            detail_fetcher=FakeDetailFetcher(),
        )

        events = service.crawl()

        self.assertEqual("2026년11월1일~2026년12월1일", events[0].registration_period)
        self.assertEqual("https://example.com/event", events[0].official_website_url)

    def test_keep_existing_event_date_when_detail_event_date_missing(self) -> None:
        fetched_at = datetime.now(KST)
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=fetched_at,
        )
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(
                [
                    MarathonEvent(
                        date_text="12/31(수)",
                        title="테스트 대회",
                        location="서울",
                        link_url="view.php?no=1",
                        event_date=date(2026, 12, 31),
                    )
                ]
            ),
            detail_fetcher=EmptyDetailFetcher(),
        )

        events = service.crawl()

        self.assertEqual("2026-12-31", events[0].event_date.isoformat())

    def test_update_location_from_detail_when_unknown(self) -> None:
        fetched_at = datetime.now(KST)
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=fetched_at,
        )
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(
                [
                    MarathonEvent(
                        date_text="12/31(수)",
                        title="테스트 대회",
                        location="unknown",
                        link_url="https://example.com/detail",
                    )
                ]
            ),
            detail_fetcher=LocationDetailFetcher(),
        )

        events = service.crawl()

        self.assertEqual("대전엑스포시민광장", events[0].location)

    def test_keep_future_event_even_when_registration_closed(self) -> None:
        class ClosedDetailFetcher(EventDetailFetchPort):
            def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
                return MarathonEventDetail(
                    registration_period="2026년1월1일~2026년2월1일",
                    official_website_url="https://example.com/event",
                    registration_start_date=date(2026, 1, 1),
                    registration_end_date=date(2026, 2, 1),
                    event_date=date(2026, 3, 20),
                )

        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=datetime.now(KST),
        )
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(),
            detail_fetcher=ClosedDetailFetcher(),
        )

        events = service.crawl()
        self.assertEqual(1, len(events))

    def test_reject_stale_payload(self) -> None:
        stale_payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=datetime.now(KST) - timedelta(minutes=10),
        )
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(stale_payload),
            event_extractor=FakeExtractor(),
        )

        with self.assertRaises(RuntimeError):
            service.crawl()

    def test_merge_multiple_sources(self) -> None:
        now = datetime.now(KST)
        source_one = SourceCrawler(
            source_fetcher=FakeSourceFetcher(
                SourcePayload(
                    source_name="source-a",
                    source_url="https://example.com/a",
                    html="<a></a>",
                    fetched_at_kst=now,
                )
            ),
            event_extractor=FakeExtractor(
                [
                    MarathonEvent(
                        date_text="12/31(수)",
                        title="A 대회",
                        location="서울",
                        link_url="https://example.com/a/1",
                        event_date=date(2026, 12, 31),
                    )
                ]
            ),
        )
        source_two = SourceCrawler(
            source_fetcher=FakeSourceFetcher(
                SourcePayload(
                    source_name="source-b",
                    source_url="https://example.com/b",
                    html="<b></b>",
                    fetched_at_kst=now,
                )
            ),
            event_extractor=FakeExtractor(
                [
                    MarathonEvent(
                        date_text="12/30(화)",
                        title="B 대회",
                        location="부산",
                        link_url="https://example.com/b/1",
                        event_date=date(2026, 12, 30),
                    )
                ]
            ),
        )

        service = CrawlSourceService(source_crawlers=[source_one, source_two])

        events = service.crawl()

        self.assertEqual(2, len(events))
        self.assertEqual(["source-a", "source-b"], [event.source_name for event in events])

    def test_deduplicate_same_event(self) -> None:
        now = datetime.now(KST)
        same_event = MarathonEvent(
            date_text="12/31(수)",
            title="중복 대회",
            location="서울",
            link_url="https://example.com/dup",
            event_date=date(2026, 12, 31),
        )

        source_one = SourceCrawler(
            source_fetcher=FakeSourceFetcher(
                SourcePayload(
                    source_name="source-a",
                    source_url="https://example.com/a",
                    html="<a></a>",
                    fetched_at_kst=now,
                )
            ),
            event_extractor=FakeExtractor([same_event]),
        )
        source_two = SourceCrawler(
            source_fetcher=FakeSourceFetcher(
                SourcePayload(
                    source_name="source-b",
                    source_url="https://example.com/b",
                    html="<b></b>",
                    fetched_at_kst=now,
                )
            ),
            event_extractor=FakeExtractor([same_event]),
        )

        service = CrawlSourceService(source_crawlers=[source_one, source_two])

        events = service.crawl()

        self.assertEqual(1, len(events))

    def test_deduplicate_by_canonical_official_url_and_choose_better_source(self) -> None:
        now = datetime.now(KST)
        source_one = SourceCrawler(
            source_fetcher=FakeSourceFetcher(
                SourcePayload(
                    source_name="onoffmix.com",
                    source_url="https://onoffmix.com/list",
                    html="<a></a>",
                    fetched_at_kst=now,
                )
            ),
            event_extractor=FakeExtractor(
                [
                    MarathonEvent(
                        date_text="12/31(수)",
                        title="포털 대회명",
                        location="서울",
                        link_url="https://portal.example.com/race?id=10&utm_source=ads",
                        official_website_url="https://race.example.com/apply?utm_campaign=x",
                        event_date=date(2026, 12, 31),
                    )
                ]
            ),
        )
        source_two = SourceCrawler(
            source_fetcher=FakeSourceFetcher(
                SourcePayload(
                    source_name="seoul-marathon.com",
                    source_url="https://seoul-marathon.com/90",
                    html="<b></b>",
                    fetched_at_kst=now - timedelta(seconds=1),
                )
            ),
            event_extractor=FakeExtractor(
                [
                    MarathonEvent(
                        date_text="2026-12-31",
                        title="공식 대회명",
                        location="서울",
                        link_url="https://seoul-marathon.com/notice",
                        official_website_url="https://race.example.com/apply/",
                        registration_start_date=date(2026, 8, 1),
                        registration_end_date=date(2026, 9, 1),
                        event_date=date(2026, 12, 31),
                    )
                ]
            ),
        )

        service = CrawlSourceService(source_crawlers=[source_one, source_two])
        events = service.crawl()

        self.assertEqual(1, len(events))
        self.assertEqual("seoul-marathon.com", events[0].source_name)
        self.assertEqual("공식 대회명", events[0].title)

    def test_store_events_with_event_store(self) -> None:
        fetched_at = datetime.now(KST)
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=fetched_at,
        )
        event_store = FakeEventStore()
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(),
            event_store=event_store,
        )

        events = service.crawl()

        self.assertEqual(1, len(events))
        self.assertEqual(1, len(event_store.saved_batches))
        self.assertEqual(1, len(event_store.saved_batches[0]))
        self.assertEqual("테스트 대회", event_store.saved_batches[0][0].title)

    def test_refresh_event_watch_after_crawl(self) -> None:
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=datetime.now(KST),
        )
        watch_store = FakeEventWatchStore()
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(),
            event_watch_store=watch_store,
        )

        service.crawl()

        self.assertTrue(watch_store.called)
        self.assertTrue(watch_store.seed_count > 0)

    def test_store_raw_payload_done_status(self) -> None:
        fetched_at = datetime.now(KST)
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=fetched_at,
        )
        raw_store = FakeRawDataStore()
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(),
            raw_data_store=raw_store,
        )

        service.crawl()

        self.assertEqual(1, len(raw_store.saved_records))
        self.assertEqual("DONE", raw_store.saved_records[0]["parsed_status"])
        self.assertEqual("test-source", raw_store.saved_records[0]["source"])

    def test_store_raw_payload_error_status(self) -> None:
        stale_payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=datetime.now(KST) - timedelta(minutes=10),
        )
        raw_store = FakeRawDataStore()
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(stale_payload),
            event_extractor=FakeExtractor(),
            raw_data_store=raw_store,
        )

        with self.assertRaises(RuntimeError):
            service.crawl()

        self.assertEqual(1, len(raw_store.saved_records))
        self.assertEqual("ERROR", raw_store.saved_records[0]["parsed_status"])

    def test_prune_raw_payloads_by_retention_policy(self) -> None:
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=datetime.now(KST),
        )
        raw_store = FakeRawDataStore()
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(),
            raw_data_store=raw_store,
            raw_done_retention_days=30,
            raw_error_retention_days=90,
        )

        service.crawl()

        self.assertEqual(2, len(raw_store.pruned_records))
        self.assertEqual("DONE", raw_store.pruned_records[0]["parsed_status"])
        self.assertEqual(30, raw_store.pruned_records[0]["older_than_days"])
        self.assertEqual("ERROR", raw_store.pruned_records[1]["parsed_status"])
        self.assertEqual(90, raw_store.pruned_records[1]["older_than_days"])

    def test_record_source_registry_result_after_crawl(self) -> None:
        payload = SourcePayload(
            source_name="test-source",
            source_url="https://example.com/list",
            html="<table></table>",
            fetched_at_kst=datetime.now(KST),
        )
        registry_store = FakeSourceRegistryStore()
        service = CrawlSourceService(
            source_fetcher=FakeSourceFetcher(payload),
            event_extractor=FakeExtractor(
                [
                    MarathonEvent(
                        date_text="2026-10-01",
                        title="2026 KB 스타 런",
                        location="서울",
                        link_url="https://example.com/race",
                        event_date=date(2026, 10, 1),
                    )
                ]
            ),
            source_registry_store=registry_store,
            source_registry_seeds=[
                SourceRegistrySeed(
                    source_name="test-source",
                    source_url="https://example.com/list",
                    source_kind="OFFICIAL",
                )
            ],
        )

        service.crawl()

        self.assertEqual(1, len(registry_store.upserted_sources))
        self.assertEqual(1, len(registry_store.results))
        self.assertTrue(registry_store.results[0].success)
        self.assertEqual(1, registry_store.results[0].event_count)
        self.assertGreater(registry_store.results[0].rare_event_count, 0)


if __name__ == "__main__":
    unittest.main()
