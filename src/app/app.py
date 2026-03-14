from adapter.inbound.scheduler.cron_runner import CronRunner
from adapter.outbound.source.marathon_pe_client import MarathonPeClient
from adapter.outbound.source.marathon_pe_detail_client import MarathonPeDetailClient
from adapter.outbound.source.marathon_pe_parser import MarathonPeParser
from adapter.outbound.source.chuncheon_notice_client import ChuncheonNoticeClient
from adapter.outbound.source.chuncheon_notice_detail_client import (
    ChuncheonNoticeDetailClient,
)
from adapter.outbound.source.chuncheon_notice_parser import ChuncheonNoticeParser
from adapter.outbound.source.jtbc_marathon_client import JtbcMarathonClient
from adapter.outbound.source.jtbc_marathon_parser import JtbcMarathonParser
from adapter.outbound.source.onoffmix_client import OnOffMixClient
from adapter.outbound.source.onoffmix_detail_client import OnOffMixDetailClient
from adapter.outbound.source.onoffmix_parser import OnOffMixParser
from adapter.outbound.source.mara1080_detail_client import Mara1080DetailClient
from adapter.outbound.source.pokemon_run_tworld_client import PokemonRunTworldClient
from adapter.outbound.source.pokemon_run_tworld_parser import PokemonRunTworldParser
from adapter.outbound.source.run1080_client import Run1080Client
from adapter.outbound.source.run1080_parser import Run1080Parser
from adapter.outbound.source.runnext_client import RunNextClient
from adapter.outbound.source.runnext_parser import RunNextParser
from adapter.outbound.source.seoul_marathon_client import SeoulMarathonClient
from adapter.outbound.source.seoul_marathon_detail_client import (
    SeoulMarathonDetailClient,
)
from adapter.outbound.source.seoul_marathon_parser import SeoulMarathonParser
from application.service.crawl_source_service import CrawlSourceService
from application.service.source_crawler import SourceCrawler
from app.settings import CrawlerSettings, load_settings
from port.outbound.event_watch_port import EventWatchPort
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


def _create_event_watch_store(settings: CrawlerSettings) -> EventWatchPort | None:
    database_url = settings.database_url
    if not database_url:
        return None

    from adapter.outbound.persistence.postgres_event_watch_repository import (
        PostgresEventWatchRepository,
    )

    return PostgresEventWatchRepository(
        dsn=database_url,
        watch_table_name=settings.event_watch_table,
        seed_table_name=settings.event_watch_seed_table,
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
            source_fetcher=ChuncheonNoticeClient(),
            event_extractor=ChuncheonNoticeParser(),
            detail_fetcher=ChuncheonNoticeDetailClient(),
        ),
        SourceCrawler(
            source_fetcher=RunNextClient(),
            event_extractor=RunNextParser(),
        ),
        SourceCrawler(
            source_fetcher=Run1080Client(),
            event_extractor=Run1080Parser(),
            detail_fetcher=Mara1080DetailClient(),
        ),
        SourceCrawler(
            source_fetcher=PokemonRunTworldClient(),
            event_extractor=PokemonRunTworldParser(),
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
        event_watch_store=_create_event_watch_store(settings),
        raw_data_store=_create_raw_data_store(settings),
        raw_done_retention_days=settings.raw_done_retention_days,
        raw_error_retention_days=settings.raw_error_retention_days,
    )
    return CronRunner(crawl_source_use_case=crawl_service)

