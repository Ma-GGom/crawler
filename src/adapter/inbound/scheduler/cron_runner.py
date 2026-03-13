from port.inbound.crawl_source_usecase import CrawlSourceUseCase
from domain.model.marathon_event import MarathonEvent


class CronRunner:
    def __init__(self, crawl_source_use_case: CrawlSourceUseCase) -> None:
        self._crawl_source_use_case = crawl_source_use_case

    def run_once(self) -> list[MarathonEvent]:
        return self._crawl_source_use_case.crawl()

