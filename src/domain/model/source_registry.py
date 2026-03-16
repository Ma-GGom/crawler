from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SourceRegistrySeed:
    source_name: str
    source_url: str
    source_kind: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class SourceCrawlResult:
    source_name: str
    source_url: str | None
    crawled_at_kst: datetime
    success: bool
    event_count: int
    rare_event_count: int = 0
    error_message: str | None = None
