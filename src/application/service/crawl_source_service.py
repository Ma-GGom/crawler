from dataclasses import replace
import logging
from typing import Iterable

from port.inbound.crawl_source_usecase import CrawlSourceUseCase
from port.outbound.event_detail_fetch_port import EventDetailFetchPort
from port.outbound.event_extract_port import EventExtractPort
from port.outbound.event_store_port import EventStorePort
from port.outbound.raw_data_store_port import RawDataStorePort
from port.outbound.source_fetch_port import SourceFetchPort
from application.service.source_crawler import SourceCrawler
from domain.model.marathon_event import MarathonEvent
from domain.rule.event_date_rule import infer_event_date_from_list_text
from domain.rule.event_filter_rule import is_actionable_event
from domain.rule.freshness_rule import is_fresh_payload

logger = logging.getLogger(__name__)


class CrawlSourceService(CrawlSourceUseCase):
    def __init__(
        self,
        source_fetcher: SourceFetchPort | None = None,
        event_extractor: EventExtractPort | None = None,
        detail_fetcher: EventDetailFetchPort | None = None,
        event_store: EventStorePort | None = None,
        raw_data_store: RawDataStorePort | None = None,
        raw_done_retention_days: int | None = None,
        raw_error_retention_days: int | None = None,
        source_crawlers: Iterable[SourceCrawler] | None = None,
    ) -> None:
        if source_crawlers is not None:
            self._source_crawlers = list(source_crawlers)
        else:
            if source_fetcher is None or event_extractor is None:
                raise ValueError(
                    "Single-source mode requires source_fetcher and event_extractor"
                )
            self._source_crawlers = [
                SourceCrawler(
                    source_fetcher=source_fetcher,
                    event_extractor=event_extractor,
                    detail_fetcher=detail_fetcher,
                )
            ]

        if not self._source_crawlers:
            raise ValueError("At least one source crawler is required")

        self._event_store = event_store
        self._raw_data_store = raw_data_store
        self._raw_done_retention_days = raw_done_retention_days
        self._raw_error_retention_days = raw_error_retention_days

    def crawl(self) -> list[MarathonEvent]:
        logger.info(
            "crawl_started",
            extra={"source_count": len(self._source_crawlers)},
        )
        merged_events: list[MarathonEvent] = []
        dedup_keys: set[tuple[str, str, str, str]] = set()

        for crawler in self._source_crawlers:
            for event in self._crawl_single_source(crawler):
                dedup_key = self._build_dedup_key(event)
                if dedup_key in dedup_keys:
                    continue

                dedup_keys.add(dedup_key)
                merged_events.append(event)

        saved_count = 0
        if self._event_store is not None and merged_events:
            saved_count = self._event_store.upsert_events(merged_events)

        self._prune_raw_data()
        logger.info(
            "crawl_completed",
            extra={
                "merged_event_count": len(merged_events),
                "saved_event_count": saved_count,
            },
        )

        return merged_events

    def _crawl_single_source(self, crawler: SourceCrawler) -> list[MarathonEvent]:
        payload = None
        source_label = type(crawler.source_fetcher).__name__

        try:
            payload = crawler.source_fetcher.fetch_source_payload()
            source_label = payload.source_name
            logger.info(
                "source_payload_fetched",
                extra={"source": source_label, "source_url": payload.source_url},
            )

            if not is_fresh_payload(payload.fetched_at_kst):
                raise RuntimeError(
                    f"Stale source payload detected: {payload.source_name} ({payload.source_url})"
                )

            events = crawler.event_extractor.extract(payload.html)
            enriched_events: list[MarathonEvent] = []
            for event in events:
                enriched = replace(
                    event,
                    source_name=payload.source_name,
                    source_url=payload.source_url,
                    crawled_at_kst=payload.fetched_at_kst,
                )

                if crawler.detail_fetcher is not None:
                    detail = crawler.detail_fetcher.fetch_detail(enriched.link_url)
                    if detail is not None:
                        enriched = replace(
                            enriched,
                            registration_period=(
                                detail.registration_period
                                or enriched.registration_period
                            ),
                            official_website_url=(
                                detail.official_website_url
                                or enriched.official_website_url
                            ),
                            registration_start_date=(
                                detail.registration_start_date
                                or enriched.registration_start_date
                            ),
                            registration_end_date=(
                                detail.registration_end_date
                                or enriched.registration_end_date
                            ),
                            event_date=detail.event_date or enriched.event_date,
                        )

                if enriched.event_date is None:
                    inferred = infer_event_date_from_list_text(enriched.date_text)
                    if inferred is not None:
                        enriched = replace(enriched, event_date=inferred)

                if not is_actionable_event(enriched):
                    continue

                enriched_events.append(enriched)

            self._save_raw(
                source=source_label,
                payload=self._build_done_raw_payload(payload, enriched_events),
                parsed_status="DONE",
            )
            logger.info(
                "source_crawl_completed",
                extra={"source": source_label, "event_count": len(enriched_events)},
            )
            return enriched_events
        except Exception as exc:
            self._save_raw(
                source=source_label,
                payload=self._build_error_raw_payload(payload, str(exc)),
                parsed_status="ERROR",
            )
            logger.exception(
                "source_crawl_failed",
                extra={"source": source_label},
            )
            raise

    @staticmethod
    def _build_dedup_key(event: MarathonEvent) -> tuple[str, str, str, str]:
        event_date_key = (
            event.event_date.isoformat()
            if event.event_date is not None
            else event.date_text.strip()
        )
        location_key = event.location.strip().lower()
        title_key = event.title.strip().lower()
        official_url_key = (event.official_website_url or event.link_url).strip().lower()
        return title_key, event_date_key, location_key, official_url_key

    def _save_raw(
        self, *, source: str, payload: dict[str, object], parsed_status: str
    ) -> None:
        if self._raw_data_store is None:
            return
        self._raw_data_store.save(
            source=source,
            payload=payload,
            parsed_status=parsed_status,
        )

    def _prune_raw_data(self) -> None:
        if self._raw_data_store is None:
            return

        self._prune_raw_status("DONE", self._raw_done_retention_days)
        self._prune_raw_status("ERROR", self._raw_error_retention_days)

    def _prune_raw_status(self, status: str, retention_days: int | None) -> None:
        if retention_days is None:
            return

        try:
            deleted = self._raw_data_store.prune(
                parsed_status=status,
                older_than_days=retention_days,
            )
            logger.info(
                "raw_data_pruned",
                extra={
                    "parsed_status": status,
                    "retention_days": retention_days,
                    "deleted_count": deleted,
                },
            )
        except Exception:
            logger.exception(
                "raw_data_prune_failed",
                extra={"parsed_status": status, "retention_days": retention_days},
            )

    @staticmethod
    def _build_done_raw_payload(
        payload, events: list[MarathonEvent]
    ) -> dict[str, object]:
        return {
            "source_url": payload.source_url,
            "fetched_at_kst": payload.fetched_at_kst.isoformat(),
            "event_count": len(events),
            "html": payload.html,
        }

    @staticmethod
    def _build_error_raw_payload(payload, error_message: str) -> dict[str, object]:
        if payload is None:
            return {
                "error": error_message,
            }
        return {
            "source_url": payload.source_url,
            "fetched_at_kst": payload.fetched_at_kst.isoformat(),
            "error": error_message,
            "html": payload.html,
        }
