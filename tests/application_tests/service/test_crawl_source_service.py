from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from application.port.outbound.event_extract_port import EventExtractPort
from application.port.outbound.event_detail_fetch_port import EventDetailFetchPort
from application.port.outbound.source_fetch_port import SourceFetchPort
from application.service.crawl_source_service import CrawlSourceService
from domain.model.event_detail import MarathonEventDetail
from domain.model.marathon_event import MarathonEvent
from domain.model.source_payload import SourcePayload

KST = timezone(timedelta(hours=9), name="KST")


class FakeSourceFetcher(SourceFetchPort):
    def __init__(self, payload: SourcePayload) -> None:
        self._payload = payload

    def fetch_source_payload(self) -> SourcePayload:
        return self._payload


class FakeExtractor(EventExtractPort):
    def extract(self, html: str) -> list[MarathonEvent]:
        self._last_html = html
        return [
            MarathonEvent(
                date_text="12/31(수)",
                title="테스트 대회",
                location="서울",
                link_url="view.php?no=1",
            )
        ]


class FakeDetailFetcher(EventDetailFetchPort):
    def fetch_detail(self, detail_url: str) -> MarathonEventDetail | None:
        return MarathonEventDetail(
            registration_period="2026년11월1일~2026년12월1일",
            official_website_url="https://example.com/event",
            registration_start_date=date(2026, 11, 1),
            registration_end_date=date(2026, 12, 1),
            event_date=date(2026, 12, 20),
        )


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

    def test_filter_out_when_registration_closed(self) -> None:
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
        self.assertEqual(0, len(events))

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


if __name__ == "__main__":
    unittest.main()

