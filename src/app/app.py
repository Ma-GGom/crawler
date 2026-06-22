import logging

from adapter.inbound.scheduler.cron_runner import CronRunner
from adapter.outbound.persistence.multi_store import (
    MultiEventStore,
    MultiEventWatchStore,
    MultiRawDataStore,
    MultiSourceRegistryStore,
)
from adapter.outbound.persistence.postgres_health_checker import (
    assert_postgres_healthy,
    redact_dsn,
)
from adapter.outbound.source.marathon_pe_client import MarathonPeClient
from adapter.outbound.source.marathon_pe_detail_client import MarathonPeDetailClient
from adapter.outbound.source.marathon_pe_parser import MarathonPeParser
from adapter.outbound.source.naver_search_client import NaverSearchClient
from adapter.outbound.source.naver_search_parser import NaverSearchParser
from adapter.outbound.source.chuncheon_notice_client import ChuncheonNoticeClient
from adapter.outbound.source.chuncheon_notice_detail_client import (
    ChuncheonNoticeDetailClient,
)
from adapter.outbound.source.chuncheon_notice_parser import ChuncheonNoticeParser
from adapter.outbound.source.dtrail_client import DtrailClient
from adapter.outbound.source.dtrail_parser import DtrailParser
from adapter.outbound.source.image_ocr import ImageTextOcrReader
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

logger = logging.getLogger(__name__)


def _resolve_database_urls(settings: CrawlerSettings) -> list[str]:
    urls: list[str] = []
    for dsn in (settings.database_url, settings.backup_database_url):
        if not dsn:
            continue
        if dsn not in urls:
            urls.append(dsn)
    return urls


def _run_database_healthcheck(settings: CrawlerSettings) -> None:
    if not settings.database_healthcheck_enabled:
        logger.info("DB 헬스체크 비활성화", extra={"enabled": False})
        return

    db_urls = _resolve_database_urls(settings)
    if not db_urls:
        logger.warning("DB URL 미설정으로 헬스체크를 건너뜀")
        return

    for dsn in db_urls:
        assert_postgres_healthy(
            dsn,
            connect_timeout_seconds=settings.database_connect_timeout_seconds,
        )
        logger.info(
            "DB 헬스체크 통과",
            extra={"database": redact_dsn(dsn)},
        )


def _create_event_store(settings: CrawlerSettings) -> EventStorePort | None:
    db_urls = _resolve_database_urls(settings)
    if not db_urls:
        return None

    from adapter.outbound.persistence.postgres_event_repository import (
        PostgresEventRepository,
    )

    stores: list[EventStorePort] = [
        PostgresEventRepository(
            dsn=dsn,
            table_name=settings.marathon_event_table,
        )
        for dsn in db_urls
    ]
    if len(stores) == 1:
        return stores[0]
    return MultiEventStore(stores)


def _create_raw_data_store(settings: CrawlerSettings) -> RawDataStorePort | None:
    db_urls = _resolve_database_urls(settings)
    if not db_urls:
        return None

    from adapter.outbound.persistence.postgres_raw_crawled_data_repository import (
        PostgresRawCrawledDataRepository,
    )

    stores: list[RawDataStorePort] = [
        PostgresRawCrawledDataRepository(
            dsn=dsn,
            table_name=settings.raw_data_table,
        )
        for dsn in db_urls
    ]
    if len(stores) == 1:
        return stores[0]
    return MultiRawDataStore(stores)


def _create_event_watch_store(settings: CrawlerSettings) -> EventWatchPort | None:
    db_urls = _resolve_database_urls(settings)
    if not db_urls:
        return None

    from adapter.outbound.persistence.postgres_event_watch_repository import (
        PostgresEventWatchRepository,
    )

    stores: list[EventWatchPort] = [
        PostgresEventWatchRepository(
            dsn=dsn,
            watch_table_name=settings.event_watch_table,
            seed_table_name=settings.event_watch_seed_table,
        )
        for dsn in db_urls
    ]
    if len(stores) == 1:
        return stores[0]
    return MultiEventWatchStore(stores)


def _create_source_registry_store(
    settings: CrawlerSettings,
) -> SourceRegistryPort | None:
    db_urls = _resolve_database_urls(settings)
    if not db_urls:
        return None

    from adapter.outbound.persistence.postgres_source_registry_repository import (
        PostgresSourceRegistryRepository,
    )

    stores: list[SourceRegistryPort] = [
        PostgresSourceRegistryRepository(
            dsn=dsn,
            table_name=settings.source_registry_table,
        )
        for dsn in db_urls
    ]
    if len(stores) == 1:
        return stores[0]
    return MultiSourceRegistryStore(stores)


def _build_source_registry_seeds(settings: CrawlerSettings) -> list[SourceRegistrySeed]:
    seeds = [
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
        SourceRegistrySeed(
            source_name=settings.dtrail_source.source_name,
            source_url=settings.dtrail_source.source_url,
            source_kind="OFFICIAL",
        ),
    ]
    if settings.naver_discovery_enabled and settings.naver_discovery_source is not None:
        seeds.append(
            SourceRegistrySeed(
                source_name=settings.naver_discovery_source.source_name,
                source_url=settings.naver_discovery_source.source_url,
                source_kind="DISCOVERY",
            )
        )
    return seeds


def create_crawler_app() -> CronRunner:
    settings = load_settings()
    _run_database_healthcheck(settings)

    dtrail_image_text_reader = None
    if settings.dtrail_ocr_enabled:
        dtrail_image_text_reader = ImageTextOcrReader(
            language=settings.dtrail_ocr_language,
            tesseract_cmd=settings.dtrail_ocr_tesseract_cmd,
        ).read_text
    else:
        logger.info("dtrail OCR 비활성화", extra={"enabled": False})

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
        SourceCrawler(
            source_fetcher=DtrailClient(
                source_url=settings.dtrail_source.source_url,
                source_name=settings.dtrail_source.source_name,
            ),
            event_extractor=DtrailParser(
                source_url=settings.dtrail_source.source_url,
                link_url=settings.dtrail_source.source_url,
                official_website_url=settings.dtrail_source.source_url,
                image_text_reader=dtrail_image_text_reader,
                max_images=settings.dtrail_ocr_max_images,
            ),
        ),
    ]
    if (
        settings.naver_discovery_enabled
        and settings.naver_discovery_source is not None
        and settings.naver_client_id is not None
        and settings.naver_client_secret is not None
    ):
        source_crawlers.append(
            SourceCrawler(
                source_fetcher=NaverSearchClient(
                    source_url=settings.naver_discovery_source.source_url,
                    source_name=settings.naver_discovery_source.source_name,
                    client_id=settings.naver_client_id,
                    client_secret=settings.naver_client_secret,
                    queries=settings.naver_discovery_queries,
                    display=settings.naver_discovery_display,
                ),
                event_extractor=NaverSearchParser(),
            )
        )
    else:
        logger.info(
            "네이버 발견 소스 비활성화",
            extra={
                "enabled": settings.naver_discovery_enabled,
                "has_source": settings.naver_discovery_source is not None,
                "has_client_id": settings.naver_client_id is not None,
                "has_client_secret": settings.naver_client_secret is not None,
            },
        )

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

