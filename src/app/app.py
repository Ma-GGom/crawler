from adapter.inbound.scheduler.cron_runner import CronRunner
from adapter.outbound.source.marathon_pe_client import MarathonPeClient
from adapter.outbound.source.marathon_pe_detail_client import MarathonPeDetailClient
from adapter.outbound.source.marathon_pe_parser import MarathonPeParser
from adapter.outbound.source.jtbc_marathon_client import JtbcMarathonClient
from adapter.outbound.source.jtbc_marathon_parser import JtbcMarathonParser
from adapter.outbound.source.onoffmix_client import OnOffMixClient
from adapter.outbound.source.onoffmix_detail_client import OnOffMixDetailClient
from adapter.outbound.source.onoffmix_parser import OnOffMixParser
from adapter.outbound.source.seoul_marathon_client import SeoulMarathonClient
from adapter.outbound.source.seoul_marathon_detail_client import (
    SeoulMarathonDetailClient,
)
from adapter.outbound.source.seoul_marathon_parser import SeoulMarathonParser
from application.service.crawl_source_service import CrawlSourceService
from application.service.source_crawler import SourceCrawler
from app.settings import CrawlerSettings, load_settings
from port.outbound.event_store_port import EventStorePort
from port.outbound.raw_data_store_port import RawDataStorePort


def _create_event_store(settings: CrawlerSettings) -> EventStorePort | None:
    database_url = settings.database_url
    if not database_url:
        return None

    from adapter.outbound.persistence.postgres_event_repository import (
        PostgresEventRepository,
    )

    return PostgresEventRepository(
        dsn=database_url,
        table_name=settings.marathon_event_table,
    )


def _create_raw_data_store(settings: CrawlerSettings) -> RawDataStorePort | None:
    database_url = settings.database_url
    if not database_url:
        return None

    from adapter.outbound.persistence.postgres_raw_crawled_data_repository import (
        PostgresRawCrawledDataRepository,
    )

    return PostgresRawCrawledDataRepository(
        dsn=database_url,
        table_name=settings.raw_data_table,
    )


def create_crawler_app() -> CronRunner:
    settings = load_settings()
    source_crawlers = [
        SourceCrawler(
            source_fetcher=MarathonPeClient(),
            event_extractor=MarathonPeParser(),
            detail_fetcher=MarathonPeDetailClient(),
        ),
        SourceCrawler(
            source_fetcher=OnOffMixClient(),
            event_extractor=OnOffMixParser(),
            detail_fetcher=OnOffMixDetailClient(),
        ),
        SourceCrawler(
            source_fetcher=JtbcMarathonClient(),
            event_extractor=JtbcMarathonParser(),
        ),
        SourceCrawler(
            source_fetcher=SeoulMarathonClient(),
            event_extractor=SeoulMarathonParser(),
            detail_fetcher=SeoulMarathonDetailClient(),
        ),
    ]

    crawl_service = CrawlSourceService(
        source_crawlers=source_crawlers,
        event_store=_create_event_store(settings),
        raw_data_store=_create_raw_data_store(settings),
        raw_done_retention_days=settings.raw_done_retention_days,
        raw_error_retention_days=settings.raw_error_retention_days,
    )
    return CronRunner(crawl_source_use_case=crawl_service)

