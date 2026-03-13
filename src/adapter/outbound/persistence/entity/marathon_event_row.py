from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class MarathonEventRow:
    title: str | None
    event_date: date | None
    region: str | None
    distances: list[str]
    reg_start_date: datetime | None
    reg_end_date: datetime | None
    is_major: bool
    link_url: str | None
    status: str
    source_name: str | None
    source_url: str | None
    crawled_at_kst: datetime | None

