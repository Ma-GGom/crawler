from dataclasses import replace

from application.port.inbound.crawl_source_usecase import CrawlSourceUseCase
from application.port.outbound.event_detail_fetch_port import EventDetailFetchPort
from application.port.outbound.event_extract_port import EventExtractPort
from application.port.outbound.source_fetch_port import SourceFetchPort
from domain.model.marathon_event import MarathonEvent
from domain.rule.event_date_rule import infer_event_date_from_list_text
from domain.rule.event_filter_rule import is_actionable_event
from domain.rule.freshness_rule import is_fresh_payload


class CrawlSourceService(CrawlSourceUseCase):
    def __init__(
        self,
        source_fetcher: SourceFetchPort,
        event_extractor: EventExtractPort,
        detail_fetcher: EventDetailFetchPort | None = None,
    ) -> None:
        self._source_fetcher = source_fetcher
        self._event_extractor = event_extractor
        self._detail_fetcher = detail_fetcher

    def crawl(self) -> list[MarathonEvent]:
        payload = self._source_fetcher.fetch_source_payload()
        if not is_fresh_payload(payload.fetched_at_kst):
            raise RuntimeError("Stale source payload detected")

        events = self._event_extractor.extract(payload.html)
        enriched_events: list[MarathonEvent] = []
        for event in events:
            enriched = replace(
                event,
                source_name=payload.source_name,
                source_url=payload.source_url,
                crawled_at_kst=payload.fetched_at_kst,
            )

            if self._detail_fetcher is not None:
                detail = self._detail_fetcher.fetch_detail(enriched.link_url)
                if detail is not None:
                    enriched = replace(
                        enriched,
                        registration_period=detail.registration_period,
                        official_website_url=detail.official_website_url,
                        registration_start_date=detail.registration_start_date,
                        registration_end_date=detail.registration_end_date,
                        event_date=detail.event_date,
                    )

            if enriched.event_date is None:
                inferred = infer_event_date_from_list_text(enriched.date_text)
                if inferred is not None:
                    enriched = replace(enriched, event_date=inferred)

            if not is_actionable_event(enriched):
                continue

            enriched_events.append(enriched)

        return enriched_events

