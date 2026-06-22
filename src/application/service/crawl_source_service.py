from collections import Counter
from dataclasses import replace
import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

from port.inbound.crawl_source_usecase import CrawlSourceUseCase
from port.outbound.event_detail_fetch_port import EventDetailFetchPort
from port.outbound.event_extract_port import EventExtractPort
from port.outbound.event_store_port import EventStorePort
from port.outbound.event_watch_port import EventWatchPort
from port.outbound.raw_data_store_port import RawDataStorePort
from port.outbound.source_fetch_port import SourceFetchPort
from port.outbound.source_registry_port import SourceRegistryPort
from application.service.source_crawler import SourceCrawler
from domain.model.marathon_event import MarathonEvent
from domain.model.recurrence_watch import RecurrenceWatchSeed
from domain.model.source_registry import SourceCrawlResult, SourceRegistrySeed
from domain.rule.event_date_rule import infer_event_date_from_list_text
from domain.rule.event_filter_rule import is_actionable_event
from domain.rule.freshness_rule import is_fresh_payload
from domain.rule.location_rule import REGION_UNKNOWN
from domain.rule.rare_marathon_rule import match_rare_marathon_keywords
from domain.rule.url_rule import normalize_url

logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9), name="KST")


class CrawlSourceService(CrawlSourceUseCase):
    def __init__(
        self,
        source_fetcher: SourceFetchPort | None = None,
        event_extractor: EventExtractPort | None = None,
        detail_fetcher: EventDetailFetchPort | None = None,
        event_store: EventStorePort | None = None,
        event_watch_store: EventWatchPort | None = None,
        source_registry_store: SourceRegistryPort | None = None,
        source_registry_seeds: list[SourceRegistrySeed] | None = None,
        source_priority: dict[str, int] | None = None,
        watch_seed_excluded_sources: set[str] | None = None,
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
        self._event_watch_store = event_watch_store
        self._source_registry_store = source_registry_store
        self._source_registry_seeds = source_registry_seeds or []
        self._source_priority = source_priority or {}
        self._watch_seed_excluded_sources = watch_seed_excluded_sources or set()
        self._raw_data_store = raw_data_store
        self._raw_done_retention_days = raw_done_retention_days
        self._raw_error_retention_days = raw_error_retention_days

    def crawl(self) -> list[MarathonEvent]:
        self._upsert_source_registry_seeds()
        logger.info(
            "크롤링 시작",
            extra={"source_count": len(self._source_crawlers)},
        )
        merged_by_key: dict[tuple[str, str], MarathonEvent] = {}
        replaced_count = 0

        for crawler in self._source_crawlers:
            for event in self._crawl_single_source(crawler):
                dedup_key = self._build_dedup_key(event)
                existing = merged_by_key.get(dedup_key)
                if existing is None:
                    merged_by_key[dedup_key] = event
                    continue
                if self._is_better_event(candidate=event, existing=existing):
                    merged_by_key[dedup_key] = event
                    replaced_count += 1

        merged_events = list(merged_by_key.values())

        saved_count = 0
        if self._event_store is not None and merged_events:
            saved_count = self._event_store.upsert_events(merged_events)

        self._refresh_event_watch()
        self._prune_raw_data()
        logger.info(
            "크롤링 완료",
            extra={
                "merged_event_count": len(merged_events),
                "saved_event_count": saved_count,
                "dedup_replaced_count": replaced_count,
            },
        )

        return merged_events

    def _upsert_source_registry_seeds(self) -> None:
        if self._source_registry_store is None or not self._source_registry_seeds:
            return

        try:
            upserted_count = self._source_registry_store.upsert_sources(
                self._source_registry_seeds
            )
            logger.info(
                "소스 레지스트리 갱신 완료",
                extra={"source_registry_count": upserted_count},
            )
        except Exception:
            logger.exception("소스 레지스트리 갱신 실패")

    def _record_source_crawl_result(
        self,
        *,
        source_name: str,
        source_url: str | None,
        crawled_at_kst: datetime,
        success: bool,
        event_count: int,
        rare_event_count: int,
        error_message: str | None = None,
    ) -> None:
        if self._source_registry_store is None:
            return

        try:
            self._source_registry_store.record_crawl_result(
                SourceCrawlResult(
                    source_name=source_name,
                    source_url=source_url,
                    crawled_at_kst=crawled_at_kst,
                    success=success,
                    event_count=event_count,
                    rare_event_count=rare_event_count,
                    error_message=error_message,
                )
            )
        except Exception:
            logger.exception("소스 레지스트리 실행결과 기록 실패")

    def _refresh_event_watch(self) -> None:
        if self._event_watch_store is None:
            return

        try:
            summary = self._event_watch_store.refresh_watchlist(
                today_kst=datetime.now(KST).date()
            )
            logger.info("재개최 추적 목록 갱신 완료", extra=summary)
        except Exception:
            logger.exception("재개최 추적 목록 갱신 실패")

    def _save_watch_seeds(self, seeds: list[RecurrenceWatchSeed]) -> None:
        if self._event_watch_store is None or not seeds:
            return

        try:
            saved_count = self._event_watch_store.save_seeds(seeds)
            logger.info("재개최 추적 시드 저장 완료", extra={"watch_seed_count": saved_count})
        except Exception:
            logger.exception("재개최 추적 시드 저장 실패")

    def _crawl_single_source(self, crawler: SourceCrawler) -> list[MarathonEvent]:
        payload = None
        source_label = type(crawler.source_fetcher).__name__

        try:
            payload = crawler.source_fetcher.fetch_source_payload()
            source_label = payload.source_name
            logger.info(
                "소스 원본 데이터 수집 완료",
                extra={"source": source_label, "source_url": payload.source_url},
            )

            if not is_fresh_payload(payload.fetched_at_kst):
                raise RuntimeError(
                    f"신선도 기준을 벗어난 소스 데이터입니다: {payload.source_name} ({payload.source_url})"
                )

            events = crawler.event_extractor.extract(payload.html)
            enriched_events: list[MarathonEvent] = []
            watch_seeds: list[RecurrenceWatchSeed] = []
            rare_keyword_counter: Counter[str] = Counter()
            today_kst = datetime.now(KST).date()
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
                            location=(
                                detail.location
                                if detail.location
                                and enriched.location.strip().lower()
                                in {"", REGION_UNKNOWN}
                                else enriched.location
                            ),
                        )

                if enriched.event_date is None:
                    inferred = infer_event_date_from_list_text(enriched.date_text)
                    if inferred is not None:
                        enriched = replace(enriched, event_date=inferred)

                if enriched.event_date is not None:
                    if (
                        enriched.source_name not in self._watch_seed_excluded_sources
                        and enriched.event_date.year in (today_kst.year - 1, today_kst.year)
                    ):
                        watch_seeds.append(
                            RecurrenceWatchSeed(
                                title=enriched.title,
                                event_date=enriched.event_date,
                                source_name=enriched.source_name,
                                source_url=enriched.source_url,
                            )
                        )

                if not is_actionable_event(enriched):
                    continue

                for keyword in match_rare_marathon_keywords(enriched.title):
                    rare_keyword_counter[keyword] += 1
                enriched_events.append(enriched)

            self._save_watch_seeds(watch_seeds)
            rare_event_count = sum(rare_keyword_counter.values())
            if rare_event_count > 0:
                logger.info(
                    "희귀 대회 키워드 감지",
                    extra={
                        "source": source_label,
                        "rare_event_count": rare_event_count,
                        "rare_keywords": sorted(rare_keyword_counter.keys()),
                    },
                )
            self._save_raw(
                source=source_label,
                payload=self._build_done_raw_payload(
                    payload,
                    enriched_events,
                    rare_keyword_counter=rare_keyword_counter,
                ),
                parsed_status="DONE",
            )
            self._record_source_crawl_result(
                source_name=payload.source_name,
                source_url=payload.source_url,
                crawled_at_kst=payload.fetched_at_kst,
                success=True,
                event_count=len(enriched_events),
                rare_event_count=rare_event_count,
            )
            logger.info(
                "소스 크롤링 완료",
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
                "소스 크롤링 실패",
                extra={"source": source_label},
            )
            self._record_source_crawl_result(
                source_name=source_label,
                source_url=payload.source_url if payload is not None else None,
                crawled_at_kst=(
                    payload.fetched_at_kst
                    if payload is not None
                    else datetime.now(KST)
                ),
                success=False,
                event_count=0,
                rare_event_count=0,
                error_message=str(exc),
            )
            raise

    @staticmethod
    def _build_dedup_key(event: MarathonEvent) -> tuple[str, str]:
        canonical_url = normalize_url(event.official_website_url or event.link_url)
        if canonical_url:
            return "url", canonical_url

        event_date_key = (
            event.event_date.isoformat()
            if event.event_date is not None
            else event.date_text.strip()
        )
        location_key = event.location.strip().lower()
        title_key = event.title.strip().lower()
        composite = f"{title_key}|{event_date_key}|{location_key}"
        return "composite", composite

    def _is_better_event(self, candidate: MarathonEvent, existing: MarathonEvent) -> bool:
        candidate_score = self._event_quality_score(candidate)
        existing_score = self._event_quality_score(existing)
        if candidate_score != existing_score:
            return candidate_score > existing_score

        candidate_time = CrawlSourceService._safe_event_time(candidate.crawled_at_kst)
        existing_time = CrawlSourceService._safe_event_time(existing.crawled_at_kst)
        return candidate_time > existing_time

    def _event_quality_score(self, event: MarathonEvent) -> int:
        score = self._source_priority.get(event.source_name, 0)
        if event.event_date is not None:
            score += 30
        if event.registration_start_date is not None:
            score += 25
        if event.registration_end_date is not None:
            score += 20
        if normalize_url(event.official_website_url):
            score += 15
        elif normalize_url(event.link_url):
            score += 10
        if event.registration_period:
            score += 5
        return score

    @staticmethod
    def _safe_event_time(value: datetime | None) -> datetime:
        if value is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

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
                "원본 데이터 보관기간 정리 완료",
                extra={
                    "parsed_status": status,
                    "retention_days": retention_days,
                    "deleted_count": deleted,
                },
            )
        except Exception:
            logger.exception(
                "원본 데이터 보관기간 정리 실패",
                extra={"parsed_status": status, "retention_days": retention_days},
            )

    @staticmethod
    def _build_done_raw_payload(
        payload,
        events: list[MarathonEvent],
        *,
        rare_keyword_counter: Counter[str],
    ) -> dict[str, object]:
        return {
            "source_url": payload.source_url,
            "fetched_at_kst": payload.fetched_at_kst.isoformat(),
            "event_count": len(events),
            "rare_event_count": sum(rare_keyword_counter.values()),
            "rare_keywords": sorted(rare_keyword_counter.keys()),
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
