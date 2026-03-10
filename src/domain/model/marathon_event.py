from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class MarathonEvent:
    date_text: str
    title: str
    location: str
    link_url: str
    registration_period: str | None = None
    official_website_url: str | None = None
    registration_start_date: date | None = None
    registration_end_date: date | None = None
    event_date: date | None = None
    source_name: str = ""
    source_url: str = ""
    crawled_at_kst: datetime | None = None
