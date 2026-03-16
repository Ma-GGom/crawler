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
from domain.model.source_registry import SourceRegistrySeed
from port.outbound.event_watch_port import EventWatchPort
from port.outbound.event_store_port import EventStorePort
from port.outbound.raw_data_store_port import RawDataStorePort
from port.outbound.source_registry_port import SourceRegistryPort


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


def _create_source_registry_store(
    settings: CrawlerSettings,
) -> SourceRegistryPort | None:
    database_url = settings.database_url
    if not database_url:
        return None

    from adapter.outbound.persistence.postgres_source_registry_repository import (
        PostgresSourceRegistryRepository,
    )

    return PostgresSourceRegistryRepository(
        dsn=database_url,
        table_name=settings.source_registry_table,
    )


def _build_source_registry_seeds(settings: CrawlerSettings) -> list[SourceRegistrySeed]:
    return [
        SourceRegistrySeed(
            source_name=settings.marathon_pe_source.source_name,
            source_url=settings.marathon_pe_source.source_url,
            source_kind="PLATFORM",
        ),
        SourceRegistrySeed(
            source_name=settings.onoffmix_source.source_name,
            source_url=settings.onoffmix_source.source_url,
            source_kind="PLATFORM",
        ),
        SourceRegistrySeed(
            source_name=settings.chuncheon_notice_source.source_name,
            source_url=settings.chuncheon_notice_source.source_url,
            source_kind="BOARD",
        ),
        SourceRegistrySeed(
            source_name=settings.runnext_source.source_name,
            source_url=settings.runnext_source.source_url,
            source_kind="PLATFORM",
        ),
        SourceRegistrySeed(
            source_name=settings.run1080_source.source_name,
            source_url=settings.run1080_source.source_url,
            source_kind="PLATFORM",
        ),
        SourceRegistrySeed(
            source_name=settings.pokemon_run_source.source_name,
            source_url=settings.pokemon_run_source.source_url,
            source_kind="OFFICIAL",
        ),
        SourceRegistrySeed(
            source_name=settings.jtbc_source.source_name,
            source_url=settings.jtbc_source.source_url,
            source_kind="OFFICIAL",
        ),
        SourceRegistrySeed(
            source_name=settings.seoul_marathon_source.source_name,
            source_url=settings.seoul_marathon_source.source_url,
            source_kind="OFFICIAL",
        ),
    ]


def create_crawler_app() -> CronRunner:
    settings = load_settings()
    source_crawlers = [
        SourceCrawler(
            source_fetcher=MarathonPeClient(
                source_url=settings.marathon_pe_source.source_url,
                source_name=settings.marathon_pe_source.source_name,
            ),
            event_extractor=MarathonPeParser(
                detail_base_url=settings.marathon_pe_detail_base_url,
            ),
            detail_fetcher=MarathonPeDetailClient(),
        ),
        SourceCrawler(
            source_fetcher=OnOffMixClient(
                source_url=settings.onoffmix_source.source_url,
                source_name=settings.onoffmix_source.source_name,
            ),
            event_extractor=OnOffMixParser(
                base_url=settings.onoffmix_base_url,
            ),
            detail_fetcher=OnOffMixDetailClient(),
        ),
        SourceCrawler(
            source_fetcher=ChuncheonNoticeClient(
                source_url=settings.chuncheon_notice_source.source_url,
                source_name=settings.chuncheon_notice_source.source_name,
            ),
            event_extractor=ChuncheonNoticeParser(
                list_url=settings.chuncheon_notice_source.source_url,
            ),
            detail_fetcher=ChuncheonNoticeDetailClient(),
        ),
        SourceCrawler(
            source_fetcher=RunNextClient(
                source_url=settings.runnext_source.source_url,
                source_name=settings.runnext_source.source_name,
            ),
            event_extractor=RunNextParser(
                fallback_url=settings.runnext_fallback_url,
            ),
        ),
        SourceCrawler(
            source_fetcher=Run1080Client(
                source_url=settings.run1080_source.source_url,
                source_name=settings.run1080_source.source_name,
            ),
            event_extractor=Run1080Parser(
                mini_url_template=settings.run1080_mini_url_template,
                event_url_template=settings.run1080_event_url_template,
            ),
            detail_fetcher=Mara1080DetailClient(),
        ),
        SourceCrawler(
            source_fetcher=PokemonRunTworldClient(
                source_url=settings.pokemon_run_source.source_url,
                source_name=settings.pokemon_run_source.source_name,
            ),
            event_extractor=PokemonRunTworldParser(
                link_url=settings.pokemon_run_source.source_url,
                official_website_url=settings.pokemon_run_official_url,
            ),
        ),
        SourceCrawler(
            source_fetcher=JtbcMarathonClient(
                source_url=settings.jtbc_source.source_url,
                source_name=settings.jtbc_source.source_name,
            ),
            event_extractor=JtbcMarathonParser(
                official_url=settings.jtbc_source.source_url,
            ),
        ),
        SourceCrawler(
            source_fetcher=SeoulMarathonClient(
                source_url=settings.seoul_marathon_source.source_url,
                source_name=settings.seoul_marathon_source.source_name,
            ),
            event_extractor=SeoulMarathonParser(
                detail_url=settings.seoul_marathon_detail_url,
            ),
            detail_fetcher=SeoulMarathonDetailClient(),
        ),
    ]

    crawl_service = CrawlSourceService(
        source_crawlers=source_crawlers,
        event_store=_create_event_store(settings),
        event_watch_store=_create_event_watch_store(settings),
        source_registry_store=_create_source_registry_store(settings),
        source_registry_seeds=_build_source_registry_seeds(settings),
        source_priority=settings.source_priority,
        watch_seed_excluded_sources=settings.watch_seed_excluded_sources,
        raw_data_store=_create_raw_data_store(settings),
        raw_done_retention_days=settings.raw_done_retention_days,
        raw_error_retention_days=settings.raw_error_retention_days,
    )
    return CronRunner(crawl_source_use_case=crawl_service)

