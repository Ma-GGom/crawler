from adapter.inbound.scheduler.cron_runner import CronRunner
from adapter.outbound.source.marathon_pe_client import MarathonPeClient
from adapter.outbound.source.marathon_pe_detail_client import MarathonPeDetailClient
from adapter.outbound.source.marathon_pe_parser import MarathonPeParser
from application.service.crawl_source_service import CrawlSourceService


def create_crawler_app() -> CronRunner:
    source_client = MarathonPeClient()
    detail_client = MarathonPeDetailClient()
    event_parser = MarathonPeParser()
    crawl_service = CrawlSourceService(
        source_fetcher=source_client,
        event_extractor=event_parser,
        detail_fetcher=detail_client,
    )
    return CronRunner(crawl_source_use_case=crawl_service)

